# Официальный источник и контроль редакций

## Две независимые координаты

`authority_class` описывает издателя/юридический вес:

- `official_primary`;
- `official_derivative`;
- `discovery_only`;
- `user_supplied_unverified`.

`acquisition_transport` описывает способ получения:

- `direct_http`;
- `browser`;
- `manual_import`;
- `firecrawl`;
- `mcp`;
- иной заявленный adapter.

Firecrawl может доставить официальный URL, но transport не делает извлечённый summary официальным доказательством. Для promotion нужны raw identity, hash и официальный anchor.

## SourceObservation и SourceEvidence

Попытка поиска возвращает один из статусов:

- `retrieved`;
- `not_found` — только после успешно завершённого bounded official query;
- `unavailable`;
- `interactive_required`;
- `invalid_response`;
- `conflict`.

CAPTCHA означает `interactive_required`; не используй solver в filing-readiness контуре. `403`, timeout и DNS error не являются нулевым результатом.

Полученный документ хранит origin URL, transport, HTTP/content type при наличии, raw/extracted hashes, identity checks, tool versions, transform chain, locator и visual check.

## NormVersionPassport

Для каждой оспариваемой нормы заполни:

- структурную ссылку: акт, статья, часть, пункт;
- official publication identity;
- `legal_timepoints[]`: материальное событие, процессуальные действия, каждый судебный акт, текущая дата подачи;
- `edition_segments[]` с `effective_from` и `effective_to_exclusive`;
- modifying acts и переходные положения;
- точный controlling text и hash;
- reason why edition governs each timepoint;
- official anchors;
- provider cross-checks и conflicts;
- reviewer и freshness.

Case-time редакция и current filing-time редакция не схлопываются. Если интервал пересекает поправку, создай несколько segments.

## Вес дополнительных providers

ГАРАНТ, Casus Legal, mirrors, doctrine, поисковые системы, embeddings и LLM помогают найти, сравнить или мониторить. Они не закрывают official-source gate самостоятельно. Конфликт provider/официального текста блокирует паспорт до ручного разрешения.

## Pre-filing refresh

Перед release повторно проверь official anchor, controlling edition, применимые формальные правила, актуальность позиции КС РФ и зависимые locators. Изменение инвалидирует конкретные sentence IDs и issue options, а не только общий timestamp.
