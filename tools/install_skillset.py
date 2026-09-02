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

# The read-only status mode must not mutate even the source checkout when this
# script is invoked directly.  Set this before importing local helper modules.
sys.dont_write_bytecode = True

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


class _ObservationChanged(RuntimeError):
    """A read-only status observation changed while it was being sampled."""


class _InvalidEvidence(InstallationError):
    """A deterministic evidence validation failure with a comparable snapshot."""

    def __init__(self, fingerprint: str) -> None:
        super().__init__("installer evidence failed validation")
        self.fingerprint = fingerprint


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

_STATUS_SCHEMA_VERSION = "1.0"
_STATUS_SCAN_MAX_ENTRIES = 20_000
_STATUS_SCAN_MAX_DEPTH = 64
_STATUS_SCAN_MAX_FILE_BYTES = 32 * 1024 * 1024
_STATUS_SCAN_MAX_TOTAL_BYTES = 128 * 1024 * 1024
_STATUS_JOURNAL_MAX_BYTES = 1024 * 1024
_STATUS_FDINFO_MAX_BYTES = 16 * 1024
_STATUS_FD_PATH_MAX_BYTES = 1024
_STATUS_MOUNT_BOUNDARY: ContextVar[tuple[str, int | None] | None] = ContextVar(
    "ksrf_status_mount_boundary",
    default=None,
)


def _status_public_text(value: str) -> str:
    """Render unpaired filesystem surrogates as printable ASCII escapes."""

    rendered: list[str] = []
    for character in value:
        codepoint = ord(character)
        if 0xDC80 <= codepoint <= 0xDCFF:
            rendered.append(f"\\x{codepoint - 0xDC00:02x}")
        elif 0xD800 <= codepoint <= 0xDFFF:
            rendered.append(f"\\u{codepoint:04x}")
        else:
            rendered.append(character)
    return "".join(rendered)


class _StatusScanBudget:
    """Bound one complete unlocked observation before reading file payloads."""

    def __init__(self) -> None:
        self.entries = 0
        self.total_bytes = 0
        self._trace = sha256()

    @property
    def remaining_entries(self) -> int:
        return _STATUS_SCAN_MAX_ENTRIES - self.entries

    def observe(
        self,
        components: tuple[str, ...],
        metadata: os.stat_result,
        *,
        role: str = "entry",
    ) -> None:
        """Bind even rejected entries into a comparable failure observation."""

        self._trace.update(
            repr((role, components, _status_metadata_tuple(metadata))).encode(
                "utf-8",
                "backslashreplace",
            )
        )

    def account(self, components: tuple[str, ...], metadata: os.stat_result) -> None:
        self.observe(components, metadata)
        if len(components) > _STATUS_SCAN_MAX_DEPTH:
            raise InstallationError("status observation depth budget exceeded")
        self.entries += 1
        if self.entries > _STATUS_SCAN_MAX_ENTRIES:
            raise InstallationError("status observation entry budget exceeded")
        if not stat.S_ISREG(metadata.st_mode):
            return
        size = metadata.st_size
        if size < 0 or size > _STATUS_SCAN_MAX_FILE_BYTES:
            raise InstallationError("status observation file budget exceeded")
        self.total_bytes += size
        if self.total_bytes > _STATUS_SCAN_MAX_TOTAL_BYTES:
            raise InstallationError("status observation byte budget exceeded")

    def failure_fingerprint(self, exc: BaseException) -> str:
        """Return a stable internal identity for one bounded failed sample."""

        failure = sha256()
        failure.update(self._trace.digest())
        failure.update(
            repr(
                (
                    type(exc).__name__,
                    getattr(exc, "errno", None),
                    str(exc),
                    self.entries,
                    self.total_bytes,
                )
            ).encode("utf-8", "backslashreplace")
        )
        return failure.hexdigest()


