"""Source-bound editorial proposals. No legal approval or release authority."""
from __future__ import annotations

from copy import deepcopy
import difflib
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

from .composer import stable_sentence_id
from .contracts import SCHEMA_VERSION
from .sentence_roles import CANONICAL_SENTENCE_ROLES
from .storage import ContentAddressedStore, canonical_json_bytes, sha256_bytes


CONCEPT_FIELDS = {
    "question": "Конституционный вопрос", "norm": "Оспариваемая норма",
    "norm_version": "Редакция нормы", "applied_meaning": "Применённый смысл",
    "harm": "Вред и причинная связь", "constitutional_defect": "Конституционный дефект",
    "requested_remedy": "Требуемое решение",
}
ARGUMENT_FIELDS = {
    "thesis": "Тезис", "applicability": "Почему источник применим",
    "conclusion": "Вывод", "strongest_objection": "Сильнейшее возражение", "response": "Ответ",
}
LEVELS = {"argument": 0, "mentioned": 1, "applied": 2, "causal": 3}
LEVEL_LABELS = {
    "argument": "правовой довод", "mentioned": "норма упомянута",
    "applied": "норма применена", "causal": "применение обусловило результат",
}
SOURCE_ROLES = {"court_reasoning", "party_submission", "legal_text", "doctrine", "other"}
PROOF_ROLES = {"norm_mention", "norm_use", "outcome_link", "alternative_ground_analysis", "holding", "norm_text", "background"}
NOTICE = "ПРЕДЛАГАЕМАЯ РЕДАКЦИЯ. Требует юридической проверки и принятия человеком."
BOUNDARIES = {"candidate_only": True, "human_review": "pending", "filing_authority": False,
              "approval_authority": False, "release_eligible": False, "source_authenticity_verified": False,
              "legal_support_verified": False, "independent_legal_review": False}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Нужно непустое поле {label}.")
    return value


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} должен быть объектом.")
    return deepcopy(dict(value))


