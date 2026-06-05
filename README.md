# Скиллы Codex для жалоб в КС РФ

Скиллы для подготовки, проверки и обогащения работы и написанию жалоб и запросов в Конституционный Суд РФ.

## Состав

- `skills/ksrf-argument-patterns` - корпусные паттерны конституционно-правовой аргументации, извлеченные из Постановлений КС РФ.
- `skills/ksrf-*` - глобальные KSRF-скиллы для цикла жалобы, интегрированные с корпусным слоем паттернов.
- `tools/` - локальные скрипты для извлечения и обогащения корпуса аргументативных паттернов КС РФ.
- `openspec/changes/extract-ksrf-argument-pattern-skills` - OpenSpec-изменение с требованиями и дизайном.

Репозиторий намеренно не включает скачанный PDF-корпус и кеш извлеченных текстов.

## Локальная установка

```bash
./install.sh
```

Команда копирует `skills/ksrf-*` в `~/.codex/skills`.

## Перегенерация справочников обогащения

Из исходного проекта, где есть `analysis_results/ksrf_argument_patterns`:

```bash
python3 tools/enrich_ksrf_argument_patterns.py \
  --analysis /Users/aegorfk/Documents/ks_parser_lower_court_marker/analysis_results/ksrf_argument_patterns \
  --skill ./skills/ksrf-argument-patterns
```

## Заметки

Граф конституционно-правовой аргументации хранится в переносимом JSON/Markdown:

- `skills/ksrf-argument-patterns/references/constitutional_graph.json`
- `skills/ksrf-argument-patterns/references/constitutional-graph.md`

Для текущего workflow отдельная графовая база не нужна.
