# Исполняемый контур анализа правоприменительной практики

Этот контур нужен не для подкрепления заранее выбранного тезиса, а для проверки того, можно ли такой тезис вообще сформулировать. Владелец состояния — `ksrf-complaint-cycle`; `ksrf-cassation-judicial-meaning` остаётся отдельным владельцем корпуса и доказательственных артефактов. Обмен идёт только через проверяемые файлы версии `2.0`, без импорта Python-кода соседнего скилла.

## Когда контур обязателен

Запускай scan до `ConstitutionalIssueOptions`, если кандидат или абзац утверждает хотя бы одно из следующего:

- повторяемый, устойчивый или единообразный судебный смысл;
- split, противоречие, межсудебное различие или «хаос»;
- изменение практики во времени, в том числе «до/после» акта высшего суда;
- число, долю или распространённость решений;
- системный эффект, неработоспособность закона или общую причинную связь;
- смысл нормы, приписываемый не одному акту заявителя, а множеству судов.

Автоматический trigger может только потребовать исследование. Снять ложное срабатывание можно лишь отдельным reviewed-решением с причиной, рецензентом, временем и неизменившимся хешем тезиса. Простая цитата одного акта, описание индивидуального применения или официальный правовой якорь без population-level вывода сами по себе не требуют корпуса.

## Основной маршрут

Точка входа:

```bash
python3 ~/.codex/skills/ksrf-complaint-cycle/scripts/ksrf_practice_analysis.py --help
```

1. `init` создаёт приватный файловый workspace дела.
2. `scan` принимает структурированные claims либо TXT/Markdown/DOCX, создаёт стабильные `claim_id` и append-only ревизии.
3. `claim review` фиксирует только человеческое решение `required` или `not-required`; итоговое состояние всегда вычисляется.
4. `request create` выпускает нейтральные `unproven_research_questions`, disconfirmation prompts, ссылки и хеши актов заявителя. Предварительный finding или желаемая формулировка в запрос не включаются.
5. `run attach` вызывает публичный CLI установленного `ksrf-cassation-judicial-meaning` и фиксирует внешний кассационный workspace как trust anchor. Отсутствующий sibling даёт локальный `blocked`, а не падение всего цикла.
6. `result import` принимает portable v2 bundle, пересчитывает request/claim/proof bindings и через sibling `handoff check --source-workspace ... --expected-target ksrf-complaint-cycle` перечитывает исходный request и доказательственные файлы из прикреплённого workspace. Без доступного внешнего anchor пакет сохраняется только как `audit_only_unanchored` и не даёт `ready`.
7. `wording review` требует reviewed-решение `within-limit`, `too-strong` или `unclear` для точной текущей формулировки. Машина не решает семантическую силу юридического тезиса за человека.
8. `validate --stage options|drafting|qa|filing` выдаёт per-claim verdict. Перед filing дополнительно нужен текущий refresh.

Все команды должны быть идемпотентны для тех же bytes. Запись JSON выполняется атомарно; старые ревизии и import receipts не переписываются.

## Состояния тезиса

| Состояние | Значение | Что разрешено |
|---|---|---|
| `not_required` | Корпусный вывод отсутствует либо trigger снят человеком | Обычный маршрут жалобы |
| `required` | Обнаружен эмпирический тезис, запрос ещё не готов | Только вопрос/гипотеза |
| `prepared` | Текущий нейтральный запрос создан | Запуск или продолжение исследования |
| `running` | Корпус собирается/кодируется | Только промежуточный статус |
| `blocked` | Не закрыт сбор, adverse, coverage, bridge, reliability, wording review или proof | `hypothesis_under_test` / `insufficient_coverage` |
| `ready` | Текущий v2 result проверен и точная формулировка признана `within-limit` | Только bounded claim |
| `stale` | Изменился тезис или одна из связанных доказательственных опор | Refresh и повторное reviewed binding |

Matter-wide статус производен от claims. Заблокированный эмпирический тезис не блокирует независимый вариант, раздел или обычный правовой довод. Он также не исправляет и не заменяет admissibility, application, exhaustion, deadline, anti-appeal, remedy и ReleaseGate.

## Что должен доказать portable result

Envelope `2.0` связывает результат с исходным `request_handoff_id`, `request_sha256`, набором `claim_id + claim_sha256`, fingerprint, планом и evidence digest. Reviewed findings строятся самим кассационным CLI из текущих одобренных thesis candidates, position cards, comparisons, relations, adverse review и normative bridge; caller не передаёт произвольный findings JSON.

Пакет включает manifest и копии proof records, отдельные хеши `human-decision.json`, `validation-report.json`, normative bridge и выбранного набора позиций. Эти хеши доказывают внутреннюю целостность, но не подлинность полностью переписанного и заново хешированного пакета. Поэтому drafting-ready требует внешней сверки с прикреплённым source workspace: неизвестный ID, подменённая цитата/роль/relation, усиленный `maximum_permitted_claim`, отсутствующий или изменённый proof не совпадут с доверенными bytes. Legacy `1.0` и internally consistent v2 без anchor можно читать только для аудита.

## Drafting и QA

Для каждого активного эмпирического абзаца ledger хранит locator и hash, trigger, request/result, supporting и adverse IDs, denominator, exclusions, maximum claim, limitations, quality bindings и wording review. Lint возвращает одно из:

- `supported_bounded`;
- `hypothesis_under_test`;
- `insufficient_coverage`;
- `blocking_empirical_overclaim`.

Фразы «все суды», «практика изменилась вследствие», «закон не работает», «судебный хаос доказывает» блокируются, если именно такой предел не разрешён current result и human wording review. Скилл показывает locator и безопасную степень утверждения, но не переписывает жалобу молча.

## Предподачная актуализация

Freshness проверяет отдельно:

- официальные source routes;
- изменения закона;
- новые акты высших судов;
- verified treatments;
- релевантные pending treatments;
- claim/fingerprint/plan/evidence/bridge/approval/validation и quality hashes.

Допустимые результаты: `current_no_material_change`, `bounded_current_with_disclosed_gaps`, `refresh_incomplete`, `material_change_requires_reanalysis`. Новый pending treatment блокирует старый вывод до проверки; неизменившийся и уже раскрытый route gap не превращается в нулевой результат.

## Неподвижные запреты

- Не закрывать queries, coverage, adverse review, coding disagreement или source route автоматически.
- Не сворачивать неопределённость, надёжность или «хаос» в один score.
- Не считать оставление решения без изменения принятием мотивировки нижестоящего суда без собственного выраженного текста кассации.
- Не переносить приватный текст заявителя в публичный корпус или публичный bundle.
- Не использовать практику как самостоятельный предмет проверки КС РФ или как замену нормативному мосту и решению человека.
- Не называть обычный SHA-256 электронной подписью или доказательством авторства; локальные hash chains обнаруживают нарушение порядка/целостности, но не защищают от полного пересоздания журнала владельцем файлов.
