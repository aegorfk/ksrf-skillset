from __future__ import annotations

import functools
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

PARSER_SCRIPTS = {
    "judicial": (
        REPO
        / "skills"
        / "ksrf-cassation-judicial-meaning"
        / "scripts"
        / "judicial_meaning.py"
    ),
    "ksrf": REPO / "skills" / "ksrf-complaint-cycle" / "scripts" / "ksrf.py",
    "practice": (
        REPO
        / "skills"
        / "ksrf-complaint-cycle"
        / "scripts"
        / "ksrf_practice_analysis.py"
    ),
}

STANDALONE_SCRIPTS = {
    "doctor": (
        REPO
        / "skills"
        / "ksrf-complaint-cycle"
        / "scripts"
        / "ksrf_setup_doctor.py"
    ),
    "autocollect": (
        REPO
        / "skills"
        / "ksrf-complaint-cycle"
        / "scripts"
        / "ksrf_autocollect.py"
    ),
    "argument": (
        REPO
        / "skills"
        / "ksrf-explore-arguments"
        / "scripts"
        / "validate_argument_research.py"
    ),
}

STANDALONE_REQUIRED = {
    "doctor": (
        "Проверить возможности",
        "--profile {basic,research,expert}",
        "--manifest ПУТЬ",
        "--allow-network",
        "--json",
        "Коды завершения диагностики:",
        "0 — основные возможности готовы (ready)",
        "2 — некорректные параметры",
        "3 — есть блокирующие пробелы (blocked)",
        "полный отчёт с причинами и следующим действием",
        "ничего не устанавливает и не исправляет автоматически",
        "не подтверждает юридическую готовность жалобы",
    ),
    "autocollect": (
        "ПУТЬ",
        "--out ФАЙЛ",
        "--no-ocr",
        "--ocr-pages ЧИСЛО",
        "--tessdata-dir ПАПКА",
        "--exclude ШАБЛОН",
    ),
    "argument": ("ПУТЬ", "Проверить файл исследования аргументов"),
}

STANDALONE_FORBIDDEN = {
    "doctor": ("MANIFEST",),
    "autocollect": (" OUT", "OCR_PAGES", "TESSDATA_DIR", "GLOB", "paths"),
    "argument": (" PATH",),
}

INSTALLED_PACKAGES = {
    "judicial": "ksrf-cassation-judicial-meaning",
    "ksrf": "ksrf-complaint-cycle",
    "practice": "ksrf-complaint-cycle",
    "doctor": "ksrf-complaint-cycle",
    "autocollect": "ksrf-complaint-cycle",
    "argument": "ksrf-explore-arguments",
}

EXPECTED_PROGRAM_LABELS = {
    "judicial": "judicial_meaning.py",
    "ksrf": "ksrf",
    "practice": "ksrf_practice_analysis.py",
    "doctor": "ksrf doctor",
    "autocollect": "ksrf_autocollect.py",
    "argument": "validate_argument_research.py",
}

EXPECTED_ROUTE_COUNTS = {
    "judicial": 72,
    "ksrf": 21,
    "practice": 18,
    "autocollect": 1,
}

EXPECTED_CONTRACT_SHA256 = {
    "judicial": "19dfb40e1712e9201939330d651e53f4df9d928d7af1cbe2a80756df005f1dd3",
    "ksrf": "356781c1a1fe339cb356ced8662c93e0a520729fce7167b46c6728942f7c9ed8",
    "practice": "ab0639062ade70b5b2c1223a5c37b306762f1fe31802d4bab54fc8c95c6bf173",
    "autocollect": "0279fa088d68fae3dcdee8dddb35a2be5462e5c43922888875f0e664bb1c659d",
}

PUBLICATION_RECOVERY_DIAGNOSTIC_HELP = (
    "--recovery-diagnostic-json",
    "одной компактной ASCII-строкой JSON в стандартном потоке ошибок",
    "может содержать приватные имена записей, device и inode",
    "administrator_only требует администратора",
    "repeat_then_compare_candidate лишь обозначает возможный повтор",
    "не разрешает его автоматически",
    "Стандартный вывод остаётся недействительным",
    "ничего не повторяет, не удаляет и не помещает в карантин",
    "не подтверждает безопасность публикации, юридическую готовность или право подачи",
)

ALLOWED_EXPLICIT_PRESENTATION_METAVARS = {
    (
        "judicial",
        ("quality", "native-reliability", "compare-audit-bundles"),
        "--expected-manifest-sha256",
    ): "SHA256_МАНИФЕСТА_УСПЕШНОГО_ПОВТОРА",
    (
        "judicial",
        ("quality", "native-reliability", "compare-audit-bundles"),
        "--expected-independent-review-packet-sha256",
    ): "SHA256_ZIP_УСПЕШНОГО_ПОВТОРА",
    (
        "judicial",
        ("quality", "native-reliability", "compare-finalizations"),
        "--expected-finalization-receipt-sha256",
    ): "SHA256_УСПЕШНОГО_ПОВТОРА",
    (
        "judicial",
        ("quality", "native-reliability", "compare-review-imports"),
        "--expected-manifest-sha256",
    ): "СОХРАНЁННЫЙ_SHA256_МАНИФЕСТА",
    (
        "judicial",
        ("quality", "native-reliability", "compare-review-imports"),
        "--expected-import-receipt-sha256",
    ): "SHA256_УСПЕШНОГО_ПОВТОРА",
}

INVENTORY_KINDS = (*PARSER_SCRIPTS, "autocollect")

FORBIDDEN_SCAFFOLDING = (
    "usage:",
    "positional arguments:",
    "optional arguments:",
    "options:",
    "show this help message and exit",
)

