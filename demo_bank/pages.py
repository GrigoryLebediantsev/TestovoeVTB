"""HTML-страницы кабинета демо-банка."""

import datetime
import json
from decimal import Decimal
from html import escape
from urllib.parse import urlencode

from .data import (
    BANK_BIC,
    BANK_CORRESPONDENT_ACCOUNT,
    BANK_NAME,
    CLIENT_FULL_NAME,
    PRODUCTS,
    PRODUCTS_BY_ID,
    DemoProduct,
    DemoTransaction,
    HistoryLoading,
    filter_by_posting_date,
)
from .formats import CURRENCY_SYMBOLS, MONTH_NAMES_GENITIVE
from .view import CabinetView

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
.period-filter { display: flex; gap: 8px; align-items: end; }
.period-filter input { width: auto; }
.transactions-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.transactions-table td, .transactions-table th { border-bottom: 1px solid #ddd; padding: 6px 4px; text-align: left; }
.scroll-spacer { height: 100vh; }
.pagination { display: flex; gap: 8px; margin-top: 12px; }
"""


EMPTY_CELL = '—'


def format_percent(value: Decimal) -> str:
    return f'{value}'.replace('.', ',') + ' %'


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


def products_page(view: CabinetView) -> str:
    items = ''.join(_product_card(product, view) for product in PRODUCTS)
    return layout(
        'Мои продукты',
        f'<h1>Мои продукты</h1><ul class="products-list" data-testid="products-list">{items}</ul>',
        signed_in=True,
    )


def _product_card(product: DemoProduct, view: CabinetView) -> str:
    number = product.card_number or product.account_number or ''
    amount = product.balance if product.balance is not None else product.debt
    amount_text = view.value_format.money(amount, product.currency) if amount is not None else ''
    return f"""<li class="product-card">
  <a class="product-link" href="/products/{escape(product.product_id)}">{escape(product.name)}</a>
  <span class="product-number">{escape(short_number(number))}</span>
  <span class="product-amount">{escape(amount_text)}</span>
</li>"""


def product_page(
    product: DemoProduct,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    view: CabinetView,
    page_number: int = 1,
) -> str:
    value_format = view.value_format
    fields: list[tuple[str, str]] = [('Тип', escape(product.type_label))]
    if product.card_number:
        fields.append(('Номер карты', escape(format_card_number(product.card_number))))
    if product.account_number:
        fields.append(('Номер счёта', escape(product.account_number)))
    if product.balance is not None:
        fields.append(('Баланс', escape(value_format.money(product.balance, product.currency))))
    if product.available_balance is not None:
        fields.append(('Доступно', escape(value_format.money(product.available_balance, product.currency))))
    if product.credit_limit is not None:
        fields.append(('Кредитный лимит', escape(value_format.money(product.credit_limit, product.currency))))
    if product.debt is not None:
        fields.append(('Остаток долга', escape(value_format.money(product.debt, product.currency))))
    if product.interest_rate is not None:
        fields.append(('Ставка', escape(format_percent(product.interest_rate))))
    fields.append(('Дата открытия', escape(value_format.date(product.opened_at))))
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
</section>
{_transactions_section(product, date_from, date_to, view, page_number)}""",
        signed_in=True,
    )


TRANSACTIONS_TABLE_HEAD = """<thead><tr><th>Дата</th><th>Проведена</th><th>Описание</th><th>Контрагент</th>
<th>Категория</th><th>Статус</th><th>Сумма</th></tr></thead>"""
EMPTY_HISTORY = '<p class="transactions-empty">Операций нет</p>'
HISTORY_PAGE_SIZE = 4

