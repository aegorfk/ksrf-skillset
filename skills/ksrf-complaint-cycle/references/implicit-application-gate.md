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
- `raised_but_not_addressed`;
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
6. существует заранее созданный host-attested approval полного канонического record и fingerprints всех использованных записей цепочки.

Нет хотя бы одного звена → `application_unclear`.

Этот итог относится к доказанности применения, причинно связанного с
оспариваемым последствием, и не стирает отдельные оси. Если court-authored
reasoning действительно воспроизвёл нормативную логику, но тот же исход
удерживает самостоятельное достаточное основание, сохрани
`norm_use_status=reasoning_linked_implicit` и
`outcome_causation=independent_sufficient_ground`; итоговый
`application_status` для admissibility остаётся `application_unclear`, а не
`not_applied`.

## Когда допустимо `not_applied`

Только при положительном доказательстве: express non-use, reasoned rejection,
несовпадение operative conditions либо полное independent ground при отсутствии
доказанного явного **и имплицитного** нормативного использования. Если явное
использование доказано, сохраняй `explicitly_applied`; если доказано
court-authored имплицитное использование, сохраняй
`norm_use_status=reasoning_linked_implicit`. Самостоятельное основание в обоих
случаях отражай отдельно на оси причинности для точного исследуемого
последствия. Молчание, отсутствие номера статьи и оставление решения без
изменения дают `application_unclear`.

Отказ принять предложенный стороной смысл сам по себе не является `reasoned_rejection`: установи, признал ли суд норму неприменимой либо использовал её в ином смысле. Неблагоприятное толкование не стирает доказанного использования нормы.

Если утверждается не обычный `reasoned_rejection`, а общеобязательный вывод о неприменимости нормы или гарантии, дополнительно заполни `NonApplicationEffectRecord` из `../../ksrf-complaint-facts-demands/references/norm-application-defect-map.md`. Различи authoritative inapplicability, обычное судебное non-use, incidental omission и доказанное имплицитное применение; одна отсутствующая ссылка не выбирает ни один статус.

## Цепочка инстанций

Сохраняй каждый StageApplicationRecord и итог:

- `survives`;
- `superseded`;
- `concurrent_ground`;
- `chain_unclear`.

Поздний суд наследует мотивировку только при доказанном incorporation locator. Простое оставление акта без изменения не доказывает принятие каждого мотива.

Если мотивы менялись или сосуществуют несколько оснований, используй [разбор оснований по инстанциям](../../ksrf-complaint-facts-demands/references/cross-instance-causal-drafting.md). Проверяй, удерживает ли другое основание именно заявленное последствие и не зависит ли оно от спорного нормативного смысла; два названных мотива ещё не доказывают их самостоятельность.

## Admissibility gate

Express use само по себе недостаточно. Нужны judicial norm use, causal harm без полного independent ground для того же заявленного последствия, требуемое preservation/exhaustion, правильная редакция, survival в цепочке и доверенное одобрение. Оно связывает не только IDs, но и цитату, locator, speaker/role, premises, causation, preservation, meaning, independent grounds и каждую supporting chain record. Любое изменение требует нового approval; raw `reviewer`/`approved` поля остаются диагностикой. Regex, keyword, RAG и similarity остаются candidate generation.

Самостоятельный процессуальный вред требует отдельного российского правового якоря гарантии, доказательств её нарушения через применение нормы и проверки исправления по [процедурному справочнику QA](../../ksrf-complaint-qa/references/procedural-adequacy-and-cure.md). Он не доказывает иной исход спора по существу и не отменяет существующие проверки допустимости.