FORBIDDEN_PROSE = (
    "supplemental",
    "дорожкам frozen plan",
    "bounded status",
    "adverse/coverage/human review",
    "fingerprint дела",
    "текущем fingerprint",
    "fail-closed статус",
    "content-bound handoff",
    "Проверить handoff",
    "handoff в inbox",
    "SQLite-кэш и object store",
    "публичный URL seed",
    "публичный snapshot",
    "закрепить snapshots",
    "public-only пакет",
    "публичных seed",
    "Fail-closed проверить contract",
    "verification gates",
    "retry-задачи",
    "Per-claim gate",
    "matter workspace",
    "practice-dependent claims",
    "corpus request",
    "кассационным workbench",
    "проверенный result",
    "prefiling refresh",
    "OCR fallback",
    "вывод в stdout",
    "Outcome-blind",
    "JSON request payload",
    "request envelope",
    "artifact-derived",
    "practice-quality",
    "совместимый alias",
    "из workspace",
    "Доверенный workspace",
    "без изменения знаменателя",
    "замороженным стратам",
    "исходозначимость",
    "ненумерованный профиль",
    "Идемпотентно",
    "правила перечислителя",
    "связи артефактов анализа",
    "Передать типизированный",
    "детерминированную выборку",
)

REQUIRED_ROUTE_HELP = {
    ("ksrf", ("doctor",)): (
        "Коды завершения диагностики:",
        "0 — основные возможности готовы (ready)",
        "2 — некорректные параметры",
        "3 — есть блокирующие пробелы (blocked)",
        "полный отчёт с причинами и следующим действием",
        "ничего не устанавливает и не исправляет автоматически",
        "не подтверждает юридическую готовность жалобы",
    ),
    ("judicial", ("intake",)): (
        "applicant_judicial_act (судебный акт по делу заявителя)",
    ),
    ("judicial", ("ocr",)): (
        "Код языка Tesseract; по умолчанию rus (русский)",
        "по умолчанию 300 точек на дюйм",
    ),
    ("judicial", ("plan", "template")): (
        "Перезаписать существующий черновик research-plan.json",
    ),
    ("judicial", ("query", "accept")): ("формате ISO 8601",),
    ("judicial", ("query", "supplement")): (
        "exact_norm — точная норма",
        "case_feature — признак дела",
        "формате ISO 8601",
    ),
    ("judicial", ("collect",)): ("по умолчанию 3",),
    ("judicial", ("review",)): (
        "evidence_reviewed — доказательства просмотрены без одобрения тезиса",
        "approved — тезис одобрен",
        "ручную проверку всех неблагоприятных материалов",
        "ручную проверку полноты охвата корпуса",
        "команда не принимает это решение автоматически",
    ),
    ("judicial", ("compare",)): (
        "--applicant ФАЙЛ_ДЕЛА_ЗАЯВИТЕЛЯ",
        "--candidate ФАЙЛ_ДЕЛА_КАНДИДАТА",
        "формате ISO 8601",
    ),
    ("judicial", ("relation", "classify")): (
        "--position-card ФАЙЛ_КАРТОЧКИ_ПОЗИЦИИ",
        "--comparison ФАЙЛ_СОПОСТАВЛЕНИЯ",
        "--applicant-position ФАЙЛ_ПОЗИЦИИ_ЗАЯВИТЕЛЯ",
        "формате ISO 8601",
    ),
    ("judicial", ("adverse", "build")): (
        "opposite_reading — противоположное толкование",
        "later_authority — более поздний акт",
    ),
    ("judicial", ("quality", "prefiling-refresh")): (
        "corpus-evidence-sha256:<64 hex>",
        "JSON-план из cache refresh-plan с явными сегментами охвата",
        "Полный JSON-набор связей из cache treatment",
        "произвольный список не принимается",
        "корневая папка того же публичного корпуса",
        "только для чтения",
        "повторите параметр для каждого требования",
        "по которые проверен корпус: RFC 3339",
        "Контрольный момент начала финального окна подготовки к подаче",
        "не процессуальный срок",
        "с секундами и часовым поясом",
        "Коды завершения проверки качества:",
        "0 — ограниченная проверка завершена (complete=true)",
        "2 — ошибка параметров, входного файла или записи результата",
        "3 — проверка неполна или устарела (complete=false)",
        "не означает юридическую готовность",
    ),
    ("judicial", ("quality", "coding-reliability")): (
        "Коды завершения проверки качества:",
        "0 — ограниченная проверка завершена (complete=true)",
        "2 — ошибка параметров, входного файла или записи результата",
        "3 — проверка неполна или устарела (complete=false)",
        "не означает юридическую готовность",
    ),
    ("judicial", ("quality", "native-reliability")): (
        "Локально и только для чтения проверить три независимых входа",
        "Один совместимый файл coding-reliability.json не подтверждает штатное происхождение",
        "doctor Диагностировать сохранённую тройку без изменения файлов",
        "compare-finalizations",
        "compare-audit-bundles",
    ),
    ("judicial", ("quality", "native-reliability", "doctor")): (
        "--coding-reliability ФАЙЛ_НАДЁЖНОСТИ_КОДИРОВАНИЯ",
        "--coding-audit-finalization-receipt ФАЙЛ_КВИТАНЦИИ_ФИНАЛИЗАЦИИ",
        "--expected-finalization-receipt-sha256 СОХРАНЁННЫЙ_SHA256_ФИНАЛИЗАЦИИ",
        "Неизменённый канонический coding-reliability.json штатной финализации",
        "отдельный совместимый отчёт остаётся только диагностикой",
        "Неизменённый coding-audit-finalization-receipt.json",
        "Отдельно сохранённый строчный SHA-256 из успешного стандартного вывода coding-audit-finalize",
        "не восстанавливается из квитанции",
        "Для статуса valid нужны все три входа",
        "пропуск разрешён только для диагностики incomplete",
        "Стандартный вывод содержит один детерминированный канонический JSON-отчёт",
        "quality coding-reliability остаётся совместимой диагностикой",
        "Коды завершения: 0 — точная техническая связь подтверждена",
        "3 — набор неполон или связь не совпала",
        "2 — переданный вход недоступен или недействителен",
        "Команда не пишет файлы, не обращается к сети или базе данных и ничего не исправляет",
        "Ожидаемый SHA-256 нельзя брать из самой квитанции",
        "повторите финализацию из тех же неизменённых входов в новой соседней папке",
        "побайтово сравните результат",
        "Статус valid не подтверждает личность или независимость проверяющего",
        "юридическую правильность, актуальность права, разрешение на публикацию",
        "одобрение или готовность к подаче",
        "последующий потребитель заново проверяет текущий план",
        "доверенное происхождение и собственные барьеры",
    ),
    (
        "judicial",
        ("quality", "native-reliability", "compare-finalizations"),
    ): (
        "--uncertain-finalization-dir СОМНИТЕЛЬНАЯ_ПАПКА_ФИНАЛИЗАЦИИ",
        "--repeated-finalization-dir ПОВТОРНАЯ_ПАПКА_ФИНАЛИЗАЦИИ",
        "--expected-finalization-receipt-sha256 SHA256_УСПЕШНОГО_ПОВТОРА",
        "две разные полные четырёхфайловые приватные соседние папки",
        "одного фактического безопасного родителя",
        "полного стандартного вывода повторного финализатора",
        "нормального возврата с кодом 0",
        "не берите его из любой квитанции",
        "не используйте SHA-256 сомнительного запуска",
        "отдельные файлы, частичная или staging-папка не принимаются",
        "Коды завершения: 0 — match",
        "3 — mismatch",
        "2 — invalid или unreadable",
        "один детерминированный канонический JSON-отчёт без значений",
        "сырые байты всех четырёх файлов",
        "полный повторный снимок обеих папок",
        "не создаёт выходных файлов",
        "не изменяет, не исправляет, не удаляет и не помещает в карантин",
        "не запускает повтор или другой процесс",
        "не обращается к сети или базе данных",
        "Один код 2 исходного финализатора недостаточен",
        "полная исходная диагностика прямо разрешила",
        "неизменённые входы в новую отсутствующую соседнюю папку",
        "очистку staging, учёт inode или жёстких ссылок",
        "местоположения, целостности, ACL или безопасности",
        "остановите автоматику",
        "системному администратору",
        "учёта всех ссылок и карантина",
        "original_recovery_eligibility_verified=false",
        "repeat_normal_return_verified=false",
        "external_digest_provenance_authenticated=false",
        "original_durability_verified=false",
        "не подтверждает личность проверяющего",
        "юридическую правильность, актуальность права",
        "разрешение на публикацию, одобрение, готовность тезиса или подачу",
        "используйте повторную папку и отдельно сохранённый SHA-256",
        "заново проверьте текущий план, доверенное происхождение",
        "точные связи и все независимые барьеры",
    ),
    (
        "judicial",
        ("quality", "native-reliability", "compare-audit-bundles"),
    ): (
        "--uncertain-audit-bundle-dir СОМНИТЕЛЬНАЯ_ПАПКА_ПАКЕТА",
        "--repeated-audit-bundle-dir ПОВТОРНАЯ_ПАПКА_ПАКЕТА",
        "--expected-manifest-sha256 SHA256_МАНИФЕСТА_УСПЕШНОГО_ПОВТОРА",
        "--expected-independent-review-packet-sha256 SHA256_ZIP_УСПЕШНОГО_ПОВТОРА",
        "из одной полной строки стандартного вывода",
        "нормального возврата с кодом 0",
        "manifest_sha256 нужен последующему импорту",
        "independent_review_packet_sha256 отдельно проверяет передачу ZIP",
        "Не восстанавливайте ни один якорь из манифеста, ZIP или сомнительного запуска",
        "две разные полные семифайловые папки",
        "прямые соседи одного безопасного приватного родителя",
        "отдельные файлы, разные родители, частичная или staging-папка недопустимы",
        "сырые байты всех семи файлов",
        "снимок обеих папок и справочников",
        "Коды завершения: 0 — match",
        "3 — mismatch; 2 — invalid или unreadable",
        "один детерминированный канонический JSON-отчёт без входных значений",
        "не создаёт выходной файл",
        "не исправляет, не копирует, не удаляет, не помещает в карантин",
        "не запускает подготовку, повтор или другой процесс",
        "не обращается к сети или базе данных",
        "Один исходный код 2",
        "полная исходная диагностика предписала повтор тех же неизменённых входов и сравнение",
        "только у системного администратора",
        "нормальный возврат повтора, происхождение обоих SHA, исходную долговечность",
        "не разрешает его дальнейшее использование",
        "не подтверждает личность проверяющего",
        "юридическую правильность, актуальность права, публикацию, готовность жалобы или подачу",
        "Только повторная папка может перейти к новой полной проверке потребителем",
        "Пример команды:",
    ),
    ("judicial", ("quality", "coding-audit-prepare")): (
        *PUBLICATION_RECOVERY_DIAGNOSTIC_HELP,
        "--workspace",
        "--codebook-version",
        "--sample-size",
        "--exclusion-sample-size",
        "--output-dir",
        "screening-candidates.audit.jsonl",
        "primary-decisions.audit.jsonl",
        "coding-audit-plan.json",
        "secondary-review-queue.jsonl",
        "secondary-coding-template.jsonl",
        "coding-audit-inputs-manifest.json",
        "CODING-BRIEF.json",
        "CODING-CODEBOOK.md",
        "manifest_sha256",
        "independent_review_packet_sha256",
        "контракт 1.2",
        "coding-audit-review-import",
        "hypothesis_under_test",
        "без сетевого доступа",
        "намеренно не удаляет",
        "все имена либо жёсткие ссылки",
        "стандартный вывод может быть пустым или частичным",
        "код 2 не означает, что каталога нет",
        "прервано до начала передачи подтверждения",
        "не подтверждено после начала передачи",
        "явно сбросить финальный JSON",
        "не восстанавливайте якорь из первого пакета",
        "ожидающим независимой вторичной проверки",
        "вовсе не иметь расширенных ACL",
        "chmod сама по себе не подтверждает удаление ACL",
        "не означает юридическую готовность",
    ),
    ("judicial", ("quality", "coding-audit-review-import")): (
        *PUBLICATION_RECOVERY_DIAGNOSTIC_HELP,
        "--bundle",
        "--expected-manifest-sha256",
        "--expected-secondary-coder",
        "--secondary-coding",
        "--output-dir",
        "заранее сохранённого стандартного вывода",
        "буквальное присутствие",
        "не проверяет локаторы",
        "0700",
        "0600",
        "audit-decisions.jsonl",
        "coding-reliability",
        "не удостоверяет личность",
        "не является аутентификацией",
        "не является",
        "готовностью к подаче",
        "audited_field_differences",
        "non_audited_content_differences",
        "returned_quote_literal_presence_verified=true",
        "secondary_coder_label_differs_from_each_sampled_primary_label=true",
        "secondary_coder_label_precommit_verified=false",
        "соседн",
        "код 0",
        "оба флага",
        "complete=true",
        "побайтно",
        "не повторяйте команду",
        "inode родителя",
        "карантин",
        "чувствительную копию неучтённой",
        "системного администратора",
        "временная копия считается неучтённой",
        "намеренно не удаляет",
        "вовсе не иметь расширенных ACL",
        "chmod сама по себе не подтверждает удаление ACL",
        "все имена и жёсткие ссылки",
        "стандартный вывод может быть пустым или частичным",
        "код 2 не означает, что каталога нет",
        "прервано до начала передачи подтверждения",
        "не подтверждено после начала передачи",
        "явно сбросить финальный JSON",
        "флаги из успешного повторного вывода",
        "не сбрасывает этот флаг",
        "исправленный полный JSONL",
        "исправьте исходную первичную запись",
        "канонической контрольной суммой решения расхождения",
        "1.1",
        "1.2",
    ),
    ("judicial", ("quality", "coding-audit-finalize")): (
        *PUBLICATION_RECOVERY_DIAGNOSTIC_HELP,
    ),
    ("judicial", ("handoff", "create")): (
        "selected_authorities — устаревший тип версии 1 только для аудита",
        "create его отклоняет, используйте authority_cards",
        "Путь к JSON-файлу с непроверенными вопросами",
        "Путь к JSON-файлу запроса версии 2",
        "по умолчанию текущее время UTC",
    ),
    ("judicial", ("cache", "register-seed")): (
        "по умолчанию official_user_seed",
    ),
    ("judicial", ("cache", "search")): ("по умолчанию 100",),
    ("judicial", ("cache", "ingest")): (
        "--parser-manifest ФАЙЛ_МАНИФЕСТА_ПАРСЕРА",
        "Путь к JSON-файлу с описанием использованного парсера",
        "RFC 3339",
        "будущее время запрещено",
        "Устойчивый идентификатор документа",
        "Идентификатор судебной цепочки",
        "Дорожка запроса",
    ),
    ("judicial", ("cache", "refresh-plan")): (
        "RFC 3339",
        "с секундами и часовым поясом",
        "явно проверяемым сегментом охвата",
        "court_id, period_id, enumerator_id и/или source_role",
    ),
    ("judicial", ("cache", "funnel", "record")): (
        "enumerated — дело найдено в перечне",
        "human_verification_pending — нужна ручная проверка",
    ),
    ("judicial", ("cache", "treatment", "discover")): (
        "applies — применяет",
        "does_not_reach — вопрос не рассмотрен",
    ),
    ("judicial", ("cache", "treatment", "review")): (
        "verified — связь подтверждена",
        "rejected — связь отклонена",
        "court — суд",
        "вручную сверил целевой судебный акт",
        "Причина отклонения кандидата",
        "RFC 3339",
        "по умолчанию текущее время UTC",
    ),
    ("judicial", ("cache", "treatment", "quality-export")): (
        "полный привязанный к корпусу набор всех связей",
        "включает все ID",
        "контрольную сумму популяции",
        "контрольную сумму набора",
    ),
    ("judicial", ("source", "reconcile")): (
        "Начальная дата периода в формате ГГГГ-ММ-ДД",
        "Конечная дата периода в формате ГГГГ-ММ-ДД",
    ),
    ("judicial", ("source", "promote-enumerator")): (
        "по умолчанию текущее время UTC",
    ),
    ("practice", ("claim", "review")): (
        "required — анализ практики нужен",
        "not-required или not_required — анализ не нужен",
    ),
    ("practice", ("wording", "review")): (
        "within-limit или within_limit",
        "too-strong или too_strong",
        "--wording-source ФАЙЛ_ИСТОЧНИКА",
    ),
    ("practice", ("run", "attach")): (
        "Передать запрос в рабочую папку исследования кассационной практики",
    ),
    ("practice", ("result",)): (
        "Импортировать результат исследования для проверки привязок",
    ),
    ("practice", ("result", "import")): (
        "недоверенный результат сохраняется только для аудита",
    ),
    ("practice", ("refresh", "record")): (
        "Дата проверки в формате ГГГГ-ММ-ДД",
        "по умолчанию равна --as-of",
    ),
    ("practice", ("lint",)): (
        "контрольные суммы и цепочки журналов анализа",
    ),
    ("ksrf", ("sources",)): ("verify — проверить официальные источники",),
    ("ksrf", ("application",)): ("analyze — проанализировать применение нормы",),
    ("ksrf", ("issues",)): ("generate — сформировать варианты",),
    ("ksrf", ("failures",)): ("research — исследовать неудачные обращения",),
    ("ksrf", ("evaluate",)): ("run — выполнить оценку качества",),
    ("ksrf", ("render",)): ("build — собрать документы",),
    ("ksrf", ("release",)): (
        "check — проверить комплект перед ручной юридической проверкой",
        "команда не одобряет и не подаёт жалобу",
    ),
}

