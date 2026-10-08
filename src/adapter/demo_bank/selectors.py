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
