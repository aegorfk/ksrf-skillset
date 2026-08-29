# Корпус неудачных обращений и отказов

## Два слоя, которые нельзя смешивать

### Public official layer

Официальные определения/решения КС РФ подтверждают мотивировку Суда и procedural disposition. Они не подтверждают полный исходный текст жалобы.

Для каждого petition unit сохрани:

- `petition_unit_id`;
- act number/date и official anchor;
- `petition_claim_source=ksrf_act_summary`;
- challenged norm/version signature;
- applicant category только при достаточных данных;
- actually answered question и unanswered subquestions;
- decisive/ancillary barriers с quote locators;
- positive remainder, transfer limit и review state.

Один PDF может охватывать несколько обращений. Не создавай принудительно `complaint:1`, если identity не установлена.

### Private consent-controlled layer

Оригинальная жалоба, письмо Секретариата, исправление, повторная подача и материалы представителя имеют собственные evidence roles. Matter-local анализ разрешён без corpus consent; cross-matter retrieval — нет.

## Событийная модель

Различай:

- `applicant_original`;
- `secretariat_notice` — не судебный отказ и не holding КС РФ;
- `cure_submission`;
- `resubmission`;
- `judicial_determination`;
- `published_outcome_not_found`/`unknown`.

Отсутствие позднего события не доказывает отказ. Неотвеченный подвопрос не считается отклонённым.

## ConsentRecord

Согласие связывается с exact hashes и раздельными целями:

- same-matter use;
- cross-matter retrieval;
- evaluation;
- model training;
- anonymized publication.

Храни полномочия предоставившего, срок/review term, retention scope и withdrawal event. Отзыв немедленно tombstone-ит материал из поиска и rebuild projections; удаление исходных bytes — отдельное явно разрешённое действие.

## Anonymized promotion

Автоматический redaction check + именованный human reviewer одобряют exact derivative hash. В shared layer попадает только производный файл, не private original. Реальные private bytes никогда не входят в bundled skillset; допустимы только schemas, validators и synthetic fixtures.

## Retrieval и delta

Сопоставляй не по словам, а по норме/редакции, disputed meaning, application pattern, constitutional benchmark, refusal barrier и remedy. Для сильного adverse analogue покажи точные совпадения, различия и требуемый ответ.

Ранний отказ и позднее постановление на похожую тему образуют лишь `repair_delta_candidate`, пока independently не доказаны изменённая жалоба, доказательства, нормативный контекст и фактически отвеченный вопрос.

Нулевой результат формулируй: `в проверенном покрытии верифицированный аналог не найден`. Не утверждай полноту при access gaps или unreviewed queue.