def _items(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{label} должен быть списком.")
    return [_mapping(item, label) for item in value]


def _digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _wording(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def _sentences(complaint: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    codes = set()
    for section in _items(complaint.get("sections"), "complaint.sections"):
        code = _text(section.get("code"), "section.code")
        if code in codes:
            raise ValueError("Повторяющийся раздел.")
        codes.add(code)
        _text(section.get("heading"), "section.heading")
        for ordinal, sentence in enumerate(_items(section.get("sentences"), "section.sentences"), 1):
            text = _text(sentence.get("text"), "sentence.text")
            sid = sentence.get("sentence_id") or stable_sentence_id(complaint["matter_id"], code, ordinal, text)
            if not isinstance(sid, str) or not re.fullmatch(r"sent-[0-9a-f]{16}", sid) or sid in result:
                raise ValueError("Некорректный или повторяющийся sentence_id.")
            role = sentence.get("role", "narrative")
            if role not in CANONICAL_SENTENCE_ROLES:
                raise ValueError(f"Неизвестная роль предложения: {sid}.")
            sentence.update(sentence_id=sid, role=role)
            result[sid] = sentence
    if not result:
        raise ValueError("В проекте нет предложений.")
    return result


def _normalize_complaint(value: Any, matter_id: str) -> dict[str, Any]:
    complaint = _mapping(value, "complaint")
    if complaint.get("matter_id") != matter_id:
        raise ValueError("Дело проекта не совпадает с рабочей папкой.")
    _text(complaint.get("draft_id"), "complaint.draft_id")
    indexed = _sentences(complaint)
    # Preserve section order and metadata while giving every line a stable ID.
    for section in complaint["sections"]:
        for ordinal, sentence in enumerate(section["sentences"], 1):
            sid = sentence.get("sentence_id") or stable_sentence_id(matter_id, section["code"], ordinal, sentence["text"])
            sentence.update(indexed[sid])
    return complaint


def _proposal(complaint: Mapping[str, Any]) -> dict[str, Any]:
    candidate = deepcopy(dict(complaint))
    candidate["approvals"] = {}
    candidate["formal_check"] = {}
    for section in candidate["sections"]:
        for sentence in section["sentences"]:
            sentence["support_status"] = "pending"
    return candidate


def _draft_text(complaint: Mapping[str, Any] | None) -> str:
    if complaint is None:
        return ""
    lines = [NOTICE, "", str(complaint.get("title") or "Рабочий проект"), ""]
    for section in complaint["sections"]:
        lines.extend(["## " + section["heading"], ""])
        for sentence in section["sentences"]:
            lines.extend([sentence["text"], ""])
    return "\n".join(lines)


class WritingWorkflow:
    def __init__(self, workspace: Path, matter_id: str):
        self.workspace = Path(workspace).resolve()
        self.matter_id = matter_id
        for path in (self.workspace / "writing", self.workspace / "drafts" / "writing"):
            if not path.resolve().is_relative_to(self.workspace):
                raise ValueError("Каталог редакций выходит за пределы дела.")
        self.store = ContentAddressedStore(self.workspace, "writing")
        self.exports = self.workspace / "drafts" / "writing"

    def _read_object(self, record: Mapping[str, Any]) -> bytes:
        data = self.store.read_bytes(record)
        if type(record.get("size")) is not int or record["size"] != len(data):
            raise ValueError("Размер сохранённого объекта не совпадает.")
        return data

    def read(self, reference: Mapping[str, Any]) -> dict[str, Any]:
        packet = _mapping(json.loads(self._read_object(reference)), "packet")
        if packet.get("artifact_type") != "WritingPacket" or packet.get("matter_id") != self.matter_id:
            raise ValueError("Пакет относится к другому делу или имеет неверный тип.")
        if any(type(packet.get(key)) is not type(value) or packet.get(key) != value for key, value in BOUNDARIES.items()):
            raise ValueError("Нарушены границы предлагаемой редакции.")
        for record in packet.get("artifacts", []):
            path = (self.workspace / record["path"]).resolve()
            if not path.is_relative_to(self.exports.resolve()):
                raise ValueError("Артефакт находится вне каталога редакций.")
            data = path.read_bytes()
            if _wording(data.decode("utf-8")) != record["sha256"] or len(data) != record["size"]:
                raise ValueError("Файл предлагаемой редакции изменился.")
        for source in packet.get("sources", []):
            self._read_object(source["object"])
        if packet.get("candidate") is not None and _digest(packet["candidate"]) != packet.get("draft_sha256"):
            raise ValueError("Отпечаток проекта не совпадает.")
        return packet

    def _sources(self, old: list[dict[str, Any]], supplied: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
        combined = {item["source_id"]: deepcopy(item) for item in old}
        supplied_ids = set()
        for source in _items(supplied, "sources"):
            sid = _text(source.get("source_id"), "source_id")
            if sid in supplied_ids or (sid in combined and combined[sid] != source):
                raise ValueError("Нельзя заменить источник под прежним source_id.")
            supplied_ids.add(sid)
            if source.get("role") not in SOURCE_ROLES:
                raise ValueError("Нужно указать роль источника.")
            combined[sid] = source
        texts = {}
        for sid, source in combined.items():
            data = self._read_object(_mapping(source.get("object"), "source.object"))
            if len(data) > 20 * 1024 * 1024:
                raise ValueError("Текстовый источник превышает 20 MiB.")
            try:
                texts[sid] = data.decode("utf-8")
            except UnicodeError:
                raise ValueError("Нужен отдельный текстовый источник UTF-8 с сохранённой связью с оригиналом.") from None
        return list(combined.values()), texts

    def _argument(self, card: dict[str, Any], sources: list[dict[str, Any]], texts: dict[str, str]) -> dict[str, Any]:
        _text(card.get("argument_id"), "argument_id")
        _text(card.get("sentence_id"), "sentence_id")
        level = card.get("inference_level")
        if level not in LEVELS:
            raise ValueError("Нужно указать силу вывода: argument, mentioned, applied или causal.")
        gaps = []
        for key, label in ARGUMENT_FIELDS.items():
            value = card.get(key, "")
            if not isinstance(value, str):
                raise ValueError(f"{key} должен быть текстом.")
            card[key] = value
            if not value.strip():
                gaps.append("Заполнить: " + label)
        source_map = {item["source_id"]: item for item in sources}
        evidence = _items(card.get("evidence", []), "argument.evidence")
        court_functions = set()
        for item in evidence:
            sid = item.get("source_id")
            if sid not in texts:
                raise ValueError("Неизвестный источник цитаты.")
            start, end = item.get("start"), item.get("end")
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(texts[sid]):
                raise ValueError("Некорректные символьные границы цитаты.")
            quote = _text(item.get("quote"), "evidence.quote")
            if texts[sid][start:end] != quote:
                raise ValueError("Цитата не совпадает с указанным фрагментом источника.")
            if item.get("proof_role") not in PROOF_ROLES:
                raise ValueError("Неизвестная доказательственная функция фрагмента.")
            if source_map[sid]["role"] == "court_reasoning":
                court_functions.add(item["proof_role"])
            item["quote_match"] = True
        if not evidence:
            gaps.append("Добавить основания довода и точные фрагменты источников.")
        required = {
            "argument": set(), "mentioned": {"norm_mention"}, "applied": {"norm_use"},
            "causal": {"norm_use", "outcome_link", "alternative_ground_analysis"},
        }[level]
        for missing in sorted(required - court_functions):
            gaps.append("Не записан фрагмент судебной мотивировки для функции: " + missing)
        # Even a complete declared role map is not proof of semantic support.
        gaps.append("Юрист проверяет автора фрагмента, подлинность, применимость и достаточность оснований вывода.")
        if "proposed_text" not in card:
            quoted = " ".join("«" + item["quote"] + "»" for item in evidence)
            card["proposed_text"] = " ".join(part for part in (
                card["thesis"], quoted, card["applicability"],
                ("Возможное возражение: " + card["strongest_objection"]) if card["strongest_objection"] else "",
                card["response"], card["conclusion"],
            ) if part)
        _text(card.get("proposed_text"), "proposed_text")
        card.update(evidence=evidence, wording_sha256=_wording(card["proposed_text"]),
                    gaps=gaps, legal_support_verified=False)
        return card

    def run(self, action: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if payload.get("matter_id") != self.matter_id:
            raise ValueError("matter_id не совпадает с рабочей папкой.")
        if action == "plan":
            packet = self._plan(payload)
        else:
            parent_ref = _mapping(payload.get("parent"), "parent")
            parent = self.read(parent_ref)
            if action in {"review", "revise"}:
                if parent.get("candidate") is None or payload.get("base_draft_sha256") != parent.get("draft_sha256"):
                    raise ValueError("Устаревший или отсутствующий отпечаток исходного проекта.")
            if action == "compose":
                packet = self._compose(parent, payload)
            elif action == "review":
                packet = self._review(parent, payload)
            elif action == "revise":
                packet = self._revise(parent, payload)
            else:
                raise ValueError("Неизвестное действие редакторского цикла.")
            packet["parent"] = parent_ref
        packet.update(BOUNDARIES)
        packet.update(schema_version=SCHEMA_VERSION, artifact_type="WritingPacket", matter_id=self.matter_id, action=action)
        return self._save(packet)

    def _plan(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        options = _items(payload.get("options"), "options")
        if not 1 <= len(options) <= 5:
            raise ValueError("Нужно от одного до пяти вариантов вопроса.")
        ids, gaps = set(), []
        for option in options:
            oid = _text(option.get("option_id"), "option_id")
            if oid in ids:
                raise ValueError("Повторяющийся option_id.")
            ids.add(oid)
            for key, label in CONCEPT_FIELDS.items():
                value = option.get(key, "")
                if not isinstance(value, str):
                    raise ValueError(f"{key} должен быть текстом.")
                option[key] = value
                if not value.strip():
                    gaps.append(f"{oid}: уточнить {label.lower()}.")
        chosen = payload.get("proposed_principal")
        if chosen not in ids:
            raise ValueError("Предлагаемый ведущий вариант отсутствует в options.")
        reason = payload.get("choice_reason", "")
        if not isinstance(reason, str):
            raise ValueError("choice_reason должен быть текстом.")
        if not reason.strip():
            gaps.append("Объяснить выбор ведущей формулировки.")
        return {"concept": {"options": options, "proposed_principal": chosen, "choice_reason": reason},
                "gaps": gaps, "sources": [], "arguments": [], "objections": [], "changes": [],
                "original": None, "candidate": None}

    def _compose(self, parent: dict[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
        if parent["action"] != "plan":
            raise ValueError("compose требует сохранённую концепцию plan; для правок используйте revise.")
        packet = deepcopy(parent)
        original = _normalize_complaint(payload.get("complaint"), self.matter_id)
        packet["original"] = original
        packet["candidate"] = _proposal(original)
        packet["sources"], texts = self._sources([], payload.get("sources", []))
        cards = _items(payload.get("arguments"), "arguments")
        if not cards:
            raise ValueError("Нужна хотя бы одна карточка довода.")
        sentences = _sentences(packet["candidate"])
        used, ids = set(), set()
        for raw in cards:
            card = self._argument(raw, packet["sources"], texts)
            sid, aid = card["sentence_id"], card["argument_id"]
            if sid not in sentences or sid in used or aid in ids:
                raise ValueError("Неизвестное предложение или повторяющаяся карточка довода.")
            used.add(sid); ids.add(aid)
            before = sentences[sid]["text"]
            self._replace_text(packet["candidate"], sid, card["proposed_text"])
            packet["arguments"].append(card)
            self._seed_objection(packet, card)
            packet["changes"].append({"sentence_id": sid, "before": before, "after": card["proposed_text"],
                                      "reason": "Сборка довода из записанных оснований.", "objection_ids": []})
        packet["unmapped_sentence_ids"] = [sid for sid in sentences if sid not in used]
        return packet

    @staticmethod
    def _seed_objection(packet: dict[str, Any], card: dict[str, Any]) -> None:
        reason = card["strongest_objection"]
        sid = card["sentence_id"]
        if not reason.strip() or any(item["sentence_id"] == sid and item["reason"] == reason for item in packet["objections"]):
            return
        packet["objections"].append({
            "objection_id": "objection-" + _digest([sid, reason])[:16], "sentence_id": sid,
            "wording_sha256": card["wording_sha256"], "reason": reason,
            "suggested_change": card["response"] or "Подготовить ответ и исправление.",
            "review_reason": "Возражение из карточки довода; отдельная проверка ещё не выполнена.",
            "status": "open", "history": [], "review_kind": "editorial", "independent_legal_review": False,
        })

    @staticmethod
    def _replace_text(complaint: dict[str, Any], sid: str, text: str) -> None:
        for section in complaint["sections"]:
            for sentence in section["sentences"]:
                if sentence["sentence_id"] == sid:
                    sentence.update(text=text, support_status="pending")
                    return
        raise ValueError("Предложение не найдено.")

    def _review(self, parent: dict[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
        packet = deepcopy(parent)
        sentences = _sentences(packet["candidate"])
        objections = {item["objection_id"]: item for item in packet["objections"]}
        seen = set()
        for finding in _items(payload.get("findings"), "findings"):
            oid = _text(finding.get("objection_id"), "objection_id")
            sid = finding.get("sentence_id")
            if oid in seen or sid not in sentences:
                raise ValueError("Повторяющееся замечание или неизвестное предложение.")
            seen.add(oid)
            if finding.get("wording_sha256") != _wording(sentences[sid]["text"]):
                raise ValueError("Замечание относится к другой редакции абзаца.")
            if finding.get("status") not in {"open", "addressed"}:
                raise ValueError("Допустимы open или addressed; юридическое одобрение здесь не выдаётся.")
            for key in ("reason", "suggested_change", "review_reason"):
                _text(finding.get(key), key)
            old = objections.get(oid)
            if old and (old["sentence_id"] != sid or old["reason"] != finding["reason"]):
                raise ValueError("Нельзя подменить смысл замечания под прежним идентификатором.")
            history = list(old.get("history", [])) if old else []
            if old:
                history.append({key: value for key, value in old.items() if key != "history"})
            objections[oid] = {**finding, "history": history, "review_kind": "editorial", "independent_legal_review": False}
        packet["objections"] = list(objections.values())
        packet["changes"] = []
        return packet

    def _revise(self, parent: dict[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
        packet = deepcopy(parent)
        packet["sources"], texts = self._sources(packet["sources"], payload.get("sources", []))
        sentences = _sentences(packet["candidate"])
        arguments = {item["sentence_id"]: item for item in packet["arguments"]}
        objections = {item["objection_id"]: item for item in packet["objections"]}
        edits = _items(payload.get("edits"), "edits")
        if not edits:
            raise ValueError("Нет предлагаемых правок.")
        packet["changes"] = []
        seen = set()
        for edit in edits:
            sid = edit.get("sentence_id")
            if sid not in sentences or sid in seen:
                raise ValueError("Неизвестное или повторяющееся предложение в правках.")
            seen.add(sid)
            before = sentences[sid]["text"]
            if edit.get("before_sha256") != _wording(before):
                raise ValueError("Исходный абзац изменился; правка устарела.")
            reason = _text(edit.get("reason"), "edit.reason")
            refs = edit.get("objection_ids", [])
            if not isinstance(refs, list) or any(oid not in objections or objections[oid]["sentence_id"] != sid for oid in refs):
                raise ValueError("Правка ссылается на неизвестное или чужое замечание.")
            card = self._argument(_mapping(edit.get("argument"), "edit.argument"), packet["sources"], texts)
            if card["sentence_id"] != sid:
                raise ValueError("Карточка довода относится к другому предложению.")
            old = arguments.get(sid)
            if old and card["argument_id"] != old["argument_id"]:
                raise ValueError("Сохраняйте argument_id редактируемого довода.")
            if any(item["argument_id"] == card["argument_id"] and target != sid for target, item in arguments.items()):
                raise ValueError("Повторяющийся argument_id.")
            after = card["proposed_text"]
            if after == before:
                raise ValueError("Правка не меняет текст.")
            stronger = old is not None and LEVELS[card["inference_level"]] > LEVELS[old["inference_level"]]
            if stronger:
                card["gaps"].append("Вывод усилен; отдельно проверить достаточность новых оснований.")
            arguments[sid] = card
            self._replace_text(packet["candidate"], sid, after)
            packet["changes"].append({"sentence_id": sid, "before": before, "after": after, "reason": reason,
                                      "objection_ids": refs, "inference_strengthened": stronger})
            for objection in packet["objections"]:
                if objection["sentence_id"] == sid:
                    history = objection.setdefault("history", [])
                    history.append({key: deepcopy(value) for key, value in objection.items() if key != "history"})
                    objection["status"] = "needs_recheck"
            self._seed_objection(packet, card)
        packet["arguments"] = list(arguments.values())
        packet["unmapped_sentence_ids"] = [sid for sid in sentences if sid not in arguments]
        return packet

    def _documents(self, packet: dict[str, Any]) -> dict[str, str]:
        concept = packet["concept"]
        lines = ["# Концепция жалобы", "", NOTICE, "",
                 "Предлагаемый ведущий вариант: " + concept["proposed_principal"],
                 "Причина выбора: " + (concept["choice_reason"] or "НЕ УСТАНОВЛЕНА"), ""]
        for option in concept["options"]:
            lines.extend(["## " + option["option_id"], ""])
            lines.extend(f"- {label}: {option[key] or 'ТРЕБУЕТ УТОЧНЕНИЯ'}" for key, label in CONCEPT_FIELDS.items())
            lines.append("")
        lines.extend(["## Пробелы концепции", "", *["- " + gap for gap in packet["gaps"]]])
        evidence = ["# Основания доводов", "", "Совпадение цитаты не подтверждает её автора, подлинность источника или юридический вывод.", ""]
        for card in packet["arguments"]:
            evidence.extend(["## " + card["argument_id"], "", "Предложение: " + card["sentence_id"],
                             "Сила вывода: " + LEVEL_LABELS[card["inference_level"]], ""])
            evidence.extend(f"- {label}: {card[key] or 'ТРЕБУЕТ УТОЧНЕНИЯ'}" for key, label in ARGUMENT_FIELDS.items())
            for item in card["evidence"]:
                evidence.extend(["", f"Источник {item['source_id']}, символы {item['start']}–{item['end']}:", "", item["quote"]])
            evidence.extend(["", *["- " + gap for gap in card["gaps"]], ""])
        if packet.get("unmapped_sentence_ids"):
            evidence.extend(["## Предложения без карточек доводов", "", *packet["unmapped_sentence_ids"]])
        statuses = {"open": "Открыто", "addressed": "Заявлено устранение; юридическое одобрение отсутствует", "needs_recheck": "Нужна повторная проверка"}
        objections = ["# Возражения и повторная проверка", "", NOTICE, ""]
        if not packet["objections"]:
            objections.append("Замечания ещё не записаны; проверка возражений не подтверждена.")
        for item in packet["objections"]:
            objections.extend(["## " + item["objection_id"], "", statuses[item["status"]],
                               "Предложение: " + item["sentence_id"], item["reason"],
                               "Предлагаемая правка: " + item["suggested_change"], "Результат проверки: " + item["review_reason"], ""])
        changes = ["# Объяснение предлагаемых правок", "", NOTICE, ""]
        for item in packet["changes"]:
            changes.extend(["## " + item["sentence_id"], "", item["reason"],
                            "Было: " + item["before"], "Предлагается: " + item["after"], ""])
            if item.get("inference_strengthened"):
                changes.append("УСИЛЕНИЕ ВЫВОДА: требуется отдельная проверка оснований.")
        documents = {"concept.md": "\n".join(lines) + "\n", "argument-evidence.md": "\n".join(evidence) + "\n",
                     "objections.md": "\n".join(objections) + "\n", "changes.md": "\n".join(changes) + "\n"}
        if packet["candidate"] is not None:
            original, proposed = _draft_text(packet["original"]), _draft_text(packet["candidate"])
            documents.update({"original-draft.md": original, "proposed-draft.md": proposed,
                              "original-complaint.json": json.dumps(packet["original"], ensure_ascii=False, indent=2) + "\n",
                              "changes.diff": "".join(difflib.unified_diff(original.splitlines(True), proposed.splitlines(True),
                                                                          fromfile="original", tofile="proposed")),
                              "render-payload.json": json.dumps({"schema_version": SCHEMA_VERSION, "complaint": packet["candidate"]},
                                                                 ensure_ascii=False, indent=2) + "\n"})
        return documents

    def _save(self, packet: dict[str, Any]) -> dict[str, Any]:
        if packet["candidate"] is not None:
            packet["candidate"] = _proposal(packet["candidate"])
        packet["draft_sha256"] = _digest(packet["candidate"]) if packet["candidate"] is not None else None
        documents = self._documents(packet)
        self.exports.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix=packet["action"] + "-", dir=self.exports))
        artifacts = []
        for name, text in documents.items():
            path = directory / name
            data = text.encode("utf-8")
            path.write_bytes(data)
            artifacts.append({"path": str(path.relative_to(self.workspace)), "sha256": sha256_bytes(data), "size": len(data)})
        packet["artifacts"] = artifacts
        reference = self.store.put_bytes(canonical_json_bytes(packet))
        scope_gaps = ([f"Предложений без карточки довода: {len(packet['unmapped_sentence_ids'])}; их основания здесь не проверялись."]
                      if packet.get("unmapped_sentence_ids") else [])
        return {"packet": reference, "draft_sha256": packet["draft_sha256"], "output_dir": str(directory),
                "artifacts": artifacts, "gaps": packet["gaps"] + [gap for card in packet["arguments"] for gap in card["gaps"]] + scope_gaps,
                "open_objections": sum(item["status"] != "addressed" for item in packet["objections"]), **BOUNDARIES}
