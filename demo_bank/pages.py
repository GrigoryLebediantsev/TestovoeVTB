"""HTML-страницы кабинета демо-банка."""

import datetime
from decimal import Decimal
from html import escape

from .data import (
    BANK_BIC,
    BANK_CORRESPONDENT_ACCOUNT,
    BANK_NAME,
    CLIENT_FULL_NAME,
    PRODUCTS,
    PRODUCTS_BY_ID,
    DemoProduct,
)

CURRENCY_SYMBOLS = {'RUB': '₽', 'USD': '$', 'EUR': '€'}

STYLE = """
body { font-family: sans-serif; margin: 0; background: #f4f5f7; color: #1d1d1f; }
header { background: #1f4fd1; color: #fff; padding: 12px 24px; display: flex; justify-content: space-between; }
main { max-width: 720px; margin: 24px auto; background: #fff; padding: 24px; border-radius: 8px; }
label { display: block; margin: 12px 0 4px; }
input { padding: 8px; width: 100%; box-sizing: border-box; }
button { margin-top: 16px; padding: 8px 16px; }
.error { color: #c00; }
.products-list { list-style: none; padding: 0; }
.product-card { border-bottom: 1px solid #ddd; padding: 12px 0; }
.product-fields div { display: flex; gap: 16px; padding: 4px 0; }
.product-fields dt { width: 200px; color: #666; }
.product-fields dd { margin: 0; }
"""


def format_money(amount: Decimal, currency: str) -> str:
    """125430.50, RUB → '125 430,50 ₽' (пробел-разделитель тысяч — неразрывный)."""
    sign = '−' if amount < 0 else ''
    integer_part, fraction_part = f'{abs(amount):.2f}'.split('.')
    grouped = f'{int(integer_part):,}'.replace(',', ' ')
    return f'{sign}{grouped},{fraction_part} {CURRENCY_SYMBOLS[currency]}'


def format_percent(value: Decimal) -> str:
    return f'{value}'.replace('.', ',') + ' %'


def format_date(value: datetime.date) -> str:
    return value.strftime('%d.%m.%Y')


def short_number(number: str) -> str:
    return f'•• {number[-4:]}'


def format_card_number(number: str) -> str:
    return ' '.join(number[index : index + 4] for index in range(0, len(number), 4))


def layout(title: str, body: str, signed_in: bool = False) -> str:
    user_block = f'<span class="client-name">{escape(CLIENT_FULL_NAME)}</span>' if signed_in else ''
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>{escape(title)} — Демо-банк</title><style>{STYLE}</style></head>
<body>
<header><strong>Демо-банк</strong>{user_block}</header>
<main>{body}</main>
</body>
</html>"""


def login_page(error: str | None = None) -> str:
    error_block = f'<p class="error">{escape(error)}</p>' if error else ''
    return layout(
        'Вход',
        f"""<h1>Вход в личный кабинет</h1>
{error_block}
<form method="post" action="/login">
  <label for="login">Логин</label><input id="login" name="login" autocomplete="username">
  <label for="password">Пароль</label><input id="password" name="password" type="password">
  <button type="submit">Войти</button>
</form>""",
    )


def one_time_code_page(error: str | None = None) -> str:
    error_block = f'<p class="error">{escape(error)}</p>' if error else ''
    return layout(
        'Подтверждение входа',
        f"""<h1>Подтверждение входа</h1>
<p>Мы отправили код в СМС.</p>
{error_block}
<form method="post" action="/otp">
  <label for="code">Код из СМС</label><input id="code" name="code" autocomplete="one-time-code">
  <button type="submit">Подтвердить</button>
</form>""",
    )


def products_page() -> str:
    items = ''.join(_product_card(product) for product in PRODUCTS)
    return layout(
        'Мои продукты',
        f'<h1>Мои продукты</h1><ul class="products-list" data-testid="products-list">{items}</ul>',
        signed_in=True,
    )


def _product_card(product: DemoProduct) -> str:
    number = product.card_number or product.account_number or ''
    amount = product.balance if product.balance is not None else product.debt
    amount_text = format_money(amount, product.currency) if amount is not None else ''
    return f"""<li class="product-card">
  <a class="product-link" href="/products/{escape(product.product_id)}">{escape(product.name)}</a>
  <span class="product-number">{escape(short_number(number))}</span>
  <span class="product-amount">{escape(amount_text)}</span>
</li>"""


def product_page(product: DemoProduct) -> str:
    fields: list[tuple[str, str]] = [('Тип', escape(product.type_label))]
    if product.card_number:
        fields.append(('Номер карты', escape(format_card_number(product.card_number))))
    if product.account_number:
        fields.append(('Номер счёта', escape(product.account_number)))
    if product.balance is not None:
        fields.append(('Баланс', escape(format_money(product.balance, product.currency))))
    if product.available_balance is not None:
        fields.append(('Доступно', escape(format_money(product.available_balance, product.currency))))
    if product.credit_limit is not None:
        fields.append(('Кредитный лимит', escape(format_money(product.credit_limit, product.currency))))
    if product.debt is not None:
        fields.append(('Остаток долга', escape(format_money(product.debt, product.currency))))
    if product.interest_rate is not None:
        fields.append(('Ставка', escape(format_percent(product.interest_rate))))
    fields.append(('Дата открытия', escape(format_date(product.opened_at))))
    if product.linked_product_id:
        linked = PRODUCTS_BY_ID[product.linked_product_id]
        link_text = f'{linked.name} {short_number(linked.account_number or "")}'
        fields.append(('Привязанный счёт', f'<a href="/products/{escape(linked.product_id)}">{escape(link_text)}</a>'))
    if product.account_number:
        fields.append(('БИК', BANK_BIC))
        fields.append(('Корр. счёт', BANK_CORRESPONDENT_ACCOUNT))
        fields.append(('Банк получателя', escape(BANK_NAME)))

    rows = ''.join(f'<div class="product-field"><dt>{label}</dt><dd>{value}</dd></div>' for label, value in fields)
    return layout(
        product.name,
        f"""<p><a href="/products">← Все продукты</a></p>
<section class="product" data-product-id="{escape(product.product_id)}">
  <h1 class="product-title">{escape(product.name)}</h1>
  <dl class="product-fields">{rows}</dl>
</section>""",
        signed_in=True,
    )