# Подгрузка истории порциями: страница сама запрашивает сервер и дописывает строки в таблицу.
# Даты, суммы и классы таблицы — такие же, как в остальном кабинете в текущем режиме.
PORTION_LOADER_SCRIPT = """<script>
(() => {
  const section = document.querySelector('[data-testid="transactions"]');
  const tableBody = section.querySelector('tbody');
  const pageQuery = new URLSearchParams(location.search);
  const currencySymbols = __CURRENCY_SYMBOLS__;
  const monthNames = __MONTH_NAMES__;
  const isChangedFormat = __IS_CHANGED_FORMAT__;
  const rowClass = __ROW_CLASS__;
  const cellClassPrefix = __CELL_CLASS_PREFIX__;
  const showMoreSelector = '.' + __SHOW_MORE_CLASS__;
  const statusLabels = {POSTED: 'Проведена', PENDING: 'В обработке', DECLINED: 'Отклонена'};
  let offset = 0;
  let hasMore = true;
  let isLoading = false;

  const formatDate = value => {
    if (!value) return '—';
    const [year, month, day] = value.split('-');
    if (isChangedFormat) return `${Number(day)} ${monthNames[Number(month) - 1]} ${year}`;
    return `${day}.${month}.${year}`;
  };
  const formatMoney = (amount, currency) => {
    const number = Number(amount);
    if (isChangedFormat) return `${number.toFixed(2)} ${currency}`;
    const sign = number < 0 ? '−' : number > 0 ? '+' : '';
    const [integerPart, fractionPart] = Math.abs(number).toFixed(2).split('.');
    const grouped = integerPart.replace(/\\B(?=(\\d{3})+(?!\\d))/g, '\u00a0');
    return `${sign}${grouped},${fractionPart}\u00a0${currencySymbols[currency]}`;
  };
  const addCell = (row, name, text) => {
    const cell = row.insertCell();
    cell.className = cellClassPrefix + name;
    cell.textContent = text;
  };
  const addRow = item => {
    const row = tableBody.insertRow();
    row.className = rowClass;
    if (item.id) row.dataset.transactionId = item.id;
    addCell(row, 'date', formatDate(item.operationDate));
    addCell(row, 'posting-date', formatDate(item.postingDate));
    addCell(row, 'description', item.description);
    addCell(row, 'counterparty', item.counterparty || '—');
    addCell(row, 'category', item.category);
    addCell(row, 'status', statusLabels[item.status] || item.status);
    addCell(row, 'amount', formatMoney(item.amount, item.currency));
  };

  async function loadPortion() {
    if (isLoading || !hasMore) return;
    isLoading = true;
    const query = new URLSearchParams({offset: String(offset)});
    for (const name of ['from', 'to']) {
      if (pageQuery.get(name)) query.set(name, pageQuery.get(name));
    }
    const response = await fetch(`/api/products/${section.dataset.productId}/transactions?${query}`);
    if (!response.ok) {
      section.dataset.state = 'error';
      section.querySelector('.transactions-status').textContent = 'Не удалось загрузить операции';
      isLoading = false;
      return;
    }
    const portion = await response.json();
    portion.items.forEach(addRow);
    offset += portion.items.length;
    hasMore = portion.hasMore;
    if (offset === 0) section.querySelector('.transactions-status').innerHTML = '__EMPTY_HISTORY__';
    if (!hasMore) {
      section.querySelectorAll(`${showMoreSelector}, .load-more-sentinel`).forEach(item => item.remove());
    }
    section.dataset.state = 'ready';
    isLoading = false;
  }

  section.querySelector(showMoreSelector)?.addEventListener('click', loadPortion);
  const sentinel = section.querySelector('.load-more-sentinel');
  if (sentinel) {
    window.addEventListener('scroll', () => {
      if (sentinel.isConnected && sentinel.getBoundingClientRect().top <= window.innerHeight) loadPortion();
    });
  }
  loadPortion();
})();
</script>""".replace('__EMPTY_HISTORY__', EMPTY_HISTORY)


def _portion_loader_script(view: CabinetView) -> str:
    return (
        PORTION_LOADER_SCRIPT.replace('__CURRENCY_SYMBOLS__', json.dumps(CURRENCY_SYMBOLS))
        .replace('__MONTH_NAMES__', json.dumps(MONTH_NAMES_GENITIVE))
        .replace('__IS_CHANGED_FORMAT__', json.dumps(view.value_format.is_changed))
        .replace('__ROW_CLASS__', json.dumps(view.table_markup.row_class))
        .replace('__CELL_CLASS_PREFIX__', json.dumps(view.table_markup.cell_class_prefix))
        .replace('__SHOW_MORE_CLASS__', json.dumps(view.table_markup.show_more_class))
    )


