# Схема выходных данных

Каждый запуск пишет файлы в папку `output/<банк>_<ГГГГММДД-ЧЧММСС>/` (время запуска в UTC). Какие файлы выписки
писать, задаёт `STORAGE__FORMAT`; отчёт о полноте пишется всегда.

| Файл                     | Формат `json` | Формат `csv` | Формат `both` |
|--------------------------|:-------------:|:------------:|:-------------:|
| `statement.json`         | да            |              | да            |
| `products.csv`           |               | да           | да            |
| `transactions.csv`       |               | да           | да            |
| `extraction_report.json` | да            | да           | да            |

Общие правила:

- суммы — точные десятичные числа с двумя знаками после точки (`-1450.00`), в JSON — числом, а не строкой
  и не float; минус — списание;
- валюта — код ISO 4217 (`RUB`, `USD`, `EUR`), символы вроде `₽` переводятся в код;
- даты — `ГГГГ-ММ-ДД`, время — ISO 8601 в UTC;
- отсутствующее значение — `null` в JSON и пустая ячейка в CSV; логические значения в CSV — `true` / `false`;
- кодировка UTF-8, разделитель CSV — запятая, первая строка CSV — заголовок (есть и у пустой таблицы).

## `statement.json` — комплексная выписка

| Поле           | Тип                     | Описание                                         |
|----------------|-------------------------|--------------------------------------------------|
| `bank`         | строка                  | Банк из настройки `EXTRACTION__BANK`             |
| `extracted_at` | время UTC               | Когда закончено извлечение                       |
| `period`       | `{from, to}`            | Запрошенный период, обе даты включительно        |
| `products`     | список продуктов        | Все продукты, карточки которых удалось прочитать |
| `transactions` | список операций         | Операции всех продуктов за период                |

### Продукт

| Поле                | Тип                                         | Описание                                                    |
|---------------------|---------------------------------------------|-------------------------------------------------------------|
| `product_id`        | строка                                      | Идентификатор продукта в кабинете                           |
| `type`              | `account` / `card` / `deposit` / `loan`     | Счёт, карта, депозит или накопительный счёт, кредит         |
| `name`              | строка                                      | Название продукта в кабинете                                |
| `masked_number`     | строка                                      | Последние 4 цифры номера карты или счёта: `**** 9012`       |
| `currency`          | код ISO 4217                                | Валюта продукта                                             |
| `balance`           | сумма или `null`                            | Текущий остаток                                             |
| `available_balance` | сумма или `null`                            | Доступный остаток                                           |
| `linked_account_id` | строка или `null`                           | Только у карты: `product_id` счёта, к которому она привязана |
| `requisites`        | объект или `null`                           | Реквизиты счёта, если они видны в кабинете                  |
| `requisites.account_number`        | строка или `null`            | Номер счёта                                                 |
| `requisites.bic`                   | строка или `null`            | БИК                                                         |
| `requisites.correspondent_account` | строка или `null`            | Корреспондентский счёт                                      |
| `requisites.bank_name`             | строка или `null`            | Название банка                                              |
| `details.interest_rate` | число или `null`                        | Ставка, % годовых                                           |
| `details.opened_at`     | дата или `null`                         | Дата открытия                                               |
| `details.credit_limit`  | сумма или `null`                        | Кредитный лимит                                             |
| `details.debt`          | сумма или `null`                        | Остаток долга по кредиту                                    |

Полный номер карты не сохраняется нигде. ФИО клиента не извлекается.

### Операция

| Поле             | Тип                                              | Описание                                                       |
|------------------|--------------------------------------------------|----------------------------------------------------------------|
| `transaction_id` | строка                                           | Устойчивый идентификатор операции                              |
| `id_source`      | `bank` / `generated`                             | Идентификатор выдан банком или сгенерирован прототипом          |
| `product_id`     | строка                                           | Продукт, в истории которого найдена операция (ровно один)      |
| `operation_date` | дата                                             | Дата операции; по ней операция относится к периоду             |
| `posting_date`   | дата или `null`                                  | Дата проведения; нет у операций в обработке и отклонённых      |
| `amount`         | сумма                                            | Сумма со знаком: минус — списание                              |
| `currency`       | код ISO 4217                                     | Валюта операции                                                |
| `type`           | `debit` / `credit`                               | Списание или зачисление, по знаку суммы                        |
| `description`    | строка                                           | Описание из кабинета, пробелы нормализованы                    |
| `counterparty`   | строка или `null`                                | Контрагент                                                     |
| `category`       | см. ниже                                         | Категория; незнакомая — `other`                                |
| `status`         | `posted` / `pending` / `declined` / `unknown`    | Статус; незнакомый — `unknown` с предупреждением в отчёте      |
| `is_duplicate`   | `true` / `false`                                 | Операция карты, которая видна и в истории привязанного счёта   |

