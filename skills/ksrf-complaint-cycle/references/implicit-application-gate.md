# Доказательство явного и имплицитного применения нормы

## Не один score, а три оси

Для каждой пары `норма × судебный акт/стадия` заполни отдельно:

### `norm_use_status`

- `direct_reasoned_use` — суд в собственной мотивировке использовал правило нормы;
- `reasoning_linked_implicit` — суд не назвал номер, но воспроизвёл точную нормативную логику;
- `mentioned_only` — упоминание без операционного использования;
- `party_only` — только довод стороны;
- `quoted_authority_only` — норма встречается в цитате иного акта;
- `reasoned_rejection` — суд мотивированно признал норму неприменимой;
- `unclear`.

### `outcome_causation`

- `determinative`;
- `contributory` с объяснённой причинной ролью;
- `independent_sufficient_ground`;
- `unclear`.

### `preservation_exhaustion`

- `raised_and_reviewed`;
- `raised_not_addressed`;
- `not_raised`;
- `record_missing`;
- `unclear`.

Проверяй сохранение довода по текущему официальному правилу отдельно от того, назвал ли заявитель номер нормы. Суд мог применить нормативную логику sua sponte.

## Четыре совместимых итоговых статуса

- `explicitly_applied` (`directly_applied` принимается только как legacy alias);
- `implicitly_applied_proven`;
- `application_unclear`;
- `not_applied`.

## Conjunctive test для `implicitly_applied_proven`

Одновременно нужны:

1. вопрос, регулируемый конкретной нормой, был перед судом;
2. court-authored reasoning воспроизвёл её точное условие, запрет, презумпцию, разрешение или последствие;
3. исход контрфактически зависит от этого смысла;
4. нет полного самостоятельного основания, удерживающего тот же исход;
5. для каждого звена есть полный акт, speaker role, locator, quote window и document hash;
6. именованный reviewer одобрил exact record.

Нет хотя бы одного звена → `application_unclear`.

## Когда допустимо `not_applied`

Только при положительном доказательстве: express non-use, reasoned rejection, несовпадение operative conditions либо полное independent ground. Молчание, отсутствие номера статьи и оставление решения без изменения дают `application_unclear`.

## Цепочка инстанций

Сохраняй каждый StageApplicationRecord и итог:

- `survives`;
- `superseded`;
- `concurrent_ground`;
- `chain_unclear`.

Поздний суд наследует мотивировку только при доказанном incorporation locator. Простое оставление акта без изменения не доказывает принятие каждого мотива.

## Admissibility gate

Express use само по себе недостаточно. Нужны judicial norm use, causal harm без полного independent ground, требуемое preservation/exhaustion, правильная редакция, survival в цепочке и human approval. Regex, keyword, RAG и similarity остаются candidate generation.