def _transactions_section(
    product: DemoProduct,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    view: CabinetView,
    page_number: int,
) -> str:
    if product.history_loading == HistoryLoading.PAGE:
        history = _render_page_history(product, date_from, date_to, view)
        state = 'ready'
    elif product.history_loading == HistoryLoading.NUMBERED_PAGES:
        history = _render_numbered_history(product, date_from, date_to, view, page_number)
        state = 'ready'
    else:
        history = _render_portion_history(product.history_loading, view)
        state = 'loading'
    from_value = date_from.isoformat() if date_from else ''
    to_value = date_to.isoformat() if date_to else ''
    export_link = ''
    if product.has_export:
        export_query = urlencode({'from': from_value, 'to': to_value})
        export_link = (
            f'<p><a class="export-csv" href="/products/{escape(product.product_id)}/export.csv?{export_query}">'
            'Скачать выписку CSV</a></p>'
        )
    return f"""<section class="transactions" data-testid="transactions" data-state="{state}"
  data-product-id="{escape(product.product_id)}">
<h2>Операции</h2>
<form class="period-filter" method="get">
  <label>С <input name="from" type="date" value="{from_value}"></label>
  <label>По <input name="to" type="date" value="{to_value}"></label>
  <button type="submit">Показать</button>
</form>
{export_link}
{history}
</section>"""


def _render_page_history(
    product: DemoProduct, date_from: datetime.date | None, date_to: datetime.date | None, view: CabinetView
) -> str:
    transactions = filter_by_posting_date(product.transactions, date_from, date_to)
    if not transactions:
        return EMPTY_HISTORY
    rows = ''.join(_transaction_row(transaction, product.currency, view) for transaction in transactions)
    return f'<table class="transactions-table">{TRANSACTIONS_TABLE_HEAD}<tbody>{rows}</tbody></table>'


def _render_numbered_history(
    product: DemoProduct,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    view: CabinetView,
    page_number: int,
) -> str:
    """История по страницам; ссылки страниц сохраняют фильтр периода."""
    transactions = filter_by_posting_date(product.transactions, date_from, date_to)
    if not transactions:
        return EMPTY_HISTORY
    pages_count = (len(transactions) + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE
    current_page = min(max(page_number, 1), pages_count)
    start = (current_page - 1) * HISTORY_PAGE_SIZE
    page_transactions = transactions[start : start + HISTORY_PAGE_SIZE]
    rows = ''.join(_transaction_row(transaction, product.currency, view) for transaction in page_transactions)

    def page_href(number: int) -> str:
        query = {'from': date_from.isoformat() if date_from else '', 'to': date_to.isoformat() if date_to else ''}
        return f'?{urlencode(query | {"page": str(number)})}'

    page_items = []
    for number in range(1, pages_count + 1):
        if number == current_page:
            page_items.append(f'<span class="page-current">{number}</span>')
        else:
            page_items.append(f'<a class="page-link" href="{page_href(number)}">{number}</a>')
    if current_page < pages_count:
        page_items.append(f'<a class="page-next" href="{page_href(current_page + 1)}">Следующая →</a>')
    return f"""<table class="transactions-table">{TRANSACTIONS_TABLE_HEAD}<tbody>{rows}</tbody></table>
<nav class="pagination">{''.join(page_items)}</nav>"""


def _render_portion_history(history_loading: HistoryLoading, view: CabinetView) -> str:
    if history_loading == HistoryLoading.SHOW_MORE:
        show_more_class = escape(view.table_markup.show_more_class)
        more_control = f'<button type="button" class="{show_more_class}">Показать ещё</button>'
    else:
        more_control = '<div class="scroll-spacer"></div><div class="load-more-sentinel"></div>'
    return f"""<table class="transactions-table">{TRANSACTIONS_TABLE_HEAD}<tbody></tbody></table>
<div class="transactions-status"></div>
{more_control}
{_portion_loader_script(view)}"""


def _transaction_row(transaction: DemoTransaction, currency: str, view: CabinetView) -> str:
    id_attribute = f' data-transaction-id="{escape(transaction.bank_id)}"' if transaction.bank_id else ''
    value_format = view.value_format
    posting_date = value_format.date(transaction.posting_date) if transaction.posting_date else EMPTY_CELL
    row_class = escape(view.table_markup.row_class)
    cell_class = escape(view.table_markup.cell_class_prefix)
    return f"""<tr class="{row_class}"{id_attribute}>
  <td class="{cell_class}date">{value_format.date(transaction.operation_date)}</td>
  <td class="{cell_class}posting-date">{posting_date}</td>
  <td class="{cell_class}description">{escape(transaction.description)}</td>
  <td class="{cell_class}counterparty">{escape(transaction.counterparty or EMPTY_CELL)}</td>
  <td class="{cell_class}category">{escape(transaction.category)}</td>
  <td class="{cell_class}status">{escape(value_format.status(transaction))}</td>
  <td class="{cell_class}amount">{escape(value_format.money(transaction.amount, currency, show_plus=True))}</td>
</tr>"""
