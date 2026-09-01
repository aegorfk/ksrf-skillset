# Проектирование

## Инвариант

Каждый submission-пакет должен быть самодостаточно проверяемым. Три обязательных значения нельзя оставлять только в поясняющем тексте после формы: они должны иметь отдельные поля внутри `ECHRArgumentPacket`.

## Размещение полей

Поля размещаются непосредственно после `source_form`:

- `reproduction_mode` — доказуемый способ воспроизведения довода в публичном акте либо `unclear`, если акт не позволяет отличить цитирование от пересказа;
- `original_application_in_source` — для submission из публичного акта строго `false`;
- `complaint_completeness` — для такого источника строго `unknown_from_public_act`.

Поля не делают submission позицией Суда и не заменяют `source_actor`, `source_function`, `source_role`, `speaker_verified` или `court_treatment`.

## TDD и stop rule

1. RED: тест извлекает только fenced-блок формы `ECHRArgumentPacket` и требует три новых поля; на exact base `7c934ebf0282221c0efe3321d6cec57e6c403841` он падает.
2. GREEN: минимально добавить три поля, безопасные значения в проверку submission-gate, positive contract fixture и одну eval expectation.
3. REFACTOR: не расширять изменение за пределы четырёх содержательных файлов скилла и механически пересобранного manifest; не менять соседние policy gates.

Candidate-этап заканчивается, когда узкий тест, полный test suite скилла, строгая OpenSpec-валидация и чистая проверка из отдельной копии проходят. На этом этапе публикация разрешена только в feature branch; `main` и `~/.codex/skills` остаются неизменными, а OpenSpec change — открытым и неархивированным. Полное завершение change требует отдельного exact-byte human approval, публикации одобренного commit в `main`, проверки live SHA, синхронизации глобального скилла и повторной exact-hash проверки.