REQUIRED_PRACTICE_ACTION_HELP = {
    (("init",), "workspace"): ("Корневая папка дела", "practice-analysis"),
    (("init",), "case_id"): ("повторный запуск init", "тем же значением"),
    (("init",), "case_file"): ("JSON-файл CaseFile", "контрольная сумма"),
    (("init",), "argument_research"): (
        "Необязательный JSON-файл ArgumentResearch",
        "без флага привязка гипотез очищается",
    ),
    (("scan",), "workspace"): ("Корневая папка дела после init", "practice-analysis"),
    (("scan",), "input"): ("JSON", "UTF-8 TXT/MD", "DOCX"),
    (("claim", "review"), "workspace"): (
        "Корневая папка дела после scan",
        "журнал practice-analysis",
    ),
    (("claim", "review"), "claim_id"): (
        "Локальный идентификатор",
        "не внешний псевдоним",
    ),
    (("claim", "review"), "decision"): (
        "required — анализ практики нужен",
        "not-required или not_required — анализ не нужен",
    ),
    (("claim", "review"), "reviewer"): ("проверяющего", "журнале решения"),
    (("claim", "review"), "reason"): ("обоснование ручного решения", "журнале"),
    (("request", "create"), "workspace"): (
        "Корневая папка дела",
        "practice-analysis/requests",
    ),
    (("request", "create"), "claim_id"): (
        "флаг можно повторять",
        "required (анализ нужен)",
        "blocked (есть блокирующая проблема)",
        "stale (данные или привязки устарели)",
        "псевдоним",
    ),
    (("request", "create"), "output"): (
        "Дополнительный JSON-файл",
        "основная копия всегда сохраняется в рабочей папке",
    ),
    (("run", "attach"), "workspace"): (
        "Корневая папка дела",
        "practice-analysis/run-attachments.jsonl",
    ),
    (("run", "attach"), "request_id"): ("handoff_id", "SHA-256", "request create"),
    (("run", "attach"), "cassation_workspace"): (
        "если CLI найден, папка создаётся",
        "handoff-inbox.jsonl",
        "не одобряет выводы",
    ),
    (("run", "attach"), "skills_root"): (
        "ksrf-cassation-judicial-meaning",
        "каталог на два уровня выше текущего скрипта",
    ),
    (("result", "import"), "workspace"): (
        "Корневая папка дела",
        "practice-analysis/results",
        "result-imports.jsonl",
    ),
    (("result", "import"), "input"): (
        "JSON-файл результата",
        "сохраняется",
        "только для аудита",
    ),
    (("result", "import"), "request_id"): ("handoff_id", "SHA-256"),
    (("result", "import"), "expected_finalization_receipt_sha256"): (
        "внешний SHA-256",
        "успешного stdout coding-audit-finalize",
        "Значение внутри квитанции его не заменяет",
    ),
    (("result", "import"), "trusted_source_workspace"): (
        "по умолчанию берётся успешно привязанная кассационная папка",
        "Явный путь должен с ней совпадать",
        "сам по себе не снимает режим только для аудита",
    ),
    (("result", "import"), "skills_root"): (
        "Общая папка с каталогом ksrf-cassation-judicial-meaning",
        "по умолчанию берётся CLI успешной привязки",
        "каталог на два уровня выше текущего скрипта",
    ),
    (("wording", "review"), "workspace"): (
        "Корневая папка дела",
        "practice-analysis/wording-reviews.jsonl",
    ),
    (("wording", "review"), "claim_id"): (
        "Локальный ID активного утверждения",
        "не внешний псевдоним",
    ),
    (("wording", "review"), "handoff_id"): (
        "импортированного результата v2 handoff_id",
        "подготовки текста",
    ),
    (("wording", "review"), "decision"): (
        "within-limit или within_limit",
        "too-strong или too_strong",
        "unclear",
    ),
    (("wording", "review"), "reviewer"): (
        "проверяющего",
        "не означает готовность жалобы к подаче",
    ),
    (("wording", "review"), "reason"): ("обоснование решения", "журнале"),
    (("wording", "review"), "finding_id"): (
        "флаг нужно повторить для каждого проверяемого вывода",
    ),
    (("wording", "review"), "wording_text"): (
        "Точная текущая формулировка",
        "совпадать с последним scan",
    ),
    (("wording", "review"), "wording_source"): (
        "отдельным фрагментом",
        "JSON, UTF-8 TXT/MD или DOCX",
    ),
    (("refresh", "record"), "workspace"): (
        "Корневая папка дела",
        "practice-analysis/refreshes.jsonl",
        "validate --stage filing",
    ),
    (("refresh", "record"), "as_of"): (
        "ГГГГ-ММ-ДД",
        "не в будущем",
        "не старше 7 дней",
    ),
    (("refresh", "record"), "reviewer"): (
        "проверяющего",
        "журнале проверки актуальности",
    ),
    (("refresh", "record"), "official_check_ref"): (
        "реквизит ручной проверки официального источника",
        "не проверяет автоматически",
    ),
    (("refresh", "record"), "corpus_cutoff"): (
        "не позже --as-of",
        "по умолчанию равна --as-of",
    ),
    (("status",), "workspace"): (
        "Корневая папка дела",
        "practice-analysis/state.json",
        "claim-index.json",
    ),
    (("status",), "stage"): (
        "Этап локальной проверки",
        "options — выбор варианта работы",
        "drafting — подготовка текста",
        "qa — контроль качества",
        "filing — проверка перед подачей",
        "по умолчанию: drafting",
        "готовый набор утверждений",
        "связанную с ним проверку актуальности",
        "не старше 7 дней",
        "не одобряет и не подаёт жалобу",
    ),
    (("validate",), "workspace"): (
        "Корневая папка дела",
        "practice-analysis/validation-report.json",
    ),
    (("validate",), "stage"): (
        "Этап локальной проверки",
        "options — выбор варианта работы",
        "drafting — подготовка текста",
        "qa — контроль качества",
        "filing — проверка перед подачей",
        "по умолчанию: drafting",
        "готовый набор утверждений",
        "связанную с ним проверку актуальности",
        "не старше 7 дней",
        "не одобряет и не подаёт жалобу",
    ),
    (("lint",), "workspace"): (
        "Корневая папка дела",
        "только читает",
        "структуру practice-analysis",
    ),
}