Категории: `top_up`, `interest`, `withdrawal`, `transfer`, `salary`, `groceries`, `restaurants`, `transport`,
`shopping`, `refund`, `utilities`, `fee`, `other`.

Сгенерированный идентификатор — первые 16 символов SHA-256 от продукта, даты операции, суммы и описания плюс
порядковый номер одинаковых операций: `ef5888f8a27676d8-1`. Дата проведения в нём не участвует, поэтому
идентификатор не меняется, когда операцию «в обработке» проводят.

**Дубликат** не удаляется: операция остаётся у карты с `is_duplicate: true`, а пара попадает в предупреждения
отчёта. При подсчёте оборотов операции с `is_duplicate: true` нужно пропускать.

## `products.csv` и `transactions.csv`

`transactions.csv` — те же поля операции, что в JSON, в том же порядке. `products.csv` — поля продукта,
вложенные объекты разворачиваются в плоские колонки с префиксом:

```
product_id,type,name,masked_number,currency,balance,available_balance,linked_account_id,requisites_account_number,requisites_bic,requisites_correspondent_account,requisites_bank_name,details_interest_rate,details_opened_at,details_credit_limit,details_debt
```

## `extraction_report.json` — отчёт о полноте извлечения

| Поле                 | Тип                        | Описание                                                         |
|----------------------|----------------------------|------------------------------------------------------------------|
| `bank`               | строка                     | Банк                                                             |
| `period`             | `{from, to}`               | Период                                                           |
| `consent.granted_at` | время UTC                  | Когда клиент нажал «Разрешаю»                                    |
| `consent.scope`      | список строк               | Что клиент разрешил прочитать — тот же текст, что на странице согласия |
| `products_count`     | число                      | Сколько продуктов в выписке                                      |
| `transactions_count` | число                      | Сколько операций в выписке                                       |
| `duration_seconds`   | число                      | Длительность запуска                                             |
| `products`           | список                     | Статус каждого продукта из списка в кабинете                     |
| `products[].product_id`         | строка          | Продукт                                                          |
| `products[].masked_number`      | строка или `null` | Маскированный номер; `null`, если карточка не загрузилась      |
| `products[].status`             | `complete` / `partial` / `failed` | Извлечён полностью, с пропусками или не извлечён |
| `products[].extraction_source`  | `export` / `server_response` / `page` или `null` | Способ, которым получена история |
| `products[].transactions_count` | число           | Операций продукта в выписке                                      |
| `products[].reason`             | строка или `null` | Почему продукт извлечён не полностью или не извлечён           |
| `warnings`           | список строк               | Предупреждения: дубликаты, операции вне периода, незнакомые статусы, повторные попытки, недоступный экспорт, нет фильтра периода |
| `errors`             | список строк               | Ошибки: продукты, карточку или историю которых получить не удалось |

В отчёте только идентификаторы продуктов и операций, маскированные номера и количества: ни сумм, ни описаний,
ни контрагентов.

## Пример

Запуск на демо-банке в режиме `normal` за период 01.05.2026 — 30.06.2026. Показаны не все продукты и операции.

`statement.json`:

