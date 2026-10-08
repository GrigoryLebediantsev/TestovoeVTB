import logging
from typing import Any, Literal

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Response
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from shared.browser_base import BrowserBase
from src import domain
from src.usecase import Bank

from . import parsing, selectors
from .config import DemoBankConfig

log = logging.getLogger(__name__)

MILLISECONDS_IN_SECOND = 1000
# Защита от бесконечной подгрузки, если сервер всё время отвечает «есть ещё»
MAX_HISTORY_PORTIONS = 200
SCROLL_DISTANCE_PIXELS = 100_000
# Достаточно готовой разметки: нужные элементы затем ждём явно
NAVIGATION_WAIT_UNTIL: Literal['domcontentloaded'] = 'domcontentloaded'

# Пары «подпись → значение и ссылка» со страницы продукта
READ_FIELD_ROWS_SCRIPT = """rows => rows.map(row => ({
    label: row.querySelector('dt')?.innerText.trim() ?? '',
    text: row.querySelector('dd')?.innerText.trim() ?? '',
    link: row.querySelector('dd a')?.getAttribute('href') ?? null,
}))"""
READ_LINKS_SCRIPT = 'links => links.map(link => link.getAttribute("href"))'
# Ячейки строк таблицы операций; идентификатор банка — в атрибуте строки, если банк его показывает
READ_TRANSACTION_ROWS_SCRIPT = """rows => rows.map(row => {
    const cell = name => row.querySelector('.transaction-' + name)?.innerText.trim() ?? '';
    return {
        bank_id: row.dataset.transactionId ?? null,
        operation_date: cell('date'),
        posting_date: cell('posting-date'),
        description: cell('description'),
        counterparty: cell('counterparty'),
        category: cell('category'),
        status: cell('status'),
        amount: cell('amount'),
    };
})"""


