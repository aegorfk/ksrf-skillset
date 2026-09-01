## Why

Пользовательская установка всё ещё содержит `ksrf-argument-patterns/references/complaint-methodology-sources.md` — журнал происхождения и обновления методологии размером 69 194 байта. Файл прямо объявлен source-only provenance-артефактом, не импортируется и не требуется для подготовки жалобы, но остаётся доступен пользователю через несколько runtime-ссылок и generated metadata.

Отдельный runtime-профиль валидатора уже реализован и опубликован: теперь payload можно уменьшить fail-closed, не ослабляя source/release QA.

## What Changes

- Классифицировать только exact identity `ksrf-argument-patterns/references/complaint-methodology-sources.md` как source-only и исключить её из manifest/установки.
- Сохранить файл tracked в source checkout, под source security scan, reverse-sync preservation и public-artifact validation.
- Удалить все runtime-backlinks и заменить их маршрутами к сохранённым operational references.
- Зафиксировать проверяемую матрицу покрытия каждой перенесённой методики и каждого пункта чеклиста: `retained`, `superseded` или `intentionally_rejected`.
- Добавить exact stale-runtime, no-overmatch, clean-room backlink, manifest disclosure и security regression tests.

## Impact

- Из пользовательской установки исчезает один source-only журнал и все мёртвые ссылки на него. Итоговый manifest уменьшается с 237 / 8 153 384 до 236 / 8 088 532 файлов/байт: net-экономия 1 файл / 64 852 байта после добавления недостающих operational gates, общего exact source-only predicate и удаления двух maintainer-only backlog routes.
- Пользователь получает более компактный skillset без crawler provenance, локальных corpus anchors и maintainer update history; рабочие маршруты ведут только к автономным runtime-справочникам.
- Методология не теряется: исключение разрешено только после полного coverage audit и fail-closed теста сохранённых successors.
- Никакие юридические, human-review, filing, release или source-security gates не расширяются.