```json
{
  "bank": "demo_bank",
  "extracted_at": "2026-10-08T12:49:00.506204+00:00",
  "period": {
    "from": "2026-05-01",
    "to": "2026-06-30"
  },
  "products": [
    {
      "product_id": "acc-rub",
      "type": "account",
      "name": "Текущий счёт",
      "masked_number": "**** 4567",
      "currency": "RUB",
      "balance": 125430.50,
      "available_balance": 125430.50,
      "linked_account_id": null,
      "requisites": {
        "account_number": "40817810500001234567",
        "bic": "044525999",
        "correspondent_account": "30101810400000000999",
        "bank_name": "АО «Демо-банк»"
      },
      "details": {
        "interest_rate": null,
        "opened_at": "2021-03-15",
        "credit_limit": null,
        "debt": null
      }
    },
    {
      "product_id": "card-debit",
      "type": "card",
      "name": "Дебетовая карта",
      "masked_number": "**** 9012",
      "currency": "RUB",
      "balance": 125430.50,
      "available_balance": 120430.50,
      "linked_account_id": "acc-rub",
      "requisites": null,
      "details": {
        "interest_rate": null,
        "opened_at": "2021-03-20",
        "credit_limit": null,
        "debt": null
      }
    },
    {
      "product_id": "loan",
      "type": "loan",
      "name": "Потребительский кредит",
      "masked_number": "**** 3322",
      "currency": "RUB",
      "balance": null,
      "available_balance": null,
      "linked_account_id": null,
      "requisites": {
        "account_number": "45507810300004443322",
        "bic": "044525999",
        "correspondent_account": "30101810400000000999",
        "bank_name": "АО «Демо-банк»"
      },
      "details": {
        "interest_rate": 21.9,
        "opened_at": "2025-02-01",
        "credit_limit": null,
        "debt": 230000.00
      }
    }
  ],
  "transactions": [
    {
      "transaction_id": "ef5888f8a27676d8-1",
      "id_source": "generated",
      "product_id": "acc-rub",
      "operation_date": "2026-05-03",
      "posting_date": "2026-05-04",
      "amount": -1450.00,
      "currency": "RUB",
      "type": "debit",
      "description": "Покупка по карте •• 9012: Пятёрочка",
      "counterparty": "Пятёрочка",
      "category": "groceries",
      "status": "posted",
      "is_duplicate": false
    },
    {
      "transaction_id": "c-001",
      "id_source": "bank",
      "product_id": "card-debit",
      "operation_date": "2026-05-03",
      "posting_date": "2026-05-04",
      "amount": -1450.00,
      "currency": "RUB",
      "type": "debit",
      "description": "Пятёрочка",
      "counterparty": "Пятёрочка",
      "category": "groceries",
      "status": "posted",
      "is_duplicate": true
    },
    {
      "transaction_id": "u-001",
      "id_source": "bank",
      "product_id": "acc-usd",
      "operation_date": "2026-05-02",
      "posting_date": "2026-05-02",
      "amount": 3000.00,
      "currency": "USD",
      "type": "credit",
      "description": "Входящий перевод SWIFT",
      "counterparty": "ACME Corp.",
      "category": "transfer",
      "status": "posted",
      "is_duplicate": false
    }
  ]
}
```

`extraction_report.json`:

```json
{
  "bank": "demo_bank",
  "period": {
    "from": "2026-05-01",
    "to": "2026-06-30"
  },
  "consent": {
    "granted_at": "2026-10-08T12:48:59.074215+00:00",
    "scope": [
      "Список продуктов: счета, карты, накопительные счета, кредиты",
      "Остатки и доступные суммы",
      "Реквизиты счетов",
      "Ставки, даты открытия, кредитные лимиты и остаток долга",
      "Операции за выбранный период"
    ]
  },
  "products_count": 5,
  "transactions_count": 41,
  "duration_seconds": 1.6,
  "products": [
    {
      "product_id": "acc-rub",
      "masked_number": "**** 4567",
      "status": "complete",
      "extraction_source": "export",
      "transactions_count": 9,
      "reason": null
    },
    {
      "product_id": "card-debit",
      "masked_number": "**** 9012",
      "status": "complete",
      "extraction_source": "server_response",
      "transactions_count": 12,
      "reason": null
    },
    {
      "product_id": "savings",
      "masked_number": "**** 1234",
      "status": "complete",
      "extraction_source": "page",
      "transactions_count": 8,
      "reason": null
    }
  ],
  "warnings": [
    "Продукт card-debit: операция c-001 совпадает с операцией ef5888f8a27676d8-1 продукта acc-rub"
  ],
  "errors": []
}
```

В режиме `load_error` у кредита не загружается карточка, а у дебетовой карты — история. Оба продукта получают
статус `failed`, причина попадает в `errors`, остальные продукты извлекаются как обычно. Строка кредита в отчёте:

```json
{
  "product_id": "loan",
  "masked_number": null,
  "status": "failed",
  "extraction_source": null,
  "transactions_count": 0,
  "reason": "карточка продукта не загружена"
}
```