_INVENTORY_CODE = r"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
skills_root = root / "skills" if (root / "skills").is_dir() else root
kind = sys.argv[2]
if kind == "judicial":
    sys.path.insert(0, str(skills_root / "ksrf-cassation-judicial-meaning" / "lib"))
    from judicial_meaning.cli import build_parser
    parser = build_parser()
elif kind == "ksrf":
    sys.path.insert(0, str(skills_root / "ksrf-complaint-cycle" / "lib"))
    from ksrf.filing.cli import build_parser
    parser = build_parser()
elif kind == "practice":
    path = skills_root / "ksrf-complaint-cycle" / "scripts" / "ksrf_practice_analysis.py"
    spec = importlib.util.spec_from_file_location("practice_cli_help_inventory", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parser = module._build_parser()
elif kind == "autocollect":
    path = skills_root / "ksrf-complaint-cycle" / "scripts" / "ksrf_autocollect.py"
    spec = importlib.util.spec_from_file_location("autocollect_cli_help_inventory", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parser = module._build_parser()
else:
    raise RuntimeError(kind)

records = []

def freeze(value):
    if callable(value):
        return {
            "callable": (
                getattr(value, "__module__", ""),
                getattr(value, "__qualname__", getattr(value, "__name__", "")),
            )
        }
    if isinstance(value, Path):
        return {"path": str(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [freeze(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): freeze(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return {"type": type(value).__name__, "repr": repr(value)}

def choice_values(action):
    choices = action.choices
    if choices is None:
        return None
    if isinstance(choices, dict):
        return list(choices)
    return [freeze(item) for item in choices]

def action_contract(action):
    return {
        "class": type(action).__name__,
        "dest": action.dest,
        "options": list(action.option_strings),
        "nargs": action.nargs,
        "required": action.required,
        "choices": choice_values(action),
        "default": freeze(action.default),
        "const": freeze(action.const),
        "type": freeze(action.type),
        "metavar": freeze(action.metavar),
        "suppressed": action.help is argparse.SUPPRESS,
    }

def state(rows):
    return [
        {
            "route": list(route),
            "prog": current.prog,
            "defaults": freeze(current._defaults),
            "format_usage": current.format_usage(),
            "actions": [action_contract(action) for action in current._actions],
        }
        for route, current in rows
    ]

def walk(current, route):
    rows.append((list(route), current))
    for action in current._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                walk(child, [*route, name])

rows = []
walk(parser, [])
before = state(rows)
for _route, current in rows:
    current.format_help()
rendering_violations = []
if kind == "practice":
    original_columns = os.environ.get("COLUMNS")
    try:
        for width in range(60, 81):
            os.environ["COLUMNS"] = str(width)
            for route, current in rows:
                rendered = current.format_help()
                line_lengths = [len(line) for line in rendered.splitlines()]
                split_token = re.search(
                    r"(?<=[0-9A-Za-zА-Яа-яЁё])-\n\s+"
                    r"(?=[0-9A-Za-zА-Яа-яЁё])",
                    rendered,
                )
                if max(line_lengths, default=0) > width or split_token is not None:
                    rendering_violations.append(
                        {
                            "route": route,
                            "width": width,
                            "max_line": max(line_lengths, default=0),
                            "split_token": split_token.group(0) if split_token else None,
                        }
                    )
    finally:
        if original_columns is None:
            os.environ.pop("COLUMNS", None)
        else:
            os.environ["COLUMNS"] = original_columns
after = state(rows)

contract_json = json.dumps(
    before,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
for route, current in rows:
    value_actions = []
    choice_actions = []
    public_actions = []
    for action in current._actions:
        if isinstance(action, argparse._SubParsersAction):
            choice_actions.append(
                {
                    "option": None,
                    "choices": choice_values(action),
                }
            )
            continue
        if not isinstance(action, argparse._HelpAction):
            public_actions.append(
                {
                    "dest": action.dest,
                    "options": list(action.option_strings),
                    "suppressed": action.help is argparse.SUPPRESS,
                    "help": action.help if isinstance(action.help, str) else None,
                }
            )
        if action.choices is not None and action.help is not argparse.SUPPRESS:
            choice_actions.append(
                {
                    "option": action.option_strings[0] if action.option_strings else None,
                    "choices": choice_values(action),
                }
            )
        if (
            action.nargs == 0
            or action.choices is not None
            or action.help is argparse.SUPPRESS
        ):
            continue
        metavar = action.metavar
        if metavar is None:
            metavar = action.dest.upper() if action.option_strings else action.dest
        if isinstance(metavar, tuple):
            metavar = metavar[0]
        value_actions.append(
            {
                "option": action.option_strings[0] if action.option_strings else None,
                "old_metavar": str(metavar),
            }
        )
    records.append(
        {
            "route": route,
            "value_actions": value_actions,
            "choice_actions": choice_actions,
            "public_actions": public_actions,
            "description": current.description,
            "has_subparsers": any(
                isinstance(action, argparse._SubParsersAction)
                for action in current._actions
            ),
        }
    )

hidden_fixture = None
if kind == "judicial":
    fixture_args = parser.parse_args(
        ["collect", "--workspace", "/tmp/workspace", "--fixture-dir", "/tmp/fixtures"]
    )
    hidden_fixture = {
        "fixture_dir": fixture_args.fixture_dir,
        "handler": freeze(fixture_args.func),
    }

print(json.dumps({
    "records": records,
    "state_restored": before == after,
    "contract_sha256": hashlib.sha256(contract_json.encode("utf-8")).hexdigest(),
    "hidden_fixture": hidden_fixture,
    "rendering_violations": rendering_violations,
}, ensure_ascii=False, sort_keys=True))
"""


def _inventory_at(kind: str, root: Path) -> dict[str, object]:
    completed = subprocess.run(
        [PYTHON, "-c", _INVENTORY_CODE, str(root), kind],
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)


@functools.lru_cache(maxsize=None)
def _inventory(kind: str) -> dict[str, object]:
    return _inventory_at(kind, REPO)


def _normalized(text: str) -> str:
    return " ".join(text.split())


class RemainingRuntimeCLIRussianHelpTests(unittest.TestCase):
    def test_recursive_inventory_and_machine_contract_are_stable(self) -> None:
        for kind in INVENTORY_KINDS:
            with self.subTest(kind=kind):
                inventory = _inventory(kind)
                records = inventory["records"]
                self.assertEqual(len(records), EXPECTED_ROUTE_COUNTS[kind])
                self.assertEqual(
                    inventory["contract_sha256"],
                    EXPECTED_CONTRACT_SHA256[kind],
                )
                self.assertTrue(inventory["state_restored"])
        self.assertEqual(
            _inventory("judicial")["hidden_fixture"],
            {
                "fixture_dir": "/tmp/fixtures",
                "handler": {
                    "callable": ["judicial_meaning.cli", "cmd_collect"],
                },
            },
        )

    def test_every_installed_help_route_uses_russian_presentation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            install = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(installed)],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            practice_inventories = {
                location: inventory
                for location, inventory in (
                    ("source", _inventory("practice")),
                    ("installed", _inventory_at("practice", installed)),
                )
            }
            practice_action_projections = {}
            for location, inventory in practice_inventories.items():
                public_actions = [
                    (tuple(record["route"]), action)
                    for record in inventory["records"]
                    for action in record["public_actions"]
                ]
                actions_by_key = {
                    (route, action["dest"]): action
                    for route, action in public_actions
                }
                practice_action_projections[location] = {
                    (route, action["dest"], tuple(action["options"])): (
                        action["suppressed"],
                        action["help"],
                    )
                    for route, action in public_actions
                }
                with self.subTest(practice_inventory=location):
                    self.assertEqual(len(inventory["records"]), 18)
                    self.assertEqual(
                        inventory["contract_sha256"],
                        EXPECTED_CONTRACT_SHA256["practice"],
                    )
                    self.assertTrue(inventory["state_restored"])
                    self.assertEqual(inventory["rendering_violations"], [])
                    self.assertEqual(len(public_actions), 43)
                    self.assertEqual(len(actions_by_key), 43)
                    self.assertEqual(
                        set(actions_by_key),
                        set(REQUIRED_PRACTICE_ACTION_HELP),
                    )
                    missing_help = [
                        {
                            "route": route,
                            "dest": action["dest"],
                            "options": action["options"],
                        }
                        for route, action in public_actions
                        if action["suppressed"]
                        or not isinstance(action["help"], str)
                        or not action["help"].strip()
                    ]
                    self.assertEqual(missing_help, [])
                    non_russian_help = [
                        {
                            "route": route,
                            "dest": action["dest"],
                            "options": action["options"],
                        }
                        for route, action in public_actions
                        if isinstance(action["help"], str)
                        and re.search(r"[А-Яа-яЁё]", action["help"]) is None
                    ]
                    self.assertEqual(non_russian_help, [])
                    for key, required_fragments in REQUIRED_PRACTICE_ACTION_HELP.items():
                        action = actions_by_key.get(key)
                        self.assertIsNotNone(action, key)
                        if action is None or not isinstance(action["help"], str):
                            continue
                        for required in required_fragments:
                            self.assertIn(required, action["help"], key)

            self.assertEqual(
                practice_action_projections["installed"],
                practice_action_projections["source"],
            )

            installed_practice_records = {
                tuple(record["route"]): record
                for record in practice_inventories["installed"]["records"]
            }

            all_outputs: list[str] = []
            for kind, source in PARSER_SCRIPTS.items():
                script = installed / INSTALLED_PACKAGES[kind] / "scripts" / source.name
                records = _inventory(kind)["records"]
                for record in records:
                    route = tuple(record["route"])
                    with self.subTest(kind=kind, route=route):
                        route_env = {
                            **os.environ,
                            "PYTHONDONTWRITEBYTECODE": "1",
                        }
                        if kind == "practice":
                            route_env["COLUMNS"] = "60"
                        completed = subprocess.run(
                            [PYTHON, str(script), *route, "--help"],
                            cwd=root,
                            env=route_env,
                            text=True,
                            capture_output=True,
                            check=False,
                        )
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertEqual(completed.stderr, "")
                        normalized = _normalized(completed.stdout)
                        self.assertIn("Использование:", normalized)
                        self.assertIn(
                            f"Использование: {EXPECTED_PROGRAM_LABELS[kind]}",
                            normalized,
                        )
                        self.assertIn("параметры:", normalized)
                        self.assertIn("показать эту справку и выйти", normalized)
                        description = record["description"]
                        self.assertIsInstance(description, str)
                        self.assertTrue(description.strip())
                        self.assertIn(_normalized(description), normalized)
                        if record["has_subparsers"]:
                            self.assertIn("команды:", normalized)
                            self.assertNotIn("позиционные аргументы:", normalized)
                        for forbidden in FORBIDDEN_SCAFFOLDING:
                            self.assertNotIn(forbidden, normalized)
                        for action in record["value_actions"]:
                            option = action["option"]
                            old_metavar = action["old_metavar"]
                            allowed_metavar = (
                                ALLOWED_EXPLICIT_PRESENTATION_METAVARS.get(
                                    (kind, tuple(route), option)
                                )
                            )
                            if allowed_metavar is not None:
                                self.assertEqual(old_metavar, allowed_metavar)
                                self.assertIn(
                                    f"{option} {allowed_metavar}",
                                    normalized,
                                )
                                continue
                            if re.fullmatch(
                                r"[А-ЯЁ][А-ЯЁ0-9_-]*",
                                old_metavar,
                            ):
                                if option is None:
                                    self.assertRegex(
                                        normalized,
                                        rf"(?<![\w-]){re.escape(old_metavar)}(?![\w-])",
                                    )
                                else:
                                    self.assertIn(
                                        f"{option} {old_metavar}",
                                        normalized,
                                    )
                                continue
                            if option is None:
                                self.assertIsNone(
                                    re.search(
                                        rf"(?<![\w-]){re.escape(old_metavar)}(?![\w-])",
                                        normalized,
                                    ),
                                    normalized,
                                )
                            else:
                                self.assertNotIn(
                                    f"{option} {old_metavar}",
                                    normalized,
                                )
                                self.assertRegex(
                                    normalized,
                                    rf"{re.escape(option)}\s+[А-ЯЁ][А-ЯЁ0-9_-]*",
                                )
                        for action in record["choice_actions"]:
                            for choice in action["choices"]:
                                self.assertRegex(
                                    normalized,
                                    rf"(?<![\w-]){re.escape(str(choice))}(?![\w-])",
                                )
                        for required in REQUIRED_ROUTE_HELP.get((kind, route), ()):
                            self.assertIn(required, normalized)
                        if kind == "practice":
                            self.assertIsNone(
                                re.search(
                                    r"(?<=[0-9A-Za-zА-Яа-яЁё])-\n\s+"
                                    r"(?=[0-9A-Za-zА-Яа-яЁё])",
                                    completed.stdout,
                                ),
                                completed.stdout,
                            )
                            self.assertLessEqual(
                                max(map(len, completed.stdout.splitlines())),
                                60,
                                completed.stdout,
                            )
                            for action in installed_practice_records[route]["public_actions"]:
                                self.assertFalse(action["suppressed"], action)
                                self.assertIn(
                                    _normalized(action["help"]),
                                    normalized,
                                    {"route": route, "action": action},
                                )
                        all_outputs.append(completed.stdout)

            for kind, source in STANDALONE_SCRIPTS.items():
                script = installed / INSTALLED_PACKAGES[kind] / "scripts" / source.name
                help_flags = ("--help", "-h") if kind == "argument" else ("--help",)
                for help_flag in help_flags:
                    with self.subTest(kind=kind, help_flag=help_flag):
                        completed = subprocess.run(
                            [PYTHON, str(script), help_flag],
                            cwd=root,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                            text=True,
                            capture_output=True,
                            check=False,
                        )
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertEqual(completed.stderr, "")
                        normalized = _normalized(completed.stdout)
                        self.assertIn("Использование:", normalized)
                        self.assertIn(
                            f"Использование: {EXPECTED_PROGRAM_LABELS[kind]}",
                            normalized,
                        )
                        self.assertIn("показать", normalized)
                        for required in STANDALONE_REQUIRED[kind]:
                            self.assertIn(required, normalized)
                        for forbidden in FORBIDDEN_SCAFFOLDING:
                            self.assertNotIn(forbidden, normalized)
                        for forbidden in STANDALONE_FORBIDDEN[kind]:
                            self.assertNotIn(forbidden, normalized)
                        all_outputs.append(completed.stdout)

        public_help = _normalized("\n".join(all_outputs))
        self.assertNotIn("--fixture-dir", public_help)
        for forbidden in FORBIDDEN_PROSE:
            self.assertNotIn(forbidden, public_help)

    def test_supported_legacy_python_help_is_russian(self) -> None:
        legacy_python = Path("/usr/bin/python3")
        if not legacy_python.is_file():
            self.skipTest("Системный Python не установлен")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            install = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(installed)],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            invocations: list[tuple[Path, tuple[str, ...]]] = []
            for kind in ("ksrf", "practice"):
                source = PARSER_SCRIPTS[kind]
                script = installed / INSTALLED_PACKAGES[kind] / "scripts" / source.name
                invocations.extend(
                    (script, (*tuple(record["route"]), "--help"))
                    for record in _inventory(kind)["records"]
                )
            invocations.extend(
                (
                    installed / INSTALLED_PACKAGES[kind] / "scripts" / source.name,
                    ("--help",),
                )
                for kind, source in STANDALONE_SCRIPTS.items()
            )
            invocations.append(
                (
                    installed
                    / INSTALLED_PACKAGES["argument"]
                    / "scripts"
                    / STANDALONE_SCRIPTS["argument"].name,
                    ("-h",),
                )
            )
            self.assertEqual(len(invocations), 43)

            for script, arguments in invocations:
                with self.subTest(script=script.name, arguments=arguments):
                    completed = subprocess.run(
                        [str(legacy_python), str(script), *arguments],
                        cwd=root,
                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    self.assertIn("Использование:", completed.stdout)
                    self.assertNotIn("optional arguments:", completed.stdout)
                    self.assertNotIn(
                        "show this help message and exit",
                        completed.stdout,
                    )

    def test_non_help_diagnostic_projection_is_exact(self) -> None:
        cases = (
            (PARSER_SCRIPTS["judicial"], ()),
            (PARSER_SCRIPTS["judicial"], ("plan",)),
            (PARSER_SCRIPTS["ksrf"], ()),
            (PARSER_SCRIPTS["practice"], ()),
            (STANDALONE_SCRIPTS["autocollect"], ()),
            (STANDALONE_SCRIPTS["argument"], ()),
            (STANDALONE_SCRIPTS["doctor"], ("--profile", "invalid")),
        )
        projection = []
        for script, arguments in cases:
            completed = subprocess.run(
                [PYTHON, str(script), *arguments],
                cwd=REPO,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            projection.append(
                {
                    "script": script.name,
                    "arguments": list(arguments),
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            )
        digest = hashlib.sha256(
            json.dumps(
                projection,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            digest,
            "29bd35eb9807fcaeef9348c6c4dfa34481584940804d7a667c256d809c12902d",
        )


if __name__ == "__main__":
    unittest.main()
