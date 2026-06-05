# Граф конституционно-правовой аргументации

Переносимый JSON-граф для перехода от фактов и дефектов нормы к статьям Конституции, паттернам, доказательствам и инструментам.

## Количество узлов

- `automation_hook`: 58
- `constitutional_article`: 31
- `harm_type`: 59
- `ksrf_decision`: 83
- `norm_type`: 69
- `pattern`: 20

## Количество связей

- `can_be_saved_by`: 20
- `has_anchor`: 160
- `may_trigger`: 153
- `reinforces_with`: 49
- `remedy_with`: 20
- `supported_by`: 60
- `uses_article`: 87

## Как использовать

- Начинай с узлов `norm:*` или `harm:*`, когда факты уже известны.
- Переходи к узлам `pattern:*`, чтобы выбрать семейства аргументов.
- Иди по связям `uses_article`, `has_anchor`, `supported_by` и пакетным связям, чтобы собрать раздел жалобы.
