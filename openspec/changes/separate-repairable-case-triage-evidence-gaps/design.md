## Context

В стабильной версии application gate уже fail-closed, но выходной контракт не заставляет различать: (a) акт или locator известен и контекст можно получить контролируемым действием; (b) критический акт не получен после зафиксированного bounded official search. Это приводит не к ложному `pass`, а к неточному operational route и неполному repair packet.

## Goals / Non-Goals

**Goals:**

- направлять исправимый evidence gap в `FIX_FIRST`;
- разрешать `ABSTAIN_PENDING_RECORD` только после документированного исчерпанного поиска недоступной записи;
- выдавать одну проверяемую repair-задачу для конкретной нормы и стадии;
- сохранять `application_unclear` и blocked readiness до завершения evidence packet.

**Non-Goals:**

- доказывать применение нормы или допустимость без полного акта;
- автоматически получать непубличные акты;
- менять правовую позицию, составлять жалобу или выдавать filing authority;
- расширять изменение на остальные KSRF skills.

## Decisions

1. **Route зависит от контролируемости пробела.** Наличие точного акта, страницы или locator делает следующий шаг repair-задачей `FIX_FIRST`; отсутствие записи после журналированного bounded search допускает `ABSTAIN_PENDING_RECORD`.
2. **Одна строка на `норма × стадия`.** `ApplicationEvidenceRecord` сохраняет identity/hash акта, court/stage/date, locator и полное окно, speaker role, три оси, independent ground, chain/preservation, missing fields и bounded next task.
3. **Цитата проверяется в обе стороны.** Для неполного окна repair включает `claim→source`, `source→claim`, `quote→page`, роль автора, причинный фрагмент и самостоятельные основания на той же официальной версии.
4. **Юридический статус не повышается ремонтом.** Пока обязательное поле отсутствует, combined status остаётся `application_unclear`, application gate не становится `pass`, а filing readiness остаётся false.

## Risks / Trade-offs

- **[Избыточный вывод]** → одна компактная строка на норму и стадию, без дублирования полного акта.
- **[Ложная контролируемость]** → `FIX_FIRST` требует точного известного объекта и ограниченного действия; иначе фиксируется search journal и используется abstain.
- **[Смешение retrieval и legal conclusion]** → успешный ремонт только повторно запускает gate и сам по себе не повышает статус.

## Verification Plan

1. Зафиксировать SHA стабильных skill/eval bytes и слепой baseline.
2. Добавить adversarial eval с имеющимся актом и обрезанным окном; прежние три evals оставить controls.
3. Прогнать skill validator, JSON validation, строгий OpenSpec validation и repo tests.
4. Выполнить независимый forward-test stable/candidate на одинаковых входах; равенство считать плато, а не улучшением.
