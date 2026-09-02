#!/usr/bin/env python3
"""Copy the exact manifest-covered KSRF payload into a skills directory."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from contextvars import ContextVar
import errno
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Iterator, Sequence
from uuid import uuid4

from skillset_file_contract import (
    FileContractError,
    SKILL_NAMES,
    development_files,
    payload_files,
    tree_digest,
)


class InstallationError(RuntimeError):
    """The requested copy cannot be performed without risking another path."""


class JournalDurabilityError(InstallationError):
    """A journal rename happened, but its containing directory was not synced."""


INSTALL_LOCK_FILE_NAME = ".ksrf-install.lock"
INSTALL_TRANSACTION_PREFIX = ".ksrf-install-transaction-"
INSTALL_GC_PREFIX = ".ksrf-install-gc-"
INSTALL_TRANSACTION_JOURNAL_NAME = "journal.json"

_JOURNAL_SCHEMA_VERSION = 2
_JOURNAL_TEMP_NAME = ".journal.json.tmp"
_STAGING_NAME = "staging"
_BACKUP_NAME = "backups"
_QUARANTINE_NAME = "quarantine"
_CLEANUP_CONTAINERS = (_STAGING_NAME, _BACKUP_NAME, _QUARANTINE_NAME)
_CLEANUP_STATES = {"pending", "deleting", "deleted"}
_JOURNAL_PHASES = {
    "building",
    "prepared",
    "rolling_back",
    "rolled_back",
    "committed",
}
_PROGRESS_STATES = {
    "pending",
    "backing_up",
    "backed_up",
    "placing",
    "placed",
    "restored",
}


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _linux_mount_points() -> set[str]:
    """Return decoded Linux mount points when the kernel exposes mountinfo."""

    mountinfo = Path("/proc/self/mountinfo")
    if not mountinfo.is_file():
        return set()
    try:
        lines = mountinfo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    mount_points: set[str] = set()
    for line in lines:
        fields = line.split(" - ", 1)[0].split()
        if len(fields) < 5:
            continue
        decoded = fields[4]
        for escaped, character in (
            (r"\040", " "),
            (r"\011", "\t"),
            (r"\012", "\n"),
            (r"\134", "\\"),
        ):
            decoded = decoded.replace(escaped, character)
        mount_points.add(decoded)
    return mount_points


def _owned_tree_entries(root: Path) -> list[tuple[Path, os.stat_result]]:
    """Collect one owned tree without ever descending across a mount boundary."""

    if root.is_symlink() or not root.is_dir():
        raise InstallationError(f"expected a regular installer-owned directory: {root}")
    root_metadata = root.lstat()
    root_device = root_metadata.st_dev
    mount_points = _linux_mount_points()
    entries: list[tuple[Path, os.stat_result]] = []

    def visit(path: Path) -> None:
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise InstallationError(f"refusing symlink in managed tree: {path}")
        if metadata.st_dev != root_device:
            raise InstallationError(f"refusing device boundary in managed tree: {path}")
        if stat.S_ISDIR(metadata.st_mode):
            absolute = str(path.resolve(strict=True))
            if os.path.ismount(path) or absolute in mount_points:
                raise InstallationError(f"refusing mount boundary in managed tree: {path}")
        elif stat.S_ISREG(metadata.st_mode):
            if metadata.st_nlink != 1:
                raise InstallationError(f"refusing hard-linked file in managed tree: {path}")
        else:
            raise InstallationError(f"refusing special file in managed tree: {path}")
        entries.append((path, metadata))
        if stat.S_ISDIR(metadata.st_mode):
            for child in sorted(path.iterdir(), key=lambda item: item.name):
                visit(child)

    visit(root)
    return entries


def _directory_identity(root: Path) -> str:
    """Hash every owned path, type, mode, and file byte below one skill root."""

    digest = sha256()
    for path, metadata in sorted(
        _owned_tree_entries(root),
        key=lambda item: item[0].relative_to(root).as_posix(),
    ):
        relative = "." if path == root else path.relative_to(root).as_posix()
        encoded = relative.encode("utf-8")
        if stat.S_ISDIR(metadata.st_mode):
            kind = b"D"
        else:
            kind = b"F"
        digest.update(kind)
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(stat.S_IMODE(metadata.st_mode).to_bytes(4, "big"))
        if kind == b"F":
            size = metadata.st_size
            digest.update(size.to_bytes(8, "big"))
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
    return digest.hexdigest()


def _fsync_tree(root: Path) -> None:
    """Make staged file bytes and directory entries durable before publication."""

    directories: list[Path] = []
    for path, metadata in _owned_tree_entries(root):
        if stat.S_ISDIR(metadata.st_mode):
            directories.append(path)
            continue
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    for directory in reversed(directories):
        _fsync_directory(directory)


def _aggregate_identity(entries: list[dict[str, object]], field: str) -> str:
    digest = sha256()
    for entry in entries:
        name = str(entry["name"]).encode("utf-8")
        value = entry[field]
        digest.update(len(name).to_bytes(4, "big"))
        digest.update(name)
        if value is None:
            digest.update(b"A")
        else:
            encoded = str(value).encode("ascii")
            digest.update(b"P")
            digest.update(encoded)
    return digest.hexdigest()


def _path_identity(path: Path) -> str | None:
    if path.is_symlink():
        raise InstallationError(f"refusing symlinked transaction path: {path}")
    if not path.exists():
        return None
    return _directory_identity(path)


def _replace_path(source: Path, destination: Path) -> None:
    anchor = _ACTIVE_TARGET_ANCHOR.get()
    if anchor is None:
        os.replace(source, destination)
        return
    anchor.replace(source, destination)


def _remove_owned_directory(path: Path) -> None:
    entries = _owned_tree_entries(path)
    for owned_path, original_metadata in reversed(entries):
        current_metadata = owned_path.lstat()
        if (
            current_metadata.st_dev,
            current_metadata.st_ino,
            stat.S_IFMT(current_metadata.st_mode),
        ) != (
            original_metadata.st_dev,
            original_metadata.st_ino,
            stat.S_IFMT(original_metadata.st_mode),
        ):
            raise InstallationError(
                f"installer-owned path changed before cleanup; retained at {owned_path}"
            )
        if stat.S_ISDIR(current_metadata.st_mode):
            if owned_path != path and os.path.ismount(owned_path):
                raise InstallationError(f"refusing mounted installer cleanup path: {owned_path}")
            owned_path.rmdir()
        else:
            owned_path.unlink()


class _TargetAnchor:
    """Held directory identities that make the advisory lock path-stable."""

    def __init__(
        self,
        target: Path,
        parent_descriptor: int,
        target_descriptor: int,
        lock_path: Path,
        lock_descriptor: int,
    ) -> None:
        self.target = target
        self.parent_descriptor = parent_descriptor
        self.target_descriptor = target_descriptor
        self.lock_path = lock_path
        self.lock_descriptor = lock_descriptor

    def assert_current(self) -> None:
        try:
            parent_now = self.target.parent.lstat()
            target_now = self.target.lstat()
            lock_now = self.lock_path.lstat()
        except OSError as exc:
            raise InstallationError(
                f"install target anchor changed while locked: {self.target}: {exc}"
            ) from exc
        parent_held = os.fstat(self.parent_descriptor)
        target_held = os.fstat(self.target_descriptor)
        lock_held = os.fstat(self.lock_descriptor)
        if (
            not stat.S_ISDIR(parent_now.st_mode)
            or (parent_now.st_dev, parent_now.st_ino)
            != (parent_held.st_dev, parent_held.st_ino)
            or not stat.S_ISDIR(target_now.st_mode)
            or (target_now.st_dev, target_now.st_ino)
            != (target_held.st_dev, target_held.st_ino)
            or not stat.S_ISREG(lock_now.st_mode)
            or (lock_now.st_dev, lock_now.st_ino)
            != (lock_held.st_dev, lock_held.st_ino)
        ):
            raise InstallationError(
                f"install target or lock inode changed while locked: {self.target}"
            )

    def replace(self, source: Path, destination: Path) -> None:
        try:
            source_relative = source.relative_to(self.target)
            destination_relative = destination.relative_to(self.target)
        except ValueError as exc:
            raise InstallationError(
                f"refusing rename outside held install target: {source} -> {destination}"
            ) from exc
        self.assert_current()
        os.replace(
            source_relative,
            destination_relative,
            src_dir_fd=self.target_descriptor,
            dst_dir_fd=self.target_descriptor,
        )
        self.assert_current()


_ACTIVE_TARGET_ANCHOR: ContextVar[_TargetAnchor | None] = ContextVar(
    "ksrf_active_target_anchor",
    default=None,
)


@contextmanager
def _target_install_lock(target: Path) -> Iterator[_TargetAnchor]:
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        parent_descriptor = os.open(target.parent, directory_flags)
    except OSError as exc:
        raise InstallationError(f"cannot anchor install target parent {target.parent}: {exc}") from exc
    try:
        try:
            fcntl.flock(parent_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                raise InstallationError(
                    f"another skillset installer holds the target parent lock: {target.parent}"
                ) from exc
            raise InstallationError(
                f"cannot acquire install target parent lock {target.parent}: {exc}"
            ) from exc
        try:
            target_descriptor = os.open(target, directory_flags)
        except OSError as exc:
            raise InstallationError(f"cannot anchor install target {target}: {exc}") from exc
        try:
            lock_path = target / INSTALL_LOCK_FILE_NAME
            if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
                raise InstallationError(f"refusing unsafe install lock: {lock_path}")
            flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(lock_path, flags, 0o600)
            except OSError as exc:
                raise InstallationError(f"cannot open install lock {lock_path}: {exc}") from exc
            try:
                lock_metadata = os.fstat(descriptor)
                if not stat.S_ISREG(lock_metadata.st_mode):
                    raise InstallationError(f"install lock is not a regular file: {lock_path}")
                if (
                    lock_metadata.st_nlink != 1
                    or lock_metadata.st_uid != os.getuid()
                    or stat.S_IMODE(lock_metadata.st_mode) & 0o022
                ):
                    raise InstallationError(f"install lock ownership or mode is unsafe: {lock_path}")
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                        raise InstallationError(
                            f"another skillset installer holds the target lock: {lock_path}"
                        ) from exc
                    raise InstallationError(
                        f"cannot acquire install lock {lock_path}: {exc}"
                    ) from exc
                anchor = _TargetAnchor(
                    target,
                    parent_descriptor,
                    target_descriptor,
                    lock_path,
                    descriptor,
                )
                anchor.assert_current()
                anchor_token = _ACTIVE_TARGET_ANCHOR.set(anchor)
                try:
                    yield anchor
                    anchor.assert_current()
                finally:
                    try:
                        _ACTIVE_TARGET_ANCHOR.reset(anchor_token)
                    finally:
                        fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
        finally:
            os.close(target_descriptor)
    finally:
        try:
            fcntl.flock(parent_descriptor, fcntl.LOCK_UN)
        finally:
            os.close(parent_descriptor)


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _json_object_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InstallationError(f"duplicate transaction journal key: {key}")
        result[key] = value
    return result


def _write_journal(transaction_root: Path, journal: dict[str, object]) -> None:
    journal_path = transaction_root / INSTALL_TRANSACTION_JOURNAL_NAME
    temporary_path = transaction_root / _JOURNAL_TEMP_NAME
    if temporary_path.is_symlink() or temporary_path.exists():
        raise InstallationError(f"unsafe stale journal temporary file: {temporary_path}")
    payload = (json.dumps(journal, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary_path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    os.replace(temporary_path, journal_path)
    try:
        _fsync_directory(transaction_root)
    except (OSError, KeyboardInterrupt) as exc:
        raise JournalDurabilityError(
            f"transaction journal rename is not durably confirmed; recovery evidence retained "
            f"at {transaction_root}"
        ) from exc


def _discard_journal_temporary(transaction_root: Path) -> None:
    temporary_path = transaction_root / _JOURNAL_TEMP_NAME
    if temporary_path.is_symlink():
        raise InstallationError(f"refusing symlinked journal temporary file: {temporary_path}")
    if temporary_path.exists():
        if not temporary_path.is_file():
            raise InstallationError(f"invalid journal temporary file: {temporary_path}")
        temporary_path.unlink()
        _fsync_directory(transaction_root)


def _forward_progress_is_reachable(progresses: list[str]) -> bool:
    index = 0
    while index < len(progresses) and progresses[index] == "placed":
        index += 1
    if index < len(progresses) and progresses[index] in {
        "backing_up",
        "backed_up",
        "placing",
    }:
        index += 1
    return all(progress == "pending" for progress in progresses[index:])


def _validate_progress_vector(entries: list[dict[str, object]], phase: str) -> None:
    progresses = [str(entry["progress"]) for entry in entries]
    if phase == "building":
        valid = all(progress == "pending" for progress in progresses)
    elif phase == "prepared":
        valid = _forward_progress_is_reachable(progresses)
    elif phase == "rolling_back":
        first_restored = next(
            (index for index, progress in enumerate(progresses) if progress == "restored"),
            len(progresses),
        )
        valid = _forward_progress_is_reachable(progresses[:first_restored]) and all(
            progress == "restored" for progress in progresses[first_restored:]
        )
    elif phase == "committed":
        valid = all(progress == "placed" for progress in progresses)
    elif phase == "rolled_back":
        valid = all(progress == "restored" for progress in progresses)
    else:
        valid = False
    if not valid:
        raise InstallationError("transaction journal progress vector is unreachable")


def _validate_cleanup_vector(
    cleanup: dict[str, object],
    phase: str,
    container_prefix: str,
) -> None:
    if set(cleanup) != set(_CLEANUP_CONTAINERS) or any(
        cleanup[name] not in _CLEANUP_STATES for name in _CLEANUP_CONTAINERS
    ):
        raise InstallationError("transaction cleanup vector is inconsistent")
    states = [str(cleanup[name]) for name in _CLEANUP_CONTAINERS]
    if container_prefix == INSTALL_TRANSACTION_PREFIX or phase not in {
        "committed",
        "rolled_back",
    }:
        valid = all(state == "pending" for state in states)
    else:
        index = 0
        while index < len(states) and states[index] == "deleted":
            index += 1
        if index < len(states) and states[index] == "deleting":
            index += 1
        valid = all(state == "pending" for state in states[index:])
    if not valid:
        raise InstallationError("transaction cleanup vector is unreachable")


def _load_journal(
    transaction_root: Path,
    target: Path,
    *,
    container_prefix: str = INSTALL_TRANSACTION_PREFIX,
) -> dict[str, object]:
    journal_path = transaction_root / INSTALL_TRANSACTION_JOURNAL_NAME
    if journal_path.is_symlink() or not journal_path.is_file():
        raise InstallationError(
            f"transaction journal is missing or unsafe; recovery evidence retained at "
            f"{transaction_root}"
        )
    if journal_path.stat().st_size > 1024 * 1024:
        raise InstallationError(
            f"transaction journal is unreasonably large; recovery evidence retained at "
            f"{transaction_root}"
        )
    try:
        journal = json.loads(
            journal_path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object_without_duplicates,
        )
    except (InstallationError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise InstallationError(
            f"corrupt transaction journal; recovery evidence retained at {transaction_root}: "
            f"{exc}"
        ) from exc
    if not isinstance(journal, dict):
        raise InstallationError(
            f"transaction journal is not an object; recovery evidence retained at "
            f"{transaction_root}"
        )

    expected_keys = {
        "schema_version",
        "transaction_id",
        "target",
        "target_device",
        "target_inode",
        "phase",
        "skill_names",
        "old_aggregate",
        "incoming_aggregate",
        "skills",
        "cleanup",
    }
    if set(journal) != expected_keys:
        raise InstallationError(
            f"transaction journal fields are incomplete or unknown; recovery evidence "
            f"retained at {transaction_root}"
        )
    if not transaction_root.name.startswith(container_prefix):
        raise InstallationError(
            f"transaction container name is inconsistent; recovery evidence retained at "
            f"{transaction_root}"
        )
    transaction_id = transaction_root.name.removeprefix(container_prefix)
    target_metadata = target.resolve(strict=True).stat()
    if (
        journal["schema_version"] != _JOURNAL_SCHEMA_VERSION
        or not transaction_id
        or journal["transaction_id"] != transaction_id
        or journal["target"] != str(target.resolve(strict=True))
        or journal["target_device"] != target_metadata.st_dev
        or journal["target_inode"] != target_metadata.st_ino
        or journal["phase"] not in _JOURNAL_PHASES
        or journal["skill_names"] != list(SKILL_NAMES)
    ):
        raise InstallationError(
            f"transaction journal identity, schema, target, or phase mismatch; recovery "
            f"evidence retained at {transaction_root}"
        )

    raw_entries = journal["skills"]
    if not isinstance(raw_entries, list) or len(raw_entries) != len(SKILL_NAMES):
        raise InstallationError(
            f"transaction journal managed set is incomplete; recovery evidence retained at "
            f"{transaction_root}"
        )
    entry_keys = {
        "name",
        "old_present",
        "old_digest",
        "incoming_digest",
        "progress",
    }
    entries: list[dict[str, object]] = []
    for expected_name, raw_entry in zip(SKILL_NAMES, raw_entries, strict=True):
        if not isinstance(raw_entry, dict) or set(raw_entry) != entry_keys:
            raise InstallationError(
                f"transaction journal skill entry is corrupt; recovery evidence retained at "
                f"{transaction_root}"
            )
        entry = raw_entry
        old_present = entry["old_present"]
        if (
            entry["name"] != expected_name
            or not isinstance(old_present, bool)
            or entry["progress"] not in _PROGRESS_STATES
            or (old_present and not _is_digest(entry["old_digest"]))
            or (not old_present and entry["old_digest"] is not None)
            or (
                entry["incoming_digest"] is not None
                and not _is_digest(entry["incoming_digest"])
            )
        ):
            raise InstallationError(
                f"transaction journal skill entry is inconsistent; recovery evidence retained "
                f"at {transaction_root}"
            )
        entries.append(entry)

    phase = str(journal["phase"])
    if phase == "building":
        if (
            journal["incoming_aggregate"] is not None
            or any(entry["incoming_digest"] is not None for entry in entries)
            or any(entry["progress"] != "pending" for entry in entries)
        ):
            raise InstallationError(
                f"building transaction journal is inconsistent; recovery evidence retained at "
                f"{transaction_root}"
            )
    else:
        if not _is_digest(journal["incoming_aggregate"]) or any(
            not _is_digest(entry["incoming_digest"]) for entry in entries
        ):
            raise InstallationError(
                f"transaction incoming generation is incomplete; recovery evidence retained at "
                f"{transaction_root}"
            )
    _validate_progress_vector(entries, phase)
    raw_cleanup = journal["cleanup"]
    if not isinstance(raw_cleanup, dict):
        raise InstallationError(
            f"transaction cleanup state is not an object; recovery evidence retained at "
            f"{transaction_root}"
        )
    _validate_cleanup_vector(raw_cleanup, phase, container_prefix)
    if (
        not _is_digest(journal["old_aggregate"])
        or journal["old_aggregate"] != _aggregate_identity(entries, "old_digest")
        or (
            phase != "building"
            and journal["incoming_aggregate"]
            != _aggregate_identity(entries, "incoming_digest")
        )
    ):
        raise InstallationError(
            f"transaction aggregate identity mismatch; recovery evidence retained at "
            f"{transaction_root}"
        )
    return journal


def _owned_container_identities(
    transaction_root: Path,
    name: str,
    *,
    required: bool,
) -> dict[str, str]:
    container = transaction_root / name
    if container.is_symlink():
        raise InstallationError(
            f"symlinked transaction container; recovery evidence retained at {transaction_root}"
        )
    if not container.exists():
        if required:
            raise InstallationError(
                f"missing transaction container; recovery evidence retained at {transaction_root}"
            )
        return {}
    if not container.is_dir():
        raise InstallationError(
            f"invalid transaction container; recovery evidence retained at {transaction_root}"
        )
    identities: dict[str, str] = {}
    for child in sorted(container.iterdir(), key=lambda item: item.name):
        if child.name not in SKILL_NAMES or child.is_symlink() or not child.is_dir():
            raise InstallationError(
                f"unknown or unsafe transaction artifact {child}; recovery evidence retained at "
                f"{transaction_root}"
            )
        identities[child.name] = _directory_identity(child)
    return identities


def _validate_transaction_layout(
    transaction_root: Path,
    phase: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    allowed = {
        INSTALL_TRANSACTION_JOURNAL_NAME,
        _JOURNAL_TEMP_NAME,
        _STAGING_NAME,
        _BACKUP_NAME,
        _QUARANTINE_NAME,
    }
    unexpected = sorted(child.name for child in transaction_root.iterdir() if child.name not in allowed)
    if unexpected:
        raise InstallationError(
            f"unknown transaction artifacts {', '.join(unexpected)}; recovery evidence retained "
            f"at {transaction_root}"
        )
    temporary = transaction_root / _JOURNAL_TEMP_NAME
    if temporary.is_symlink() or (temporary.exists() and not temporary.is_file()):
        raise InstallationError(
            f"unsafe journal temporary file; recovery evidence retained at {transaction_root}"
        )
    required = phase in {"prepared", "rolling_back"}
    staged = _owned_container_identities(
        transaction_root,
        _STAGING_NAME,
        required=required,
    )
    backups = _owned_container_identities(
        transaction_root,
        _BACKUP_NAME,
        required=required,
    )
    quarantined = _owned_container_identities(
        transaction_root,
        _QUARANTINE_NAME,
        required=required,
    )
    return staged, backups, quarantined


def _target_state(target: Path, entry: dict[str, object]) -> str | None:
    return _path_identity(target / str(entry["name"]))


def _verify_old_generation(target: Path, entries: list[dict[str, object]]) -> None:
    for entry in entries:
        if _target_state(target, entry) != entry["old_digest"]:
            raise InstallationError(
                f"old generation verification failed for {entry['name']}"
            )


def _verify_incoming_generation(target: Path, entries: list[dict[str, object]]) -> None:
    for entry in entries:
        if _target_state(target, entry) != entry["incoming_digest"]:
            raise InstallationError(
                f"incoming generation verification failed for {entry['name']}"
            )


def _forward_states(
    entry: dict[str, object],
) -> set[tuple[object, object, object, object]]:
    old = entry["old_digest"]
    incoming = entry["incoming_digest"]
    progress = str(entry["progress"])
    if bool(entry["old_present"]):
        states_by_progress = {
            "pending": {(old, None, incoming, None)},
            "backing_up": {
                (old, None, incoming, None),
                (None, old, incoming, None),
            },
            "backed_up": {(None, old, incoming, None)},
            "placing": {
                (None, old, incoming, None),
                (incoming, old, None, None),
            },
            "placed": {(incoming, old, None, None)},
        }
    else:
        states_by_progress = {
            "pending": {(None, None, incoming, None)},
            "backing_up": {(None, None, incoming, None)},
            "backed_up": {(None, None, incoming, None)},
            "placing": {
                (None, None, incoming, None),
                (incoming, None, None, None),
            },
            "placed": {(incoming, None, None, None)},
        }
    return states_by_progress.get(progress, set())


def _validate_uncommitted_state(
    target: Path,
    entries: list[dict[str, object]],
    staged: dict[str, str],
    backups: dict[str, str],
    quarantined: dict[str, str],
    *,
    rolling_back: bool,
) -> None:
    for entry in entries:
        name = str(entry["name"])
        physical = (
            _target_state(target, entry),
            backups.get(name),
            staged.get(name),
            quarantined.get(name),
        )
        allowed = _forward_states(entry)
        if rolling_back:
            old = entry["old_digest"]
            incoming = entry["incoming_digest"]
            allowed |= {
                (old, None, incoming, None),
                (old, None, None, incoming),
            }
            if bool(entry["old_present"]):
                allowed.add((None, old, None, incoming))
            else:
                allowed.add((None, None, None, incoming))
        if physical not in allowed:
            raise InstallationError(
                f"ambiguous transaction state for {name}; recovery evidence retained"
            )


def _validate_terminal_transaction(
    target: Path,
    transaction_root: Path,
    journal: dict[str, object],
    staged: dict[str, str],
    backups: dict[str, str],
    quarantined: dict[str, str],
) -> None:
    entries = journal["skills"]
    assert isinstance(entries, list)
    cleanup = journal["cleanup"]
    assert isinstance(cleanup, dict)
    phase = str(journal["phase"])
    identities_by_container = {
        _STAGING_NAME: staged,
        _BACKUP_NAME: backups,
        _QUARANTINE_NAME: quarantined,
    }
    for container_name, identities in identities_by_container.items():
        state = str(cleanup[container_name])
        exists = (transaction_root / container_name).exists()
        if state == "pending" and not exists:
            raise InstallationError(
                f"pending cleanup container is missing: {container_name}; recovery evidence "
                f"retained at {transaction_root}"
            )
        if state == "deleted" and (exists or identities):
            raise InstallationError(
                f"deleted cleanup container reappeared: {container_name}; recovery evidence "
                f"retained at {transaction_root}"
            )
    if phase == "committed":
        _verify_incoming_generation(target, entries)
        if cleanup[_STAGING_NAME] == "pending" and staged:
            raise InstallationError(
                f"committed transaction still has staged artifacts; recovery evidence "
                f"retained at {transaction_root}"
            )
        if cleanup[_QUARANTINE_NAME] == "pending" and quarantined:
            raise InstallationError(
                f"committed transaction still has quarantine artifacts; recovery evidence "
                f"retained at {transaction_root}"
            )
        if cleanup[_BACKUP_NAME] == "pending":
            expected_backups = {
                str(entry["name"]): str(entry["old_digest"])
                for entry in entries
                if bool(entry["old_present"])
            }
            if backups != expected_backups:
                raise InstallationError(
                    f"committed backup set mismatch; recovery evidence retained at "
                    f"{transaction_root}"
                )
        return
    if phase == "rolled_back":
        _verify_old_generation(target, entries)
        if cleanup[_BACKUP_NAME] == "pending" and backups:
            raise InstallationError(
                f"rolled-back transaction still has backups; recovery evidence retained at "
                f"{transaction_root}"
            )
        pending_incoming: dict[str, str] = {}
        for entry in entries:
            name = str(entry["name"])
            if (
                cleanup[_STAGING_NAME] == "pending"
                and name in staged
                and staged[name] != entry["incoming_digest"]
            ):
                raise InstallationError(
                    f"rolled-back staging mismatch; recovery evidence retained at "
                    f"{transaction_root}"
                )
            if (
                cleanup[_QUARANTINE_NAME] == "pending"
                and name in quarantined
                and quarantined[name] != entry["incoming_digest"]
            ):
                raise InstallationError(
                    f"rolled-back quarantine mismatch; recovery evidence retained at "
                    f"{transaction_root}"
                )
            if (
                cleanup[_STAGING_NAME] == "pending"
                and cleanup[_QUARANTINE_NAME] == "pending"
                and name in staged
                and name in quarantined
            ):
                raise InstallationError(
                    f"duplicated rolled-back incoming payload; recovery evidence retained at "
                    f"{transaction_root}"
                )
            if cleanup[_STAGING_NAME] == "pending" and name in staged:
                pending_incoming[name] = staged[name]
            if cleanup[_QUARANTINE_NAME] == "pending" and name in quarantined:
                pending_incoming[name] = quarantined[name]
        if (
            cleanup[_STAGING_NAME] == "pending"
            and cleanup[_QUARANTINE_NAME] == "pending"
            and set(pending_incoming) != set(SKILL_NAMES)
        ):
            raise InstallationError(
                f"rolled-back incoming artifact set is incomplete; recovery evidence retained "
                f"at {transaction_root}"
            )
        return
    raise InstallationError(
        f"transaction is not terminal; recovery evidence retained at {transaction_root}"
    )


def _cleanup_transaction(target: Path, transaction_root: Path) -> None:
    allowed = {
        INSTALL_TRANSACTION_JOURNAL_NAME,
        _JOURNAL_TEMP_NAME,
        _STAGING_NAME,
        _BACKUP_NAME,
        _QUARANTINE_NAME,
    }
    unexpected = [child for child in transaction_root.iterdir() if child.name not in allowed]
    if unexpected:
        raise InstallationError(
            f"refusing to clean unknown transaction artifacts; recovery evidence retained at "
            f"{transaction_root}"
        )
    transaction_id = transaction_root.name.removeprefix(INSTALL_TRANSACTION_PREFIX)
    garbage_root = target / f"{INSTALL_GC_PREFIX}{transaction_id}"
    if (
        not transaction_id
        or len(transaction_id) != 32
        or any(character not in "0123456789abcdef" for character in transaction_id)
        or garbage_root.exists()
        or garbage_root.is_symlink()
    ):
        raise InstallationError(
            f"refusing ambiguous transaction cleanup; recovery evidence retained at "
            f"{transaction_root}"
        )
    os.replace(transaction_root, garbage_root)
    _fsync_directory(target)
    _cleanup_stale_garbage_root(target, garbage_root)


def _validate_garbage_root(garbage_root: Path) -> None:
    transaction_id = garbage_root.name.removeprefix(INSTALL_GC_PREFIX)
    if (
        garbage_root.is_symlink()
        or not garbage_root.is_dir()
        or len(transaction_id) != 32
        or any(character not in "0123456789abcdef" for character in transaction_id)
    ):
        raise InstallationError(f"unsafe installer garbage path retained at {garbage_root}")
    allowed_top_level = {
        INSTALL_TRANSACTION_JOURNAL_NAME,
        _JOURNAL_TEMP_NAME,
        _STAGING_NAME,
        _BACKUP_NAME,
        _QUARANTINE_NAME,
    }
    for path, metadata in _owned_tree_entries(garbage_root):
        if path.parent == garbage_root and path.name not in allowed_top_level:
            raise InstallationError(f"unknown installer garbage retained at {garbage_root}")


def _cleanup_stale_garbage_root(target: Path, garbage_root: Path) -> None:
    _validate_garbage_root(garbage_root)
    if not any(garbage_root.iterdir()):
        garbage_root.rmdir()
        _fsync_directory(target)
        return
    journal = _load_journal(
        garbage_root,
        target,
        container_prefix=INSTALL_GC_PREFIX,
    )
    phase = str(journal["phase"])
    if phase not in {"committed", "rolled_back"}:
        raise InstallationError(
            f"non-terminal installer garbage retained at {garbage_root}"
        )
    staged, backups, quarantined = _validate_transaction_layout(garbage_root, phase)
    _validate_terminal_transaction(
        target,
        garbage_root,
        journal,
        staged,
        backups,
        quarantined,
    )
    _discard_journal_temporary(garbage_root)
    cleanup = journal["cleanup"]
    assert isinstance(cleanup, dict)
    for container_name in _CLEANUP_CONTAINERS:
        container = garbage_root / container_name
        state = str(cleanup[container_name])
        if state == "pending":
            cleanup[container_name] = "deleting"
            _write_journal(garbage_root, journal)
            state = "deleting"
        if state == "deleting":
            if container.exists():
                _remove_owned_directory(container)
                _fsync_directory(garbage_root)
            cleanup[container_name] = "deleted"
            _write_journal(garbage_root, journal)
        elif state != "deleted":
            raise InstallationError(
                f"unknown cleanup state retained at {garbage_root}"
            )
        if container.exists():
            raise InstallationError(
                f"deleted cleanup container remains at {garbage_root}"
            )
        if state == "deleted":
            _fsync_directory(garbage_root)
    temporary = garbage_root / _JOURNAL_TEMP_NAME
    if temporary.exists():
        _discard_journal_temporary(garbage_root)
    _load_journal(
        garbage_root,
        target,
        container_prefix=INSTALL_GC_PREFIX,
    )
    journal_path = garbage_root / INSTALL_TRANSACTION_JOURNAL_NAME
    journal_metadata = journal_path.lstat()
    if (
        not stat.S_ISREG(journal_metadata.st_mode)
        or journal_metadata.st_nlink != 1
        or journal_metadata.st_dev != garbage_root.lstat().st_dev
    ):
        raise InstallationError(f"unsafe terminal journal retained at {garbage_root}")
    journal_path.unlink()
    _fsync_directory(garbage_root)
    garbage_root.rmdir()
    _fsync_directory(target)


def _cleanup_stale_garbage(target: Path) -> None:
    garbage_roots = sorted(
        (child for child in target.iterdir() if child.name.startswith(INSTALL_GC_PREFIX)),
        key=lambda item: item.name,
    )
    if len(garbage_roots) > 1:
        locations = ", ".join(str(path) for path in garbage_roots)
        raise InstallationError(
            f"multiple installer garbage roots are ambiguous; evidence retained at {locations}"
        )
    for garbage_root in garbage_roots:
        _cleanup_stale_garbage_root(target, garbage_root)


def _rollback_transaction(
    target: Path,
    transaction_root: Path,
    journal: dict[str, object],
    staged: dict[str, str],
    backups: dict[str, str],
    quarantined: dict[str, str],
) -> None:
    entries = journal["skills"]
    assert isinstance(entries, list)
    phase = str(journal["phase"])
    _validate_uncommitted_state(
        target,
        entries,
        staged,
        backups,
        quarantined,
        rolling_back=phase == "rolling_back",
    )
    _discard_journal_temporary(transaction_root)
    if phase == "prepared":
        journal["phase"] = "rolling_back"
        _write_journal(transaction_root, journal)

    for entry in reversed(entries):
        name = str(entry["name"])
        destination = target / name
        backup = transaction_root / _BACKUP_NAME / name
        quarantine = transaction_root / _QUARANTINE_NAME / name
        live_digest = _path_identity(destination)
        backup_digest = _path_identity(backup)
        quarantine_digest = _path_identity(quarantine)
        old_digest = entry["old_digest"]
        incoming_digest = entry["incoming_digest"]
        if bool(entry["old_present"]):
            if live_digest == old_digest and backup_digest is None:
                pass
            elif backup_digest == old_digest:
                if live_digest is not None:
                    if live_digest != incoming_digest or quarantine_digest is not None:
                        raise InstallationError(
                            f"cannot prove incoming live identity for {name}; recovery evidence "
                            f"retained at {transaction_root}"
                        )
                    _replace_path(destination, quarantine)
                    _fsync_directory(target)
                    _fsync_directory(transaction_root / _QUARANTINE_NAME)
                    quarantine_digest = incoming_digest
                if quarantine_digest not in {None, incoming_digest}:
                    raise InstallationError(
                        f"quarantine identity mismatch for {name}; recovery evidence retained at "
                        f"{transaction_root}"
                    )
                _replace_path(backup, destination)
                _fsync_directory(target)
                _fsync_directory(transaction_root / _BACKUP_NAME)
            else:
                raise InstallationError(
                    f"required backup is missing for {name}; recovery evidence retained at "
                    f"{transaction_root}"
                )
        else:
            if backup_digest is not None:
                raise InstallationError(
                    f"unexpected backup for initially absent {name}; recovery evidence retained "
                    f"at {transaction_root}"
                )
            if live_digest is not None:
                if live_digest != incoming_digest or quarantine_digest is not None:
                    raise InstallationError(
                        f"cannot prove incoming absent-state payload for {name}; recovery evidence "
                        f"retained at {transaction_root}"
                    )
                _replace_path(destination, quarantine)
                _fsync_directory(target)
                _fsync_directory(transaction_root / _QUARANTINE_NAME)
                quarantine_digest = incoming_digest
            if quarantine_digest not in {None, incoming_digest}:
                raise InstallationError(
                    f"quarantine identity mismatch for {name}; recovery evidence retained at "
                    f"{transaction_root}"
                )
        entry["progress"] = "restored"
        _discard_journal_temporary(transaction_root)
        _write_journal(transaction_root, journal)

    _verify_old_generation(target, entries)
    journal["phase"] = "rolled_back"
    _write_journal(transaction_root, journal)
    _cleanup_transaction(target, transaction_root)


def _cleanup_unpublished_transaction(target: Path, transaction_root: Path) -> None:
    transaction_id = transaction_root.name.removeprefix(INSTALL_TRANSACTION_PREFIX)
    if (
        not transaction_root.name.startswith(INSTALL_TRANSACTION_PREFIX)
        or len(transaction_id) != 32
        or any(character not in "0123456789abcdef" for character in transaction_id)
        or transaction_root.is_symlink()
        or not transaction_root.is_dir()
    ):
        raise InstallationError(
            f"unsafe unpublished transaction retained at {transaction_root}"
        )
    children = list(transaction_root.iterdir())
    if len(children) > 1 or (
        children and children[0].name != _JOURNAL_TEMP_NAME
    ):
        raise InstallationError(
            f"install transaction has no journal; recovery evidence retained at {transaction_root}"
        )
    for path in [transaction_root, *children]:
        metadata = path.lstat()
        expected_kind = stat.S_ISDIR(metadata.st_mode) if path == transaction_root else stat.S_ISREG(metadata.st_mode)
        if (
            path.is_symlink()
            or not expected_kind
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
            or (stat.S_ISREG(metadata.st_mode) and metadata.st_nlink != 1)
        ):
            raise InstallationError(
                f"unsafe unpublished transaction retained at {transaction_root}"
            )
    _remove_owned_directory(transaction_root)
    _fsync_directory(target)


def _cleanup_building_transaction(
    target: Path,
    transaction_root: Path,
    journal: dict[str, object],
    backups: dict[str, str],
    quarantined: dict[str, str],
) -> None:
    entries = journal["skills"]
    assert isinstance(entries, list)
    if journal["phase"] != "building" or backups or quarantined:
        raise InstallationError(
            f"building transaction is not safe to discard; recovery evidence retained at "
            f"{transaction_root}"
        )
    _verify_old_generation(target, entries)
    for container_name in _CLEANUP_CONTAINERS:
        container = transaction_root / container_name
        if container.exists():
            _remove_owned_directory(container)
            _fsync_directory(transaction_root)
    _discard_journal_temporary(transaction_root)
    _load_journal(transaction_root, target)
    journal_path = transaction_root / INSTALL_TRANSACTION_JOURNAL_NAME
    journal_metadata = journal_path.lstat()
    if (
        not stat.S_ISREG(journal_metadata.st_mode)
        or journal_metadata.st_nlink != 1
        or journal_metadata.st_dev != transaction_root.lstat().st_dev
    ):
        raise InstallationError(
            f"unsafe building journal retained at {transaction_root}"
        )
    journal_path.unlink()
    _fsync_directory(transaction_root)
    transaction_root.rmdir()
    _fsync_directory(target)


def _recover_existing_transaction(target: Path) -> str | None:
    transaction_roots = sorted(
        (
            child
            for child in target.iterdir()
            if child.name.startswith(INSTALL_TRANSACTION_PREFIX)
        ),
        key=lambda item: item.name,
    )
    if len(transaction_roots) > 1:
        locations = ", ".join(str(path) for path in transaction_roots)
        raise InstallationError(
            f"multiple unfinished install transactions; recovery evidence retained at {locations}"
        )
    if not transaction_roots:
        return None
    transaction_root = transaction_roots[0]
    if transaction_root.is_symlink() or not transaction_root.is_dir():
        raise InstallationError(
            f"unsafe install transaction path; recovery evidence retained at {transaction_root}"
        )
    journal_path = transaction_root / INSTALL_TRANSACTION_JOURNAL_NAME
    if not journal_path.exists() and not journal_path.is_symlink():
        _cleanup_unpublished_transaction(target, transaction_root)
        return "cleaned"

    _fsync_directory(transaction_root)
    journal = _load_journal(transaction_root, target)
    phase = str(journal["phase"])
    staged, backups, quarantined = _validate_transaction_layout(transaction_root, phase)
    entries = journal["skills"]
    assert isinstance(entries, list)

    if phase == "building":
        _cleanup_building_transaction(
            target,
            transaction_root,
            journal,
            backups,
            quarantined,
        )
        return "rolled_back"
    if phase in {"prepared", "rolling_back"}:
        _rollback_transaction(
            target,
            transaction_root,
            journal,
            staged,
            backups,
            quarantined,
        )
        return "rolled_back"
    if phase == "rolled_back":
        _validate_terminal_transaction(
            target,
            transaction_root,
            journal,
            staged,
            backups,
            quarantined,
        )
        _cleanup_transaction(target, transaction_root)
        return "rolled_back"
    if phase == "committed":
        _validate_terminal_transaction(
            target,
            transaction_root,
            journal,
            staged,
            backups,
            quarantined,
        )
        _cleanup_transaction(target, transaction_root)
        return "committed"
    raise InstallationError(
        f"unknown transaction phase; recovery evidence retained at {transaction_root}"
    )


def _validate_source(source_root: Path) -> dict[str, list[Path]]:
    source_root = source_root.resolve(strict=True)
    undeclared = sorted(
        path.name
        for path in source_root.glob("ksrf-*")
        if path.is_dir() and path.name not in SKILL_NAMES
    )
    if undeclared:
        raise InstallationError(f"undeclared bundled skills: {', '.join(undeclared)}")

    files_by_skill: dict[str, list[Path]] = {}
    for skill_name in SKILL_NAMES:
        skill_root = source_root / skill_name
        if skill_root.is_symlink():
            raise InstallationError(f"refusing symlinked source skill: {skill_root}")
        if not skill_root.is_dir() or not (skill_root / "SKILL.md").is_file():
            raise InstallationError(f"required source skill is missing: {skill_root}")
        try:
            files_by_skill[skill_name] = payload_files(skill_root)
        except FileContractError as exc:
            raise InstallationError(str(exc)) from exc
    return files_by_skill


def _validate_target(target: Path) -> Path:
    target = _absolute_without_resolving(target)
    root = Path(target.anchor)
    home = Path.home().resolve()
    if target == root or target.resolve(strict=False) == home:
        raise InstallationError(f"refusing broad install target: {target}")
    if target.is_symlink():
        raise InstallationError(f"refusing symlinked install target: {target}")
    if target.exists() and not target.is_dir():
        raise InstallationError(f"install target exists and is not a directory: {target}")
    for skill_name in SKILL_NAMES:
        destination = target / skill_name
        if destination.is_symlink():
            raise InstallationError(f"refusing symlinked skill destination: {destination}")
        if destination.exists() and not destination.is_dir():
            raise InstallationError(
                f"skill destination exists and is not a directory: {destination}"
            )
    return target


def _validate_copy_boundaries(source_root: Path, target: Path) -> None:
    """Refuse copies that could replace or nest inside their own source tree."""

    resolved_source = source_root.resolve(strict=False)
    resolved_target = _absolute_without_resolving(target).resolve(strict=False)
    if resolved_source.is_relative_to(resolved_target) or resolved_target.is_relative_to(
        resolved_source
    ):
        raise InstallationError(
            "source and target paths overlap: "
            f"source={resolved_source}, target={resolved_target}"
        )


def copy_skillset(
    source_root: Path,
    target: Path,
    *,
    preserve_target_development: bool = False,
) -> Path:
    """Install one verified generation with a lock, journal, backup, and recovery."""

    source_root = _absolute_without_resolving(source_root)
    target = _validate_target(target)
    reported_target = target
    _validate_copy_boundaries(source_root, target)
    target.mkdir(parents=True, exist_ok=True)
    actual_target = target.resolve(strict=True)
    _validate_target(actual_target)
    target = actual_target

    with _target_install_lock(target) as anchor:
        anchor.assert_current()
        _validate_target(target)
        _recover_existing_transaction(target)
        anchor.assert_current()
        _cleanup_stale_garbage(target)
        anchor.assert_current()

        source_root = source_root.resolve(strict=True)
        _validate_copy_boundaries(source_root, target)
        files_by_skill = _validate_source(source_root)
        anchor.assert_current()

        preserved_by_skill: dict[str, list[Path]] = {}
        for skill_name in SKILL_NAMES:
            destination = target / skill_name
            try:
                preserved_by_skill[skill_name] = (
                    development_files(destination)
                    if preserve_target_development and destination.exists()
                    else []
                )
            except FileContractError as exc:
                raise InstallationError(str(exc)) from exc

        entries: list[dict[str, object]] = []
        for skill_name in SKILL_NAMES:
            anchor.assert_current()
            destination = target / skill_name
            old_digest = _path_identity(destination)
            entries.append(
                {
                    "name": skill_name,
                    "old_present": old_digest is not None,
                    "old_digest": old_digest,
                    "incoming_digest": None,
                    "progress": "pending",
                }
            )

        transaction_id = uuid4().hex
        transaction_root = target / f"{INSTALL_TRANSACTION_PREFIX}{transaction_id}"
        journal: dict[str, object] = {
            "schema_version": _JOURNAL_SCHEMA_VERSION,
            "transaction_id": transaction_id,
            "target": str(target),
            "target_device": target.stat().st_dev,
            "target_inode": target.stat().st_ino,
            "phase": "building",
            "skill_names": list(SKILL_NAMES),
            "old_aggregate": _aggregate_identity(entries, "old_digest"),
            "incoming_aggregate": None,
            "skills": entries,
            "cleanup": {name: "pending" for name in _CLEANUP_CONTAINERS},
        }

        anchor.assert_current()
        transaction_root.mkdir(mode=0o700)
        _fsync_directory(target)
        anchor.assert_current()
        try:
            _write_journal(transaction_root, journal)
            anchor.assert_current()
            staging_parent = transaction_root / _STAGING_NAME
            backup_parent = transaction_root / _BACKUP_NAME
            quarantine_parent = transaction_root / _QUARANTINE_NAME
            staging_parent.mkdir()
            backup_parent.mkdir()
            quarantine_parent.mkdir()
            _fsync_directory(transaction_root)
            anchor.assert_current()
            target_device = target.stat().st_dev
            if any(
                path.stat().st_dev != target_device
                for path in (
                    transaction_root,
                    staging_parent,
                    backup_parent,
                    quarantine_parent,
                )
            ):
                raise InstallationError("transaction paths are not on the target filesystem")

            for entry in entries:
                anchor.assert_current()
                skill_name = str(entry["name"])
                source_skill = source_root / skill_name
                staged_skill = staging_parent / skill_name
                staged_skill.mkdir()
                for source_file in files_by_skill[skill_name]:
                    relative = source_file.relative_to(source_skill)
                    staged_file = staged_skill / relative
                    staged_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, staged_file)

                destination = target / skill_name
                for preserved_file in preserved_by_skill[skill_name]:
                    relative = preserved_file.relative_to(destination)
                    staged_file = staged_skill / relative
                    if staged_file.exists():
                        raise InstallationError(
                            f"development path collides with runtime payload: "
                            f"{skill_name}/{relative}"
                        )
                    staged_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(preserved_file, staged_file)

                _fsync_tree(staged_skill)
                staged_files = payload_files(staged_skill)
                source_relatives = [
                    path.relative_to(source_skill).as_posix()
                    for path in files_by_skill[skill_name]
                ]
                staged_relatives = [
                    path.relative_to(staged_skill).as_posix() for path in staged_files
                ]
                if source_relatives != staged_relatives or tree_digest(
                    source_skill, files_by_skill[skill_name]
                ) != tree_digest(staged_skill, staged_files):
                    raise InstallationError(
                        f"staged payload verification failed: {skill_name}"
                    )

                if preserve_target_development:
                    staged_development = development_files(staged_skill)
                    preserved_relatives = [
                        path.relative_to(destination).as_posix()
                        for path in preserved_by_skill[skill_name]
                    ]
                    staged_development_relatives = [
                        path.relative_to(staged_skill).as_posix()
                        for path in staged_development
                    ]
                    if preserved_relatives != staged_development_relatives or tree_digest(
                        destination, preserved_by_skill[skill_name]
                    ) != tree_digest(staged_skill, staged_development):
                        raise InstallationError(
                            f"staged development preservation failed: {skill_name}"
                        )
                entry["incoming_digest"] = _directory_identity(staged_skill)
                anchor.assert_current()

            _fsync_directory(staging_parent)
            journal["incoming_aggregate"] = _aggregate_identity(
                entries,
                "incoming_digest",
            )
            journal["phase"] = "prepared"
            _write_journal(transaction_root, journal)
            anchor.assert_current()

            for entry in entries:
                skill_name = str(entry["name"])
                destination = target / skill_name
                staged_skill = staging_parent / skill_name
                backup = backup_parent / skill_name

                anchor.assert_current()
                if _path_identity(destination) != entry["old_digest"]:
                    raise InstallationError(
                        f"managed destination changed after snapshot: {skill_name}; transaction "
                        f"evidence retained at {transaction_root}"
                    )
                entry["progress"] = "backing_up"
                _write_journal(transaction_root, journal)
                anchor.assert_current()
                if bool(entry["old_present"]):
                    _replace_path(destination, backup)
                    _fsync_directory(target)
                    _fsync_directory(backup_parent)
                    anchor.assert_current()
                    if _path_identity(backup) != entry["old_digest"]:
                        raise InstallationError(
                            f"backup identity changed during placement: {skill_name}; transaction "
                            f"evidence retained at {transaction_root}"
                        )
                elif _path_identity(destination) is not None:
                    raise InstallationError(
                        f"initially absent destination appeared during install: {skill_name}; "
                        f"transaction evidence retained at {transaction_root}"
                    )
                entry["progress"] = "backed_up"
                _write_journal(transaction_root, journal)
                anchor.assert_current()

                entry["progress"] = "placing"
                _write_journal(transaction_root, journal)
                anchor.assert_current()
                if _path_identity(staged_skill) != entry["incoming_digest"]:
                    raise InstallationError(
                        f"staged identity changed before placement: {skill_name}; transaction "
                        f"evidence retained at {transaction_root}"
                    )
                _replace_path(staged_skill, destination)
                _fsync_directory(target)
                _fsync_directory(staging_parent)
                anchor.assert_current()
                if _path_identity(destination) != entry["incoming_digest"]:
                    raise InstallationError(
                        f"live identity changed during placement: {skill_name}; transaction "
                        f"evidence retained at {transaction_root}"
                    )
                entry["progress"] = "placed"
                _write_journal(transaction_root, journal)
                anchor.assert_current()

            anchor.assert_current()
            _verify_incoming_generation(target, entries)
            if journal["incoming_aggregate"] != _aggregate_identity(
                [
                    {
                        **entry,
                        "incoming_digest": _target_state(target, entry),
                    }
                    for entry in entries
                ],
                "incoming_digest",
            ):
                raise InstallationError("aggregate installed generation verification failed")
            journal["phase"] = "committed"
            _write_journal(transaction_root, journal)
            anchor.assert_current()
            _cleanup_transaction(target, transaction_root)
            anchor.assert_current()
        except (Exception, KeyboardInterrupt) as install_error:
            if isinstance(install_error, JournalDurabilityError) and journal.get("phase") == "committed":
                raise InstallationError(
                    f"installation reached an unconfirmed commit marker; no success is reported "
                    f"and recovery evidence is retained at {transaction_root}"
                ) from install_error
            try:
                anchor.assert_current()
            except (Exception, KeyboardInterrupt) as anchor_error:
                raise InstallationError(
                    f"installation target identity changed; automatic recovery was not attempted "
                    f"against a different path: {anchor_error}"
                ) from install_error
            try:
                _recover_existing_transaction(target)
            except (Exception, KeyboardInterrupt) as recovery_error:
                raise InstallationError(
                    f"installation failed and automatic rollback is incomplete; recovery "
                    f"evidence retained at {transaction_root}: {recovery_error}"
                ) from install_error
            raise
        return reported_target


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo", type=Path)
    source.add_argument("--source-skills-root", type=Path)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--preserve-target-development", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source_root = args.repo / "skills" if args.repo is not None else args.source_skills_root
    assert source_root is not None
    try:
        if args.preserve_target_development and args.source_skills_root is None:
            raise InstallationError(
                "--preserve-target-development requires --source-skills-root"
            )
        target = copy_skillset(
            source_root,
            args.target,
            preserve_target_development=args.preserve_target_development,
        )
    except (InstallationError, FileNotFoundError, OSError) as exc:
        print(f"Skillset installation refused: {exc}", file=sys.stderr)
        return 1
    if args.preserve_target_development:
        print(
            "Synchronized exact KSRF runtime payload while preserving "
            f"target development files in {target}"
        )
    else:
        print(f"Installed exact manifest-covered KSRF skill payload into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
