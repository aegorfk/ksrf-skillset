## Why

Успешная установка теперь говорит с пользователем по-русски, но отказ
обязательной проверки публикации всё ещё передаёт сырой англоязычный stderr с
внутренними путями, SHA и деталями Git/Python. Пользователю нужна безопасная
причина остановки и понятное следующее действие, а подробности должны остаться в
отдельном maintainer-интерфейсе.

## What Changes

- Canonical `./install.sh` при отказе publication guard скрывает его stdout и
  stderr и выводит фиксированное ограниченное русское объяснение с действием.
- Точный ненулевой код guard сохраняется, writer не запускается, success и
  `export` не печатаются.
- Прямой `tools/verify_publication_state.py`, его JSON, подробные ошибки и
  maintainer-синхронизация остаются без изменений.
- Отдельная установка через явный non-canonical `--target` сохраняет прежний
  маршрут без publication guard.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

- `ksrf-skillset-install-transaction`: заменить сырой failure-output вложенного
  guard фиксированным безопасным пользовательским сообщением.
- `ksrf-skillset-install-status`: уточнить совместимость обычной установки с
  узким изменением presentation отказа при неизменных операциях и кодах.

## Impact

Затрагиваются `install.sh`, shell-регрессии, прямой CLI-регрессионный тест,
README и две существующие OpenSpec-спеки. Runtime-состав, транзакционный writer,
publication policy, сетевые операции и maintainer CLI не меняются.