class DemoBank(Bank):
    display_name = 'Демо-банк'

    def __init__(self, config: DemoBankConfig, browser: BrowserBase) -> None:
        self.config = config
        self.browser = browser

    async def wait_for_login(self) -> None:
        await self._open(selectors.LOGIN_PATH)
        log.info('Waiting for client login')
        try:
            await self.browser.page.locator(selectors.PRODUCTS_LIST).wait_for(
                timeout=self.config.LOGIN_TIMEOUT_SECONDS * MILLISECONDS_IN_SECOND
            )
        except PlaywrightTimeoutError as error:
            raise domain.LoginTimeout() from error

    async def get_products(self) -> list[domain.Product]:
        page = self.browser.page
        try:
            await self._open(selectors.PRODUCTS_PATH)
            await page.locator(selectors.PRODUCTS_LIST).wait_for(timeout=self._action_timeout_ms())
            links: list[str] = await page.locator(selectors.PRODUCT_LINK).evaluate_all(READ_LINKS_SCRIPT)
        except PlaywrightError as error:
            log.error('Products list not loaded: %s', type(error).__name__)
            raise domain.ProductsNotLoaded() from error

        product_ids = [parsing.parse_product_id(link) for link in links]
        log.info('Products found', extra={'product_ids': product_ids})
        return [await self._get_product(product_id) for product_id in product_ids]

    async def get_transactions(self, product_id: str, period: domain.Period) -> domain.TransactionHistory:
        """Сначала ответы сервера, которые получает сама страница, иначе — разбор страницы (ADR 0002)."""
        page = self.browser.page
        history_responses: list[Response] = []

        def remember_history_response(response: Response) -> None:
            if parsing.is_history_response_url(response.url, product_id, period=None):
                history_responses.append(response)

        # Своих запросов к серверу не делаем: только слушаем ответы на запросы страницы
        page.on('response', remember_history_response)
        try:
            await self._open(f'{selectors.PRODUCTS_PATH}/{product_id}')
            await page.locator(selectors.TRANSACTIONS_SECTION).wait_for(timeout=self._action_timeout_ms())
            is_filter_applied = await self._apply_period_filter(period)
            await page.locator(selectors.TRANSACTIONS_READY).wait_for(timeout=self._action_timeout_ms())

            # Без фильтра годится любой ответ, с фильтром — только за запрошенный период
            filter_period = period if is_filter_applied else None
            period_responses = [
                response
                for response in history_responses
                if parsing.is_history_response_url(response.url, product_id, period=filter_period)
            ]
            if period_responses:
                history = await self._read_server_history(product_id, filter_period, period_responses[-1])
            else:
                history = await self._read_page_history(product_id)
        finally:
            page.remove_listener('response', remember_history_response)

        if not is_filter_applied:
            history.warnings.append(f'Продукт {product_id}: фильтр периода в кабинете не найден')
        return history

    async def _read_server_history(
        self, product_id: str, filter_period: domain.Period | None, first_response: Response
    ) -> domain.TransactionHistory:
        """Собирает все порции истории: подгружает следующие так же, как клиент, и читает ответы сервера."""
        page = self.browser.page
        portion = parsing.parse_server_portion(await first_response.json())
        items = list(portion.items)
        warnings = []
        portions_count = 1
        while portion.has_more:
            if portions_count >= MAX_HISTORY_PORTIONS or not await self._has_next_portion_control():
                warnings.append(f'Продукт {product_id}: история загружена не полностью')
                break
            async with page.expect_response(
                lambda response: parsing.is_history_response_url(response.url, product_id, period=filter_period),
                timeout=self._action_timeout_ms(),
            ) as response_info:
                await self._request_next_portion()
            next_response = await response_info.value
            portion = parsing.parse_server_portion(await next_response.json())
            items.extend(portion.items)
            portions_count += 1

        log.info('History collected', extra={'product_id': product_id, 'portions_count': portions_count})
        return domain.TransactionHistory(
            transactions=parsing.parse_server_transactions(product_id, items),
            source=domain.ExtractionSource.SERVER_RESPONSE,
            warnings=warnings,
        )

    async def _has_next_portion_control(self) -> bool:
        page = self.browser.page
        controls_count = await page.locator(selectors.SHOW_MORE_BUTTON).count()
        controls_count += await page.locator(selectors.SCROLL_SENTINEL).count()
        return controls_count > 0

    async def _request_next_portion(self) -> None:
        """Действие клиента для следующей порции: кнопка «Показать ещё» или прокрутка вниз."""
        page = self.browser.page
        if await page.locator(selectors.SHOW_MORE_BUTTON).count() > 0:
            await page.locator(selectors.SHOW_MORE_BUTTON).click()
        else:
            await page.mouse.wheel(0, SCROLL_DISTANCE_PIXELS)

    async def _read_page_history(self, product_id: str) -> domain.TransactionHistory:
        # Ключи словарей совпадают с полями TransactionRow: скрипт возвращает их тем же списком
        rows: list[dict[str, Any]] = await self.browser.page.locator(selectors.TRANSACTION_ROW).evaluate_all(
            READ_TRANSACTION_ROWS_SCRIPT
        )
        transaction_rows = [parsing.TransactionRow(**row) for row in rows]
        return domain.TransactionHistory(
            transactions=parsing.parse_transactions(product_id, transaction_rows),
            source=domain.ExtractionSource.PAGE,
        )

    async def _apply_period_filter(self, period: domain.Period) -> bool:
        """Выставляет период в фильтре кабинета и ждёт перезагрузки истории; False — фильтра на странице нет."""
        page = self.browser.page
        if await page.locator(selectors.PERIOD_FILTER_FORM).count() == 0:
            log.warning('Period filter not found, history loaded without it')
            return False
        await page.locator(selectors.PERIOD_FILTER_FROM).fill(period.date_from.isoformat())
        await page.locator(selectors.PERIOD_FILTER_TO).fill(period.date_to.isoformat())
        async with page.expect_navigation(timeout=self._action_timeout_ms(), wait_until=NAVIGATION_WAIT_UNTIL):
            await page.locator(selectors.PERIOD_FILTER_SUBMIT).click()
        await page.locator(selectors.TRANSACTIONS_SECTION).wait_for(timeout=self._action_timeout_ms())
        return True

    async def _get_product(self, product_id: str) -> domain.Product:
        page = self.browser.page
        await self._open(f'{selectors.PRODUCTS_PATH}/{product_id}')
        await page.locator(selectors.PRODUCT_TITLE).wait_for(timeout=self._action_timeout_ms())
        name = await page.locator(selectors.PRODUCT_TITLE).inner_text()
        rows: list[dict[str, str | None]] = await page.locator(selectors.PRODUCT_FIELD_ROW).evaluate_all(
            READ_FIELD_ROWS_SCRIPT
        )
        fields = {
            str(row['label']): parsing.ProductField(text=str(row['text']), link=row['link'])
            for row in rows
            if row['label']
        }
        return parsing.parse_product(product_id, name, fields)

    async def _open(self, path: str) -> None:
        url = f'{self.config.BASE_URL.rstrip("/")}{path}'
        await self.browser.page.goto(url, timeout=self._action_timeout_ms(), wait_until=NAVIGATION_WAIT_UNTIL)

    def _action_timeout_ms(self) -> float:
        return self.config.ACTION_TIMEOUT_SECONDS * MILLISECONDS_IN_SECOND
