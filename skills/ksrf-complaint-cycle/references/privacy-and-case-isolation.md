# Конфиденциальность и изоляция дел

## Default

Любой пользовательский документ по умолчанию:

- `local_confidential`;
- доступен только текущему matter;
- не включён в cross-matter retrieval;
- не передаётся remote provider;
- не входит в skillset, fixtures или публичный отчёт.

## Перед внешней передачей

Покажи пользователю:

- provider;
- точные поля/фрагменты;
- цель;
- срок/retention, если известен;
- альтернативный local path.

Нужно operation-specific согласие. Наличие API key не является согласием на передачу case text.

## Минимизация

Передавай минимум, необходимый для bounded task. Для discovery используй обезличенный query profile, когда возможно. Не передавай полный пакет ради поиска одной нормы.

## Раздельные зоны

- public official evidence;
- case-local confidential evidence;
- private consent-controlled corpus;
- anonymized approved derivative;
- synthetic eval fixtures.

Индексы и embeddings наследуют privacy zone исходника. Отдельная projection не снижает класс конфиденциальности.

## Withdrawal и deletion

Отзыв согласия немедленно исключает запись и производные projections из retrieval и инвалидирует зависимые findings. Удаление исходного файла выполняется только по отдельному явному указанию и с точным target manifest; audit tombstone сохраняет факт отзыва без private text.

## Publication guard

Перед публикацией skillset проверь отсутствие:

- real complaints и Secretariat correspondence;
- consent/person identifiers;
- connector tokens и tokenized URLs;
- local case paths;
- `.serena`, `__pycache__`, `*.pyc` и runtime output.