_STATUS_EXIT_CODES = {
    "clean": 0,
    "not_installed": 10,
    "incomplete": 20,
    "recovery_required": 20,
    "unsafe": 30,
}
_STATUS_SEVERITIES = {
    "clean": "ok",
    "not_installed": "info",
    "incomplete": "warning",
    "recovery_required": "warning",
    "unsafe": "error",
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
        not isinstance(cleanup[name], str)
        or cleanup[name] not in _CLEANUP_STATES
        for name in _CLEANUP_CONTAINERS
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
    except (
        InstallationError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        OSError,
        RecursionError,
        ValueError,
    ) as exc:
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
    phase_value = journal["phase"]
    if (
        not isinstance(journal["schema_version"], int)
        or isinstance(journal["schema_version"], bool)
        or journal["schema_version"] != _JOURNAL_SCHEMA_VERSION
        or not transaction_id
        or not isinstance(journal["transaction_id"], str)
        or journal["transaction_id"] != transaction_id
        or not isinstance(journal["target"], str)
        or journal["target"] != str(target.resolve(strict=True))
        or not isinstance(journal["target_device"], int)
        or isinstance(journal["target_device"], bool)
        or journal["target_device"] != target_metadata.st_dev
        or not isinstance(journal["target_inode"], int)
        or isinstance(journal["target_inode"], bool)
        or journal["target_inode"] != target_metadata.st_ino
        or not isinstance(phase_value, str)
        or phase_value not in _JOURNAL_PHASES
        or not isinstance(journal["skill_names"], list)
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
        progress = entry["progress"]
        if (
            not isinstance(entry["name"], str)
            or entry["name"] != expected_name
            or not isinstance(old_present, bool)
            or not isinstance(progress, str)
            or progress not in _PROGRESS_STATES
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


def _validate_unpublished_transaction(transaction_root: Path) -> list[Path]:
    """Validate a transaction created before its durable journal, without changing it."""

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
    return children


def _cleanup_unpublished_transaction(target: Path, transaction_root: Path) -> None:
    children = _validate_unpublished_transaction(transaction_root)
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


def _status_metadata_tuple(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        stat.S_IMODE(metadata.st_mode),
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _status_same_object(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        stat.S_IFMT(left.st_mode),
    ) == (
        right.st_dev,
        right.st_ino,
        stat.S_IFMT(right.st_mode),
    )


def _status_directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _status_file_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _status_bounded_names(
    descriptor: int,
    *,
    budget: _StatusScanBudget | None = None,
) -> list[str]:
    limit = (
        _STATUS_SCAN_MAX_ENTRIES
        if budget is None
        else max(0, budget.remaining_entries)
    )
    names: list[str] = []
    try:
        with os.scandir(descriptor) as entries:
            for entry in entries:
                names.append(entry.name)
                if len(names) > limit:
                    raise InstallationError(
                        "status observation entry budget exceeded"
                    )
    except OSError as exc:
        raise InstallationError("cannot list status directory") from exc
    return sorted(names)


def _status_linux_mountinfo_available() -> bool:
    return Path("/proc/self/mountinfo").is_file()


def _status_linux_fd_mount_id(descriptor: int) -> int | None:
    """Read one kernel-owned Linux mount ID without following a path payload."""

    fdinfo = f"/proc/self/fdinfo/{descriptor}"
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        info_descriptor = os.open(fdinfo, flags)
    except OSError:
        return None
    try:
        chunks: list[bytes] = []
        remaining = _STATUS_FDINFO_MAX_BYTES + 1
        while remaining:
            chunk = os.read(info_descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
    except OSError:
        return None
    finally:
        os.close(info_descriptor)
    if len(raw) > _STATUS_FDINFO_MAX_BYTES:
        return None
    try:
        lines = raw.decode("ascii", errors="strict").splitlines()
    except UnicodeDecodeError:
        return None
    values = [
        line.removeprefix("mnt_id:").strip()
        for line in lines
        if line.startswith("mnt_id:")
    ]
    if (
        len(values) != 1
        or not values[0].isdigit()
        or len(values[0]) > 20
    ):
        return None
    try:
        return int(values[0])
    except ValueError:
        return None


def _status_capture_mount_boundary(
    target_descriptor: int,
) -> tuple[str, int | None]:
    if not _status_linux_mountinfo_available():
        return ("path_ismount_only", None)
    mount_id = _status_linux_fd_mount_id(target_descriptor)
    if mount_id is None:
        return ("live_mountinfo_fallback", None)
    return ("linux_mnt_id", mount_id)


def _status_mount_boundary_fingerprint() -> str:
    boundary = _STATUS_MOUNT_BOUNDARY.get()
    if boundary is None:
        return "standalone"
    return sha256(repr(boundary).encode("ascii")).hexdigest()


def _status_bind_mount_fingerprint(fingerprint: str) -> str:
    combined = sha256()
    combined.update(_status_mount_boundary_fingerprint().encode("ascii"))
    combined.update(fingerprint.encode("ascii"))
    return combined.hexdigest()


def _status_fd_is_mount(descriptor: int) -> bool:
    candidates: list[str] = []
    proc_path = f"/proc/self/fd/{descriptor}"
    try:
        candidates.append(os.readlink(proc_path))
    except OSError:
        pass
    dev_path = f"/dev/fd/{descriptor}"
    try:
        candidates.append(str(Path(dev_path).resolve(strict=True)))
    except OSError:
        pass
    get_path = getattr(fcntl, "F_GETPATH", None)
    if get_path is not None:
        try:
            raw_path = fcntl.fcntl(
                descriptor,
                get_path,
                b"\0" * _STATUS_FD_PATH_MAX_BYTES,
            )
            encoded_path = raw_path.split(b"\0", 1)[0]
            if encoded_path:
                candidates.append(os.fsdecode(encoded_path))
        except OSError:
            pass
    boundary = _STATUS_MOUNT_BOUNDARY.get()
    if boundary is None:
        linux_mounts = _linux_mount_points()
    elif boundary[0] == "linux_mnt_id":
        current_mount_id = _status_linux_fd_mount_id(descriptor)
        if current_mount_id is None or current_mount_id != boundary[1]:
            return True
        linux_mounts = set()
    elif boundary[0] == "live_mountinfo_fallback":
        linux_mounts = _linux_mount_points()
    else:
        linux_mounts = set()
    return any(os.path.ismount(path) or path in linux_mounts for path in candidates)


def _status_open_directory_at(
    parent_descriptor: int,
    name: str,
    *,
    expected_device: int,
) -> tuple[int, os.stat_result]:
    before = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if not stat.S_ISDIR(before.st_mode):
        raise InstallationError(f"status path is not a safe directory: {name}")
    if before.st_dev != expected_device:
        raise InstallationError(f"status path crosses a device boundary: {name}")
    descriptor = os.open(
        name,
        _status_directory_flags(),
        dir_fd=parent_descriptor,
    )
    try:
        anchored = os.fstat(descriptor)
        if not _status_same_object(before, anchored):
            raise _ObservationChanged(f"directory changed while opening: {name}")
        if _status_fd_is_mount(descriptor):
            raise InstallationError(f"status path is a mount boundary: {name}")
        return descriptor, anchored
    except BaseException:
        os.close(descriptor)
        raise


def _status_read_regular_at(
    parent_descriptor: int,
    name: str,
    *,
    expected_device: int,
    capture_limit: int | None = None,
) -> tuple[bytes | None, str, tuple[int, ...]]:
    before = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_dev != expected_device
        or before.st_nlink != 1
    ):
        raise InstallationError(f"status file is unsafe: {name}")
    if capture_limit is not None and before.st_size > capture_limit:
        raise InstallationError(f"status file is unreasonably large: {name}")
    descriptor = os.open(name, _status_file_flags(), dir_fd=parent_descriptor)
    content = bytearray() if capture_limit is not None else None
    content_digest = sha256()
    try:
        anchored = os.fstat(descriptor)
        if not _status_same_object(before, anchored):
            raise _ObservationChanged(f"file changed while opening: {name}")
        remaining = anchored.st_size
        while chunk := os.read(
            descriptor,
            min(1024 * 1024, remaining + 1),
        ):
            if len(chunk) > remaining:
                raise _ObservationChanged(f"file grew while reading: {name}")
            content_digest.update(chunk)
            remaining -= len(chunk)
            if content is not None:
                content.extend(chunk)
                if len(content) > capture_limit:
                    raise InstallationError(f"status file is unreasonably large: {name}")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if _status_metadata_tuple(before) != _status_metadata_tuple(after):
        raise _ObservationChanged(f"file changed while reading: {name}")
    return (
        bytes(content) if content is not None else None,
        content_digest.hexdigest(),
        _status_metadata_tuple(after),
    )


def _status_scan_open_directory(
    descriptor: int,
    *,
    expected_device: int,
    budget: _StatusScanBudget | None = None,
) -> tuple[str, str]:
    """Return transaction-compatible content identity plus inode-bound observation."""

    if budget is None:
        budget = _StatusScanBudget()
    records: list[tuple[tuple[str, ...], os.stat_result]] = []
    directory_metadata: dict[tuple[str, ...], os.stat_result] = {}

    def collect_directory(
        current_descriptor: int,
        components: tuple[str, ...],
        expected_metadata: os.stat_result,
    ) -> None:
        directory_before = os.fstat(current_descriptor)
        relative = "." if not components else "/".join(components)
        if (
            not stat.S_ISDIR(directory_before.st_mode)
            or directory_before.st_dev != expected_device
        ):
            raise InstallationError(f"unsafe directory in status observation: {relative}")
        if _status_metadata_tuple(expected_metadata) != _status_metadata_tuple(
            directory_before
        ):
            raise _ObservationChanged(
                f"directory changed before status scan: {relative}"
            )
        budget.account(components, directory_before)
        records.append((components, directory_before))
        directory_metadata[components] = directory_before
        names = _status_bounded_names(current_descriptor, budget=budget)
        for name in names:
            child_components = (*components, name)
            child_relative = "/".join(child_components)
            metadata = os.stat(
                name,
                dir_fd=current_descriptor,
                follow_symlinks=False,
            )
            if stat.S_ISLNK(metadata.st_mode):
                raise InstallationError(f"refusing symlink in status tree: {child_relative}")
            if metadata.st_dev != expected_device:
                raise InstallationError(
                    f"refusing device boundary in status tree: {child_relative}"
                )
            if stat.S_ISDIR(metadata.st_mode):
                child_descriptor, anchored = _status_open_directory_at(
                    current_descriptor,
                    name,
                    expected_device=expected_device,
                )
                try:
                    if _status_metadata_tuple(metadata) != _status_metadata_tuple(
                        anchored
                    ):
                        raise _ObservationChanged(
                            f"directory changed during status scan: {child_relative}"
                        )
                    collect_directory(
                        child_descriptor,
                        child_components,
                        anchored,
                    )
                finally:
                    os.close(child_descriptor)
                continue
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise InstallationError(
                    f"refusing special or hard-linked status entry: {child_relative}"
                )
            budget.account(child_components, metadata)
            records.append((child_components, metadata))

        directory_after = os.fstat(current_descriptor)
        if _status_metadata_tuple(directory_before) != _status_metadata_tuple(
            directory_after
        ):
            raise _ObservationChanged(f"directory changed while reading: {relative}")

    root_metadata = os.fstat(descriptor)
    try:
        collect_directory(descriptor, (), root_metadata)
    except RecursionError as exc:
        raise InstallationError("status evidence tree is too deep") from exc

    def open_anchored_directory(components: tuple[str, ...]) -> int:
        current_descriptor = os.dup(descriptor)
        try:
            if _status_metadata_tuple(directory_metadata[()]) != _status_metadata_tuple(
                os.fstat(current_descriptor)
            ):
                raise _ObservationChanged("status tree root changed")
            for index, name in enumerate(components):
                child_descriptor, anchored = _status_open_directory_at(
                    current_descriptor,
                    name,
                    expected_device=expected_device,
                )
                os.close(current_descriptor)
                current_descriptor = child_descriptor
                expected = directory_metadata[components[: index + 1]]
                if _status_metadata_tuple(expected) != _status_metadata_tuple(
                    anchored
                ):
                    raise _ObservationChanged(
                        f"directory changed while reopening: {'/'.join(components[: index + 1])}"
                    )
            return current_descriptor
        except BaseException:
            os.close(current_descriptor)
            raise

    semantic = sha256()
    observation = sha256()
    for components, metadata in sorted(
        records,
        key=lambda item: "." if not item[0] else "/".join(item[0]),
    ):
        relative = "." if not components else "/".join(components)
        try:
            encoded = relative.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InstallationError("status evidence path is not valid UTF-8") from exc
        if stat.S_ISDIR(metadata.st_mode):
            current_descriptor = open_anchored_directory(components)
            try:
                current = os.fstat(current_descriptor)
            finally:
                os.close(current_descriptor)
            if _status_metadata_tuple(metadata) != _status_metadata_tuple(current):
                raise _ObservationChanged(
                    f"directory changed during identity scan: {relative}"
                )
            semantic.update(b"D")
            semantic.update(len(encoded).to_bytes(4, "big"))
            semantic.update(encoded)
            semantic.update(stat.S_IMODE(current.st_mode).to_bytes(4, "big"))
            observation.update(
                repr((relative, _status_metadata_tuple(current))).encode()
            )
            continue

        parent_descriptor = open_anchored_directory(components[:-1])
        try:
            current = os.stat(
                components[-1],
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if _status_metadata_tuple(metadata) != _status_metadata_tuple(current):
                raise _ObservationChanged(
                    f"file changed before identity scan: {relative}"
                )
            file_descriptor = os.open(
                components[-1],
                _status_file_flags(),
                dir_fd=parent_descriptor,
            )
            file_digest = sha256()
            try:
                anchored = os.fstat(file_descriptor)
                if _status_metadata_tuple(current) != _status_metadata_tuple(anchored):
                    raise _ObservationChanged(f"file changed while opening: {relative}")
                semantic.update(b"F")
                semantic.update(len(encoded).to_bytes(4, "big"))
                semantic.update(encoded)
                semantic.update(stat.S_IMODE(anchored.st_mode).to_bytes(4, "big"))
                semantic.update(anchored.st_size.to_bytes(8, "big"))
                remaining = anchored.st_size
                while chunk := os.read(
                    file_descriptor,
                    min(1024 * 1024, remaining + 1),
                ):
                    if len(chunk) > remaining:
                        raise _ObservationChanged(
                            f"file grew while reading: {relative}"
                        )
                    semantic.update(chunk)
                    file_digest.update(chunk)
                    remaining -= len(chunk)
                file_after = os.fstat(file_descriptor)
            finally:
                os.close(file_descriptor)
        finally:
            os.close(parent_descriptor)
        if _status_metadata_tuple(metadata) != _status_metadata_tuple(file_after):
            raise _ObservationChanged(f"file changed while reading: {relative}")
        observation.update(
            repr(
                (
                    relative,
                    _status_metadata_tuple(file_after),
                    file_digest.hexdigest(),
                )
            ).encode()
        )

    if _status_metadata_tuple(root_metadata) != _status_metadata_tuple(
        os.fstat(descriptor)
    ):
        raise _ObservationChanged("status tree root changed during identity scan")
    return semantic.hexdigest(), observation.hexdigest()


def _status_top_level_snapshot(
    target_descriptor: int,
    *,
    target_device: int,
) -> tuple[dict[str, tuple[int, ...]], dict[str, object]]:
    relevant_names = set(SKILL_NAMES) | {INSTALL_LOCK_FILE_NAME}
    names = _status_bounded_names(target_descriptor)
    relevant_names.update(
        name
        for name in names
        if name.startswith(INSTALL_TRANSACTION_PREFIX)
        or name.startswith(INSTALL_GC_PREFIX)
    )
    snapshot: dict[str, tuple[int, ...]] = {}
    present: list[str] = []
    for name in sorted(relevant_names):
        try:
            metadata = os.stat(
                name,
                dir_fd=target_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            continue
        snapshot[name] = _status_metadata_tuple(metadata)
        if name == INSTALL_LOCK_FILE_NAME:
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o022
                or metadata.st_dev != target_device
            ):
                raise InstallationError("existing installer lock metadata is unsafe")
            descriptor = os.open(
                name,
                _status_file_flags(),
                dir_fd=target_descriptor,
            )
            try:
                if not _status_same_object(metadata, os.fstat(descriptor)):
                    raise _ObservationChanged("installer lock changed while opening")
            finally:
                os.close(descriptor)
            continue
        if name in SKILL_NAMES:
            descriptor, anchored = _status_open_directory_at(
                target_descriptor,
                name,
                expected_device=target_device,
            )
            try:
                if not _status_same_object(metadata, anchored):
                    raise _ObservationChanged(f"managed skill changed while opening: {name}")
            finally:
                os.close(descriptor)
            present.append(name)
            continue
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_dev != target_device:
            raise InstallationError(f"installer evidence path is unsafe: {name}")
    missing = [name for name in SKILL_NAMES if name not in present]
    return snapshot, {
        "expected": len(SKILL_NAMES),
        "present": len(present),
        "missing": missing,
    }


def _status_parse_journal(
    raw: bytes,
    *,
    root_name: str,
    container_prefix: str,
    target_path: str,
    target_metadata: os.stat_result,
) -> dict[str, object]:
    try:
        journal = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_json_object_without_duplicates,
        )
    except (
        InstallationError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        RecursionError,
        ValueError,
    ) as exc:
        raise InstallationError(f"transaction journal is corrupt: {exc}") from exc
    if not isinstance(journal, dict):
        raise InstallationError("transaction journal is not an object")
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
        raise InstallationError("transaction journal fields are incomplete or unknown")
    transaction_id = root_name.removeprefix(container_prefix)
    phase_value = journal["phase"]
    if (
        not root_name.startswith(container_prefix)
        or len(transaction_id) != 32
        or any(character not in "0123456789abcdef" for character in transaction_id)
        or not isinstance(journal["schema_version"], int)
        or isinstance(journal["schema_version"], bool)
        or journal["schema_version"] != _JOURNAL_SCHEMA_VERSION
        or not isinstance(journal["transaction_id"], str)
        or journal["transaction_id"] != transaction_id
        or not isinstance(journal["target"], str)
        or journal["target"] != target_path
        or not isinstance(journal["target_device"], int)
        or isinstance(journal["target_device"], bool)
        or journal["target_device"] != target_metadata.st_dev
        or not isinstance(journal["target_inode"], int)
        or isinstance(journal["target_inode"], bool)
        or journal["target_inode"] != target_metadata.st_ino
        or not isinstance(phase_value, str)
        or phase_value not in _JOURNAL_PHASES
        or not isinstance(journal["skill_names"], list)
        or journal["skill_names"] != list(SKILL_NAMES)
    ):
        raise InstallationError("transaction journal identity, schema, target, or phase mismatch")

    raw_entries = journal["skills"]
    if not isinstance(raw_entries, list) or len(raw_entries) != len(SKILL_NAMES):
        raise InstallationError("transaction journal managed set is incomplete")
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
            raise InstallationError("transaction journal skill entry is corrupt")
        old_present = raw_entry["old_present"]
        progress = raw_entry["progress"]
        if (
            not isinstance(raw_entry["name"], str)
            or raw_entry["name"] != expected_name
            or not isinstance(old_present, bool)
            or not isinstance(progress, str)
            or progress not in _PROGRESS_STATES
            or (old_present and not _is_digest(raw_entry["old_digest"]))
            or (not old_present and raw_entry["old_digest"] is not None)
            or (
                raw_entry["incoming_digest"] is not None
                and not _is_digest(raw_entry["incoming_digest"])
            )
        ):
            raise InstallationError("transaction journal skill entry is inconsistent")
        entries.append(raw_entry)

    phase = str(journal["phase"])
    if phase == "building":
        if (
            journal["incoming_aggregate"] is not None
            or any(entry["incoming_digest"] is not None for entry in entries)
            or any(entry["progress"] != "pending" for entry in entries)
        ):
            raise InstallationError("building transaction journal is inconsistent")
    elif not _is_digest(journal["incoming_aggregate"]) or any(
        not _is_digest(entry["incoming_digest"]) for entry in entries
    ):
        raise InstallationError("transaction incoming generation is incomplete")
    _validate_progress_vector(entries, phase)
    cleanup = journal["cleanup"]
    if not isinstance(cleanup, dict) or any(
        not isinstance(value, str) for value in cleanup.values()
    ):
        raise InstallationError("transaction cleanup state is not an object")
    _validate_cleanup_vector(cleanup, phase, container_prefix)
    if (
        not _is_digest(journal["old_aggregate"])
        or journal["old_aggregate"] != _aggregate_identity(entries, "old_digest")
        or (
            phase != "building"
            and journal["incoming_aggregate"]
            != _aggregate_identity(entries, "incoming_digest")
        )
    ):
        raise InstallationError("transaction aggregate identity mismatch")
    return journal


def _status_scan_container(
    root_descriptor: int,
    name: str,
    *,
    expected_device: int,
    required: bool,
    budget: _StatusScanBudget,
) -> tuple[dict[str, str], str]:
    try:
        metadata = os.stat(
            name,
            dir_fd=root_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        if required:
            raise InstallationError(f"missing transaction container: {name}")
        return {}, "absent"
    if not stat.S_ISDIR(metadata.st_mode):
        raise InstallationError(f"transaction container is unsafe: {name}")
    descriptor, anchored = _status_open_directory_at(
        root_descriptor,
        name,
        expected_device=expected_device,
    )
    identities: dict[str, str] = {}
    observation = sha256()
    observation.update(repr((name, _status_metadata_tuple(anchored))).encode())
    try:
        budget.account((name,), anchored)
        names = _status_bounded_names(descriptor, budget=budget)
        for skill_name in names:
            if skill_name not in SKILL_NAMES:
                raise InstallationError(
                    f"unknown transaction artifact: {name}/{skill_name}"
                )
            skill_descriptor, skill_metadata = _status_open_directory_at(
                descriptor,
                skill_name,
                expected_device=expected_device,
            )
            try:
                semantic, fingerprint = _status_scan_open_directory(
                    skill_descriptor,
                    expected_device=expected_device,
                    budget=budget,
                )
            finally:
                os.close(skill_descriptor)
            identities[skill_name] = semantic
            observation.update(
                repr(
                    (
                        skill_name,
                        _status_metadata_tuple(skill_metadata),
                        fingerprint,
                    )
                ).encode()
            )
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if _status_metadata_tuple(anchored) != _status_metadata_tuple(after):
        raise _ObservationChanged(f"transaction container changed: {name}")
    return identities, observation.hexdigest()


def _status_scan_live_skills(
    target_descriptor: int,
    *,
    target_device: int,
    budget: _StatusScanBudget,
) -> tuple[dict[str, str | None], str]:
    identities: dict[str, str | None] = {}
    observation = sha256()
    for skill_name in SKILL_NAMES:
        try:
            metadata = os.stat(
                skill_name,
                dir_fd=target_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            identities[skill_name] = None
            observation.update(f"{skill_name}:missing".encode())
            continue
        if not stat.S_ISDIR(metadata.st_mode):
            raise InstallationError(f"managed skill is unsafe: {skill_name}")
        descriptor, anchored = _status_open_directory_at(
            target_descriptor,
            skill_name,
            expected_device=target_device,
        )
        try:
            semantic, fingerprint = _status_scan_open_directory(
                descriptor,
                expected_device=target_device,
                budget=budget,
            )
        finally:
            os.close(descriptor)
        identities[skill_name] = semantic
        observation.update(
            repr(
                (
                    skill_name,
                    _status_metadata_tuple(anchored),
                    fingerprint,
                )
            ).encode()
        )
    return identities, observation.hexdigest()


def _status_scan_evidence(
    target_descriptor: int,
    root_name: str,
    *,
    kind: str,
    target_path: str,
    target_metadata: os.stat_result,
    budget: _StatusScanBudget,
) -> tuple[
    dict[str, object] | None,
    str,
    dict[str, dict[str, str]],
    dict[str, bool],
    str,
]:
    prefix = INSTALL_TRANSACTION_PREFIX if kind == "transaction" else INSTALL_GC_PREFIX
    transaction_id = root_name.removeprefix(prefix)
    if (
        not root_name.startswith(prefix)
        or len(transaction_id) != 32
        or any(character not in "0123456789abcdef" for character in transaction_id)
    ):
        raise InstallationError(f"installer evidence name is unsafe: {root_name}")
    root_descriptor, root_metadata = _status_open_directory_at(
        target_descriptor,
        root_name,
        expected_device=target_metadata.st_dev,
    )
    observation = sha256()
    observation.update(repr((root_name, _status_metadata_tuple(root_metadata))).encode())
    allowed = {
        INSTALL_TRANSACTION_JOURNAL_NAME,
        _JOURNAL_TEMP_NAME,
        _STAGING_NAME,
        _BACKUP_NAME,
        _QUARANTINE_NAME,
    }
    try:
        budget.account((), root_metadata)
        if (
            root_metadata.st_uid != os.getuid()
            or stat.S_IMODE(root_metadata.st_mode) & 0o022
        ):
            raise InstallationError("installer evidence ownership or mode is unsafe")
        names = _status_bounded_names(root_descriptor, budget=budget)
        unexpected = sorted(set(names) - allowed)
        if unexpected:
            raise InstallationError(
                f"unknown installer evidence entry count: {len(unexpected)}"
            )
        if INSTALL_TRANSACTION_JOURNAL_NAME not in names:
            if kind == "transaction":
                if any(name != _JOURNAL_TEMP_NAME for name in names):
                    raise InstallationError("pre-journal transaction layout is unsafe")
                if _JOURNAL_TEMP_NAME in names:
                    temporary_before = os.stat(
                        _JOURNAL_TEMP_NAME,
                        dir_fd=root_descriptor,
                        follow_symlinks=False,
                    )
                    if (
                        not stat.S_ISREG(temporary_before.st_mode)
                        or temporary_before.st_uid != os.getuid()
                        or stat.S_IMODE(temporary_before.st_mode) & 0o022
                        or temporary_before.st_nlink != 1
                    ):
                        raise InstallationError(
                            "unpublished journal temporary file is unsafe"
                        )
                    _, digest, metadata = _status_read_regular_at(
                        root_descriptor,
                        _JOURNAL_TEMP_NAME,
                        expected_device=target_metadata.st_dev,
                        capture_limit=_STATUS_JOURNAL_MAX_BYTES,
                    )
                    if metadata != _status_metadata_tuple(temporary_before):
                        raise _ObservationChanged(
                            "unpublished journal temporary file changed"
                        )
                    observation.update(
                        repr((_JOURNAL_TEMP_NAME, metadata, digest)).encode()
                    )
                phase = "pre_journal"
            elif names:
                raise InstallationError("journal-free GC evidence is not empty")
            else:
                phase = "empty"
            root_after = os.fstat(root_descriptor)
            if _status_metadata_tuple(root_metadata) != _status_metadata_tuple(root_after):
                raise _ObservationChanged("installer evidence changed during observation")
            return None, phase, {}, {}, observation.hexdigest()

        raw, journal_digest, journal_metadata = _status_read_regular_at(
            root_descriptor,
            INSTALL_TRANSACTION_JOURNAL_NAME,
            expected_device=target_metadata.st_dev,
            capture_limit=_STATUS_JOURNAL_MAX_BYTES,
        )
        assert raw is not None
        observation.update(
            repr(
                (
                    INSTALL_TRANSACTION_JOURNAL_NAME,
                    journal_metadata,
                    journal_digest,
                )
            ).encode()
        )
        journal = _status_parse_journal(
            raw,
            root_name=root_name,
            container_prefix=prefix,
            target_path=target_path,
            target_metadata=target_metadata,
        )
        if _JOURNAL_TEMP_NAME in names:
            _, temporary_digest, temporary_metadata = _status_read_regular_at(
                root_descriptor,
                _JOURNAL_TEMP_NAME,
                expected_device=target_metadata.st_dev,
                capture_limit=_STATUS_JOURNAL_MAX_BYTES,
            )
            observation.update(
                repr(
                    (
                        _JOURNAL_TEMP_NAME,
                        temporary_metadata,
                        temporary_digest,
                    )
                ).encode()
            )
        phase = str(journal["phase"])
        if kind == "gc" and phase not in {"committed", "rolled_back"}:
            raise InstallationError("installer garbage is not terminal")
        required = phase in {"prepared", "rolling_back"}
        containers: dict[str, dict[str, str]] = {}
        container_presence: dict[str, bool] = {}
        for container_name in _CLEANUP_CONTAINERS:
            identities, fingerprint = _status_scan_container(
                root_descriptor,
                container_name,
                expected_device=target_metadata.st_dev,
                required=required,
                budget=budget,
            )
            containers[container_name] = identities
            container_presence[container_name] = fingerprint != "absent"
            observation.update(repr((container_name, fingerprint)).encode())
        root_after = os.fstat(root_descriptor)
        if _status_metadata_tuple(root_metadata) != _status_metadata_tuple(root_after):
            raise _ObservationChanged("installer evidence changed during observation")
        return (
            journal,
            phase,
            containers,
            container_presence,
            observation.hexdigest(),
        )
    finally:
        os.close(root_descriptor)


def _status_validate_uncommitted_snapshot(
    entries: list[dict[str, object]],
    live: dict[str, str | None],
    staged: dict[str, str],
    backups: dict[str, str],
    quarantined: dict[str, str],
    *,
    rolling_back: bool,
) -> None:
    for entry in entries:
        name = str(entry["name"])
        physical = (
            live[name],
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
            raise InstallationError(f"ambiguous transaction state for {name}")


def _status_validate_terminal_snapshot(
    journal: dict[str, object],
    live: dict[str, str | None],
    containers: dict[str, dict[str, str]],
    presence: dict[str, bool],
) -> None:
    entries = journal["skills"]
    cleanup = journal["cleanup"]
    assert isinstance(entries, list)
    assert isinstance(cleanup, dict)
    for container_name in _CLEANUP_CONTAINERS:
        state = str(cleanup[container_name])
        exists = presence[container_name]
        identities = containers[container_name]
        if state == "pending" and not exists:
            raise InstallationError(f"pending cleanup container is missing: {container_name}")
        if state == "deleted" and (exists or identities):
            raise InstallationError(f"deleted cleanup container reappeared: {container_name}")

    phase = str(journal["phase"])
    if phase == "committed":
        for entry in entries:
            if live[str(entry["name"])] != entry["incoming_digest"]:
                raise InstallationError(
                    f"incoming generation verification failed for {entry['name']}"
                )
        if cleanup[_STAGING_NAME] == "pending" and containers[_STAGING_NAME]:
            raise InstallationError("committed transaction still has staged artifacts")
        if cleanup[_QUARANTINE_NAME] == "pending" and containers[_QUARANTINE_NAME]:
            raise InstallationError("committed transaction still has quarantine artifacts")
        if cleanup[_BACKUP_NAME] == "pending":
            expected_backups = {
                str(entry["name"]): str(entry["old_digest"])
                for entry in entries
                if bool(entry["old_present"])
            }
            if containers[_BACKUP_NAME] != expected_backups:
                raise InstallationError("committed backup set mismatch")
        return
    if phase != "rolled_back":
        raise InstallationError("transaction is not terminal")
    for entry in entries:
        if live[str(entry["name"])] != entry["old_digest"]:
            raise InstallationError(
                f"old generation verification failed for {entry['name']}"
            )
    if cleanup[_BACKUP_NAME] == "pending" and containers[_BACKUP_NAME]:
        raise InstallationError("rolled-back transaction still has backups")
    pending_incoming: dict[str, str] = {}
    for entry in entries:
        name = str(entry["name"])
        incoming = entry["incoming_digest"]
        if (
            cleanup[_STAGING_NAME] == "pending"
            and name in containers[_STAGING_NAME]
            and containers[_STAGING_NAME][name] != incoming
        ):
            raise InstallationError("rolled-back staging mismatch")
        if (
            cleanup[_QUARANTINE_NAME] == "pending"
            and name in containers[_QUARANTINE_NAME]
            and containers[_QUARANTINE_NAME][name] != incoming
        ):
            raise InstallationError("rolled-back quarantine mismatch")
        if (
            cleanup[_STAGING_NAME] == "pending"
            and cleanup[_QUARANTINE_NAME] == "pending"
            and name in containers[_STAGING_NAME]
            and name in containers[_QUARANTINE_NAME]
        ):
            raise InstallationError("duplicated rolled-back incoming payload")
        if cleanup[_STAGING_NAME] == "pending" and name in containers[_STAGING_NAME]:
            pending_incoming[name] = containers[_STAGING_NAME][name]
        if (
            cleanup[_QUARANTINE_NAME] == "pending"
            and name in containers[_QUARANTINE_NAME]
        ):
            pending_incoming[name] = containers[_QUARANTINE_NAME][name]
    if (
        cleanup[_STAGING_NAME] == "pending"
        and cleanup[_QUARANTINE_NAME] == "pending"
        and set(pending_incoming) != set(SKILL_NAMES)
    ):
        raise InstallationError("rolled-back incoming artifact set is incomplete")


def _status_observe_evidence_once(
    target_descriptor: int,
    root_name: str,
    *,
    kind: str,
    target_path: str,
    target_metadata: os.stat_result,
) -> tuple[dict[str, object], str]:
    budget = _StatusScanBudget()
    journal, phase, containers, presence, evidence_fingerprint = _status_scan_evidence(
        target_descriptor,
        root_name,
        kind=kind,
        target_path=target_path,
        target_metadata=target_metadata,
        budget=budget,
    )
    live, live_fingerprint = _status_scan_live_skills(
        target_descriptor,
        target_device=target_metadata.st_dev,
        budget=budget,
    )
    combined = sha256()
    combined.update(evidence_fingerprint.encode())
    combined.update(live_fingerprint.encode())
    fingerprint = combined.hexdigest()
    if journal is None:
        return (
            {
                "kind": kind,
                "phase": phase,
                "evidence_paths": [
                    _status_public_text(str(Path(target_path) / root_name))
                ],
            },
            fingerprint,
        )

    entries = journal["skills"]
    assert isinstance(entries, list)
    try:
        if phase == "building":
            if containers[_BACKUP_NAME] or containers[_QUARANTINE_NAME]:
                raise InstallationError("building transaction is not safe to discard")
            for entry in entries:
                if live[str(entry["name"])] != entry["old_digest"]:
                    raise InstallationError(
                        f"old generation verification failed for {entry['name']}"
                    )
        elif phase in {"prepared", "rolling_back"}:
            _status_validate_uncommitted_snapshot(
                entries,
                live,
                containers[_STAGING_NAME],
                containers[_BACKUP_NAME],
                containers[_QUARANTINE_NAME],
                rolling_back=phase == "rolling_back",
            )
        else:
            _status_validate_terminal_snapshot(journal, live, containers, presence)
    except InstallationError as exc:
        raise _InvalidEvidence(fingerprint) from exc
    return (
        {
            "kind": kind,
            "phase": phase,
            "evidence_paths": [
                _status_public_text(str(Path(target_path) / root_name))
            ],
        },
        fingerprint,
    )


def _status_raw_observation_fingerprint(
    target_descriptor: int,
    root_name: str,
    *,
    target_metadata: os.stat_result,
) -> str:
    """Fingerprint evidence and live payload without interpreting the journal."""

    budget = _StatusScanBudget()
    try:
        root_descriptor, root_metadata = _status_open_directory_at(
            target_descriptor,
            root_name,
            expected_device=target_metadata.st_dev,
        )
        budget.observe((root_name,), root_metadata, role="evidence-root")
        try:
            _, evidence_fingerprint = _status_scan_open_directory(
                root_descriptor,
                expected_device=target_metadata.st_dev,
                budget=budget,
            )
        finally:
            os.close(root_descriptor)
        _, live_fingerprint = _status_scan_live_skills(
            target_descriptor,
            target_device=target_metadata.st_dev,
            budget=budget,
        )
    except (InstallationError, OSError) as exc:
        raise _InvalidEvidence(budget.failure_fingerprint(exc)) from exc
    combined = sha256()
    combined.update(evidence_fingerprint.encode())
    combined.update(live_fingerprint.encode())
    return combined.hexdigest()


def _status_observe_evidence(
    target_descriptor: int,
    root_name: str,
    *,
    kind: str,
    target_path: str,
    target_metadata: os.stat_result,
) -> tuple[dict[str, object], str]:
    boundary_token = None
    if _STATUS_MOUNT_BOUNDARY.get() is None:
        boundary_token = _STATUS_MOUNT_BOUNDARY.set(
            _status_capture_mount_boundary(target_descriptor)
        )
    try:
        try:
            report, fingerprint = _status_observe_evidence_once(
                target_descriptor,
                root_name,
                kind=kind,
                target_path=target_path,
                target_metadata=target_metadata,
            )
        except _InvalidEvidence as exc:
            raise _InvalidEvidence(
                _status_bind_mount_fingerprint(exc.fingerprint)
            ) from exc
        except InstallationError as exc:
            try:
                raw_fingerprint = _status_raw_observation_fingerprint(
                    target_descriptor,
                    root_name,
                    target_metadata=target_metadata,
                )
            except _InvalidEvidence as raw_invalid:
                raise _InvalidEvidence(
                    _status_bind_mount_fingerprint(raw_invalid.fingerprint)
                ) from raw_invalid
            raise _InvalidEvidence(
                _status_bind_mount_fingerprint(raw_fingerprint)
            ) from exc
        return report, _status_bind_mount_fingerprint(fingerprint)
    finally:
        if boundary_token is not None:
            _STATUS_MOUNT_BOUNDARY.reset(boundary_token)


def _status_report(
    status_name: str,
    target: Path,
    *,
    target_exists: bool,
    managed_skills: dict[str, object] | None = None,
    transaction: dict[str, object] | None = None,
    reason_code: str | None = None,
) -> dict[str, object]:
    if managed_skills is None:
        managed_skills = {
            "expected": len(SKILL_NAMES),
            "present": None,
            "missing": None,
        }
    messages = {
        "clean": (
            "Служебных данных незавершённой установки нет; все 15 каталогов "
            "навыков КС РФ находятся на месте. Содержимое и версия здесь не проверяются."
        ),
        "not_installed": "Набор навыков КС РФ в указанной папке не установлен.",
        "incomplete": "Установка неполная: отсутствует часть каталогов навыков КС РФ.",
        "recovery_required": (
            "Обнаружено незавершённое или меняющееся состояние установки. "
            "Автоматическое восстановление не запускалось."
        ),
        "unsafe": (
            "Состояние установки неоднозначно или небезопасно; положительный "
            "результат не выдан."
        ),
    }
    actions = {
        "clean": (
            "Проверьте содержимое runtime-валидатором; актуальность версии "
            "подтверждается обычной установкой из чистого опубликованного main."
        ),
        "not_installed": "Запустите обычную установку из опубликованного набора.",
        "incomplete": "Запустите обычную установку, чтобы восстановить полный набор.",
        "recovery_required": (
            "Если установка ещё выполняется, дождитесь её завершения и повторите проверку; "
            "иначе запустите обычную установку для проверенного восстановления."
        ),
        "unsafe": (
            "Не удаляйте служебные данные вручную; сохраните найденные доказательства "
            "и проверьте путь или журнал перед новой установкой."
        ),
    }
    reason_code = reason_code or status_name
    reason_messages = {
        "target_appeared": "Папка появилась во время наблюдения; результат нужно повторить.",
        "target_replaced": "Целевая папка была заменена во время наблюдения.",
        "observation_changed": "Состояние изменилось во время наблюдения.",
        "unsafe_target": "Целевой путь небезопасен или недоступен для проверки.",
        "unsafe_evidence": "Служебные данные установки не прошли безопасную проверку.",
    }
    message = messages[status_name]
    if reason_code in reason_messages:
        message = f"{message} {reason_messages[reason_code]}"
    return {
        "schema_version": _STATUS_SCHEMA_VERSION,
        "status": status_name,
        "severity": _STATUS_SEVERITIES[status_name],
        "exit_code": _STATUS_EXIT_CODES[status_name],
        "reason_code": reason_code,
        "target": _status_public_text(str(target)),
        "target_exists": target_exists,
        "managed_skills": managed_skills,
        "transaction": transaction,
        "message": message,
        "recommended_action": actions[status_name],
        "observation": {
            "consistency": "unlocked_read_only",
            "explicit_mutations_performed": False,
            "filesystem_access_time_updates_possible": True,
            "atomic_snapshot": False,
        },
    }


def _status_target_matches(
    target: Path,
    target_descriptor: int,
    opened_metadata: os.stat_result,
) -> bool:
    try:
        lexical = target.lstat()
        anchored = os.fstat(target_descriptor)
    except OSError:
        return False
    return _status_same_object(opened_metadata, anchored) and _status_same_object(
        opened_metadata,
        lexical,
    )


def inspect_installation_status(target: Path) -> dict[str, object]:
    """Inspect one target without issuing a write, lock, or recovery operation."""

    target = _absolute_without_resolving(target)
    root = Path(target.anchor)
    try:
        if target == root or target.resolve(strict=False) == Path.home().resolve():
            raise InstallationError(f"refusing broad install target: {target}")
        try:
            initial_metadata = target.lstat()
        except FileNotFoundError:
            try:
                target.lstat()
            except FileNotFoundError:
                return _status_report(
                    "not_installed",
                    target,
                    target_exists=False,
                    managed_skills={
                        "expected": len(SKILL_NAMES),
                        "present": 0,
                        "missing": list(SKILL_NAMES),
                    },
                )
            return _status_report(
                "recovery_required",
                target,
                target_exists=True,
                reason_code="target_appeared",
            )
        if stat.S_ISLNK(initial_metadata.st_mode) or not stat.S_ISDIR(
            initial_metadata.st_mode
        ):
            raise InstallationError("целевая папка является ссылкой или не каталогом")

        target_path = str(target.resolve(strict=True))
        target_descriptor = os.open(target, _status_directory_flags())
        first_top: dict[str, tuple[int, ...]] | None = None
        managed: dict[str, object] | None = None
        evidence_name: str | None = None
        evidence_kind: str | None = None
        mount_tokens: list[object] = []
        first_mount_fingerprint: str | None = None
        second_mount_fingerprint: str | None = None

        def activate_mount_sample() -> str:
            boundary = _status_capture_mount_boundary(target_descriptor)
            mount_tokens.append(_STATUS_MOUNT_BOUNDARY.set(boundary))
            return _status_mount_boundary_fingerprint()

        try:
            anchored_metadata = os.fstat(target_descriptor)
            if not _status_same_object(initial_metadata, anchored_metadata):
                raise _ObservationChanged("целевая папка изменилась при открытии")
            first_mount_fingerprint = activate_mount_sample()
            try:
                first_top, managed = _status_top_level_snapshot(
                    target_descriptor,
                    target_device=anchored_metadata.st_dev,
                )
                transaction_roots = sorted(
                    name
                    for name in first_top
                    if name.startswith(INSTALL_TRANSACTION_PREFIX)
                )
                garbage_roots = sorted(
                    name for name in first_top if name.startswith(INSTALL_GC_PREFIX)
                )
                if (
                    len(transaction_roots) > 1
                    or len(garbage_roots) > 1
                    or (transaction_roots and garbage_roots)
                ):
                    raise InstallationError(
                        "обнаружено несколько или конфликтующие служебные каталоги"
                    )

                transaction: dict[str, object] | None = None
                evidence_fingerprint: str | None = None
                if transaction_roots or garbage_roots:
                    evidence_kind = "transaction" if transaction_roots else "gc"
                    evidence_name = (transaction_roots or garbage_roots)[0]
                    transaction, evidence_fingerprint = _status_observe_evidence(
                        target_descriptor,
                        evidence_name,
                        kind=evidence_kind,
                        target_path=target_path,
                        target_metadata=anchored_metadata,
                    )
                    transaction["evidence_paths"] = [
                        _status_public_text(str(target / evidence_name))
                    ]
                    second_mount_fingerprint = activate_mount_sample()
                    try:
                        _, repeated_fingerprint = _status_observe_evidence(
                            target_descriptor,
                            evidence_name,
                            kind=evidence_kind,
                            target_path=target_path,
                            target_metadata=anchored_metadata,
                        )
                    except (InstallationError, OSError) as exc:
                        raise _ObservationChanged(
                            "служебные данные изменились во время повторной выборки"
                        ) from exc
                    if evidence_fingerprint != repeated_fingerprint:
                        raise _ObservationChanged(
                            "служебные данные изменились во время наблюдения"
                        )

                if second_mount_fingerprint is None:
                    second_mount_fingerprint = activate_mount_sample()
                second_top, repeated_managed = _status_top_level_snapshot(
                    target_descriptor,
                    target_device=anchored_metadata.st_dev,
                )
                if not _status_target_matches(
                    target,
                    target_descriptor,
                    anchored_metadata,
                ):
                    return _status_report(
                        "unsafe",
                        target,
                        target_exists=True,
                        managed_skills=managed,
                        transaction=transaction,
                        reason_code="target_replaced",
                    )
                if (
                    first_mount_fingerprint != second_mount_fingerprint
                    or first_top != second_top
                    or managed != repeated_managed
                ):
                    return _status_report(
                        "recovery_required",
                        target,
                        target_exists=True,
                        managed_skills=repeated_managed,
                        transaction=transaction,
                        reason_code="observation_changed",
                    )
                if transaction is not None:
                    return _status_report(
                        "recovery_required",
                        target,
                        target_exists=True,
                        managed_skills=managed,
                        transaction=transaction,
                    )
                present = int(managed["present"])
                if present == 0:
                    status_name = "not_installed"
                elif present < len(SKILL_NAMES):
                    status_name = "incomplete"
                else:
                    status_name = "clean"
                return _status_report(
                    status_name,
                    target,
                    target_exists=True,
                    managed_skills=managed,
                )
            except (_ObservationChanged, InstallationError, OSError) as exc:
                if second_mount_fingerprint is None:
                    second_mount_fingerprint = activate_mount_sample()
                if not _status_target_matches(
                    target,
                    target_descriptor,
                    anchored_metadata,
                ):
                    return _status_report(
                        "unsafe",
                        target,
                        target_exists=True,
                        managed_skills=managed,
                        reason_code="target_replaced",
                    )
                if first_mount_fingerprint != second_mount_fingerprint:
                    return _status_report(
                        "recovery_required",
                        target,
                        target_exists=True,
                        managed_skills=managed,
                        reason_code="observation_changed",
                    )
                if isinstance(exc, _ObservationChanged):
                    return _status_report(
                        "recovery_required",
                        target,
                        target_exists=True,
                        managed_skills=managed,
                        reason_code="observation_changed",
                    )
                if (
                    isinstance(exc, _InvalidEvidence)
                    and evidence_name is not None
                    and evidence_kind is not None
                ):
                    repeated_is_same_invalid = False
                    try:
                        _status_observe_evidence(
                            target_descriptor,
                            evidence_name,
                            kind=evidence_kind,
                            target_path=target_path,
                            target_metadata=anchored_metadata,
                        )
                    except _InvalidEvidence as repeated:
                        repeated_is_same_invalid = (
                            repeated.fingerprint == exc.fingerprint
                        )
                    except (_ObservationChanged, InstallationError, OSError):
                        repeated_is_same_invalid = False
                    if not _status_target_matches(
                        target,
                        target_descriptor,
                        anchored_metadata,
                    ):
                        return _status_report(
                            "unsafe",
                            target,
                            target_exists=True,
                            managed_skills=managed,
                            reason_code="target_replaced",
                        )
                    if not repeated_is_same_invalid:
                        return _status_report(
                            "recovery_required",
                            target,
                            target_exists=True,
                            managed_skills=managed,
                            reason_code="observation_changed",
                        )
                if first_top is not None:
                    try:
                        last_top, _ = _status_top_level_snapshot(
                            target_descriptor,
                            target_device=anchored_metadata.st_dev,
                        )
                    except (InstallationError, OSError, _ObservationChanged):
                        last_top = None
                    if last_top is not None and last_top != first_top:
                        return _status_report(
                            "recovery_required",
                            target,
                            target_exists=True,
                            managed_skills=managed,
                            reason_code="observation_changed",
                        )
                return _status_report(
                    "unsafe",
                    target,
                    target_exists=True,
                    managed_skills=managed,
                    reason_code="unsafe_evidence",
                )
        finally:
            for token in reversed(mount_tokens):
                _STATUS_MOUNT_BOUNDARY.reset(token)
            os.close(target_descriptor)
    except (InstallationError, OSError) as exc:
        try:
            target.lstat()
            target_exists = True
        except OSError:
            target_exists = False
        return _status_report(
            "unsafe",
            target,
            target_exists=target_exists,
            reason_code="unsafe_target",
        )


def render_installation_status(report: dict[str, object]) -> str:
    labels = {
        "clean": "чисто",
        "not_installed": "не установлено",
        "incomplete": "установка неполная",
        "recovery_required": "требуется повторная проверка или восстановление",
        "unsafe": "небезопасное или повреждённое состояние",
    }
    phase_labels = {
        "pre_journal": "до записи основного журнала",
        "building": "подготовка новой версии",
        "prepared": "подготовлено к замене",
        "rolling_back": "восстановление прежней версии",
        "rolled_back": "прежняя версия восстановлена",
        "committed": "новая версия подтверждена",
        "empty": "завершение служебной очистки",
    }
    managed = report["managed_skills"]
    assert isinstance(managed, dict)
    present = managed["present"]
    expected = managed["expected"]
    skills_line = (
        "Навыки КС РФ: число не подтверждено"
        if present is None
        else f"Навыки КС РФ: {present} из {expected}"
    )
    transaction = report["transaction"]
    lines = [
        f"Состояние: {labels[str(report['status'])]}",
        f"Папка: {report['target']}",
        skills_line,
        str(report["message"]),
    ]
    if isinstance(transaction, dict):
        paths = transaction.get("evidence_paths", [])
        lines.append(f"Служебные данные: {', '.join(str(path) for path in paths)}")
        phase = str(transaction.get("phase", "unknown"))
        lines.append(f"Этап: {phase_labels.get(phase, 'неизвестный этап')}")
    lines.extend(
        [
            f"Что делать: {report['recommended_action']}",
            (
                "Граница проверки: команда не выполняла операций записи или блокировки, "
                "но файловая система могла обновить время последнего доступа; это не "
                "атомарный снимок, состояние могло измениться сразу после проверки."
            ),
        ]
    )
    return "\n".join(lines)


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


class _RussianArgumentParser(argparse.ArgumentParser):
    """Keep the user-facing CLI help and common parse errors in Russian."""

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "Использование:", 1)

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "Использование:", 1)
            .replace("options:", "параметры:", 1)
            .replace(
                "show this help message and exit",
                "показать эту справку и выйти",
            )
        )

    def error(self, message: str) -> None:
        translations = {
            "the following arguments are required: ":
                "не указаны обязательные параметры: ",
            "unrecognized arguments: ": "неизвестные параметры: ",
        }
        localized = message
        for source, replacement in translations.items():
            if localized.startswith(source):
                localized = replacement + localized.removeprefix(source)
                break
        if localized.startswith("argument ") and ": expected one argument" in localized:
            option = localized.removeprefix("argument ").split(":", 1)[0]
            localized = f"параметр {option} требует значение"
        if localized.startswith("argument ") and ": not allowed with argument " in localized:
            option, conflicting = localized.removeprefix("argument ").split(
                ": not allowed with argument ",
                1,
            )
            localized = (
                f"параметр {option} нельзя использовать вместе с {conflicting}"
            )
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: ошибка: {localized}\n")


def _parser() -> argparse.ArgumentParser:
    parser = _RussianArgumentParser(
        allow_abbrev=False,
        description=(
            "Установить точный состав навыков КС РФ или без записи проверить "
            "состояние установленного набора."
        )
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--repo",
        type=Path,
        metavar="ПУТЬ",
        help="исходный корень опубликованного репозитория",
    )
    source.add_argument(
        "--source-skills-root",
        type=Path,
        metavar="ПУТЬ",
        help="исходная папка с 15 навыками КС РФ",
    )
    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        metavar="ПУТЬ",
        help="папка установки или проверки",
    )
    parser.add_argument(
        "--preserve-target-development",
        action="store_true",
        help="при синхронизации сохранить исходные QA-файлы целевой копии",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="без записи проверить установленный набор и служебные данные",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="в режиме --status вывести стабильный JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.status:
        if (
            args.repo is not None
            or args.source_skills_root is not None
            or args.preserve_target_development
        ):
            parser.error(
                "--status нельзя сочетать с источником или "
                "--preserve-target-development"
            )
        report = inspect_installation_status(args.target)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        else:
            print(render_installation_status(report))
        return int(report["exit_code"])
    if args.json:
        parser.error("--json можно использовать только вместе с --status")
    if args.repo is None and args.source_skills_root is None:
        parser.error(
            "для установки требуется --repo или --source-skills-root"
        )
    source_root = args.repo / "skills" if args.repo is not None else args.source_skills_root
    assert source_root is not None
    try:
        if args.preserve_target_development and args.source_skills_root is None:
            raise InstallationError(
                "--preserve-target-development требует --source-skills-root"
            )
        target = copy_skillset(
            source_root,
            args.target,
            preserve_target_development=args.preserve_target_development,
        )
    except (InstallationError, FileNotFoundError, OSError) as exc:
        print(f"Установка набора навыков отклонена: {exc}", file=sys.stderr)
        return 1
    if args.preserve_target_development:
        print(
            "Точный runtime-состав навыков КС РФ синхронизирован с сохранением "
            f"исходных QA-файлов в {target}"
        )
    else:
        print(f"Точный состав навыков КС РФ из манифеста установлен в {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
