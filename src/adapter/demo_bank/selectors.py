"""Все селекторы и подписи кабинета демо-банка в одном месте: при изменении разметки правится только этот файл."""

LOGIN_PATH = '/login'
PRODUCTS_PATH = '/products'

# Признак входа и список продуктов
PRODUCTS_LIST = '[data-testid="products-list"]'
PRODUCT_LINK = '[data-testid="products-list"] a.product-link'

# Страница продукта
PRODUCT_TITLE = '.product-title'
PRODUCT_FIELD_ROW = '.product-fields .product-field'

# Подписи полей на странице продукта
FIELD_TYPE = 'Тип'
FIELD_CARD_NUMBER = 'Номер карты'
FIELD_ACCOUNT_NUMBER = 'Номер счёта'
FIELD_BALANCE = 'Баланс'
FIELD_AVAILABLE_BALANCE = 'Доступно'
FIELD_CREDIT_LIMIT = 'Кредитный лимит'
FIELD_DEBT = 'Остаток долга'
FIELD_INTEREST_RATE = 'Ставка'
FIELD_OPENED_AT = 'Дата открытия'
FIELD_LINKED_ACCOUNT = 'Привязанный счёт'
FIELD_BIC = 'БИК'
FIELD_CORRESPONDENT_ACCOUNT = 'Корр. счёт'
FIELD_BANK_NAME = 'Банк получателя'

# История операций на странице продукта
PERIOD_FILTER_FORM = '.period-filter'
PERIOD_FILTER_FROM = '.period-filter input[name="from"]'
PERIOD_FILTER_TO = '.period-filter input[name="to"]'
PERIOD_FILTER_SUBMIT = '.period-filter button[type="submit"]'
TRANSACTIONS_SECTION = '[data-testid="transactions"]'
TRANSACTION_ROW = '[data-testid="transactions"] tr.transaction'
TRANSACTIONS_READY = '[data-testid="transactions"][data-state="ready"]'
SHOW_MORE_BUTTON = '[data-testid="transactions"] button.show-more'
SCROLL_SENTINEL = '[data-testid="transactions"] .load-more-sentinel'

# Запросы страницы к серверу банка за порциями истории
HISTORY_API_PATH = '/api/products/{product_id}/transactions'
HISTORY_API_FROM_PARAM = 'from'
HISTORY_API_TO_PARAM = 'to'

# Экспорт истории в CSV: ссылка на странице продукта и колонки файла
EXPORT_LINK = '[data-testid="transactions"] a.export-csv'
EXPORT_DELIMITER = ';'
EXPORT_COLUMN_OPERATION_DATE = 'Дата операции'
EXPORT_COLUMN_POSTING_DATE = 'Дата проведения'
EXPORT_COLUMN_DESCRIPTION = 'Описание'
EXPORT_COLUMN_COUNTERPARTY = 'Контрагент'
EXPORT_COLUMN_CATEGORY = 'Категория'
EXPORT_COLUMN_STATUS = 'Статус'
EXPORT_COLUMN_AMOUNT = 'Сумма'
EXPORT_COLUMN_CURRENCY = 'Валюта'

# История на страницах с номерами
NEXT_PAGE_LINK = '[data-testid="transactions"] .pagination a.page-next'
