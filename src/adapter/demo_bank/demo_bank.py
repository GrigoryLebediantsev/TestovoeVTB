import functools
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
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
MAX_HISTORY_PAGES = 200
SCROLL_DISTANCE_PIXELS = 100_000
# Достаточно готовой разметки: нужные элементы затем ждём явно
NAVIGATION_WAIT_UNTIL: Literal['domcontentloaded'] = 'domcontentloaded'


class BankPageError(Exception):
    """Кабинет ответил на открытие страницы ошибкой сервера."""


# Технические сбои, после которых чтение стоит повторить: таймаут, ошибка кабинета.
# Незнакомый формат данных (ValueError) не повторяем: повтор его не исправит
RETRYABLE_ERRORS = (PlaywrightError, OSError, BankPageError, domain.TransactionsNotLoaded)
HISTORY_INCOMPLETE_REASON = 'история загружена не полностью'
HTTP_SERVER_ERROR = 500

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

    async def get_product_ids(self) -> list[str]:
        try:
            links, _ = await self._with_retries(self._read_product_links, 'Products list')
            product_ids = [parsing.parse_product_id(link) for link in links]
        except (*RETRYABLE_ERRORS, ValueError) as error:
            log.error('Products list not loaded: %s', type(error).__name__)
            raise domain.ProductsNotLoaded() from error
        log.info('Products found', extra={'product_ids': product_ids})
        return product_ids

    async def get_product(self, product_id: str) -> domain.Product:
        try:
            product, _ = await self._with_retries(
                functools.partial(self._read_product, product_id), 'Product page', product_id
            )
        except (*RETRYABLE_ERRORS, ValueError) as error:
            log.error('Product page not loaded: %s', type(error).__name__, extra={'product_id': product_id})
            raise domain.ProductDetailsNotLoaded() from error
        return product

    async def get_transactions(self, product_id: str, period: domain.Period) -> domain.TransactionHistory:
        """Технические сбои повторяются RETRY_COUNT раз, затем — domain.TransactionsNotLoaded.

        Незнакомая разметка или формат — сразу domain.TransactionsLayoutNotRecognized
        или domain.TransactionsFormatNotRecognized: повтор их не исправит.
        """
        try:
            history, retries_count = await self._with_retries(
                functools.partial(self._read_history, product_id, period), 'History', product_id
            )
        except ValueError as error:
            log.error('History format not recognized: %s', type(error).__name__, extra={'product_id': product_id})
            raise domain.TransactionsFormatNotRecognized() from error
        except RETRYABLE_ERRORS as error:
            raise domain.TransactionsNotLoaded() from error
        if retries_count > 0:
            history.warnings.append(f'Продукт {product_id}: история загружена после повторной попытки')
        return history

    async def _with_retries[T](
        self, read: Callable[[], Awaitable[T]], action_name: str, product_id: str | None = None
    ) -> tuple[T, int]:
        """Повторяет чтение после технического сбоя; возвращает результат и число повторов.

        Последняя ошибка, когда повторы исчерпаны, пробрасывается как есть.
        """
        for retries_count in range(self.config.RETRY_COUNT):
            try:
                return await read(), retries_count
            except RETRYABLE_ERRORS as error:
                log.warning(
                    '%s attempt %s failed, retrying: %s',
                    action_name,
                    retries_count + 1,
                    type(error).__name__,
                    extra={'product_id': product_id},
                )
        return await read(), self.config.RETRY_COUNT

    async def _read_product_links(self) -> list[str]:
        page = self.browser.page
        await self._open(selectors.PRODUCTS_PATH)
        await page.locator(selectors.PRODUCTS_LIST).wait_for(timeout=self._action_timeout_ms())
        links: list[str] = await page.locator(selectors.PRODUCT_LINK).evaluate_all(READ_LINKS_SCRIPT)
        return links

    async def _read_history(self, product_id: str, period: domain.Period) -> domain.TransactionHistory:
        """Способы по порядку: экспорт CSV → ответы сервера на запросы страницы → разбор страницы (ADR 0002)."""
        page = self.browser.page
        history_responses: list[Response] = []

        def remember_history_response(response: Response) -> None:
            # Ответ с ошибкой сервера не годится: о сбое кабинет сообщит на странице
            if response.ok and parsing.is_history_response_url(response.url, product_id, period=None):
                history_responses.append(response)

        # Своих запросов к серверу не делаем: только слушаем ответы на запросы страницы
        page.on('response', remember_history_response)
        warnings = []
        try:
            is_filter_applied = await self._open_product_history(product_id, period)

            history = None
            if await page.locator(selectors.EXPORT_LINK).count() > 0:
                try:
                    history = await self._read_export_history(product_id)
                except (PlaywrightError, ValueError, OSError) as error:
                    log.warning(
                        'Export failed, trying next source: %s', type(error).__name__, extra={'product_id': product_id}
                    )
                    warnings.append(f'Продукт {product_id}: экспорт не удался, использован другой способ')
                    # Вместо файла кабинет мог открыть страницу ошибки: возвращаемся к истории продукта
                    is_filter_applied = await self._open_product_history(product_id, period)

            if history is None:
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
            warnings.append(f'Продукт {product_id}: фильтр периода в кабинете не найден')
        history.warnings.extend(warnings)
        return history

    async def _open_product_history(self, product_id: str, period: domain.Period) -> bool:
        """Открывает историю продукта с фильтром периода; False — фильтра в кабинете нет.

        Если кабинет показал ошибку загрузки истории — domain.TransactionsNotLoaded.
        """
        page = self.browser.page
        await self._open(f'{selectors.PRODUCTS_PATH}/{product_id}')
        await page.locator(selectors.TRANSACTIONS_SECTION).wait_for(timeout=self._action_timeout_ms())
        is_filter_applied = await self._apply_period_filter(period)
        await page.locator(selectors.TRANSACTIONS_SETTLED).wait_for(timeout=self._action_timeout_ms())
        if await page.locator(selectors.TRANSACTIONS_FAILED).count() > 0:
            log.warning('Bank page shows history load error', extra={'product_id': product_id})
            raise domain.TransactionsNotLoaded()
        return is_filter_applied

    async def _read_export_history(self, product_id: str) -> domain.TransactionHistory:
        """Скачивает экспорт кнопкой кабинета, как клиент, читает файл и сразу удаляет его с диска."""
        page = self.browser.page
        async with page.expect_download(timeout=self._action_timeout_ms()) as download_info:
            await page.locator(selectors.EXPORT_LINK).click()
        download = await download_info.value
        try:
            content = Path(await download.path()).read_bytes()
        finally:
            await download.delete()

        history = parsing.parse_export_transactions(product_id, content)
        log.info('Export read', extra={'product_id': product_id, 'transactions_count': len(history.transactions)})
        return history

    async def _read_server_history(
        self, product_id: str, filter_period: domain.Period | None, first_response: Response
    ) -> domain.TransactionHistory:
        """Собирает все порции истории: подгружает следующие так же, как клиент, и читает ответы сервера."""
        page = self.browser.page
        portion = parsing.parse_server_portion(await first_response.json())
        items = list(portion.items)
        incomplete_reason = None
        portions_count = 1
        while portion.has_more:
            if portions_count >= MAX_HISTORY_PORTIONS or not await self._has_next_portion_control():
                log.warning('Next history portion control not found', extra={'product_id': product_id})
                incomplete_reason = HISTORY_INCOMPLETE_REASON
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
        history = parsing.parse_server_transactions(product_id, items)
        history.incomplete_reason = incomplete_reason
        return history

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
        """Читает таблицу операций; если история разбита на страницы — переходит по ним, как клиент."""
        page = self.browser.page
        rows: list[dict[str, Any]] = []
        incomplete_reason = None
        pages_count = 1
        while True:
            # Ключи словарей совпадают с полями TransactionRow: скрипт возвращает их тем же списком
            rows.extend(await page.locator(selectors.TRANSACTION_ROW).evaluate_all(READ_TRANSACTION_ROWS_SCRIPT))
            if await page.locator(selectors.NEXT_PAGE_LINK).count() == 0:
                break
            if pages_count >= MAX_HISTORY_PAGES:
                incomplete_reason = HISTORY_INCOMPLETE_REASON
                break
            async with page.expect_navigation(timeout=self._action_timeout_ms(), wait_until=NAVIGATION_WAIT_UNTIL):
                await page.locator(selectors.NEXT_PAGE_LINK).click()
            await page.locator(selectors.TRANSACTIONS_READY).wait_for(timeout=self._action_timeout_ms())
            pages_count += 1

        # Ни строк, ни надписи «Операций нет»: разметка таблицы изменилась, пустую историю не выдумываем
        if not rows and await page.locator(selectors.TRANSACTIONS_EMPTY).count() == 0:
            log.warning('Transactions table not recognized', extra={'product_id': product_id})
            raise domain.TransactionsLayoutNotRecognized()

        log.info('History pages read', extra={'product_id': product_id, 'pages_count': pages_count})
        transaction_rows = [parsing.TransactionRow(**row) for row in rows]
        history = parsing.parse_transactions(product_id, transaction_rows)
        history.incomplete_reason = incomplete_reason
        return history

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

    async def _read_product(self, product_id: str) -> domain.Product:
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
        response = await self.browser.page.goto(
            url, timeout=self._action_timeout_ms(), wait_until=NAVIGATION_WAIT_UNTIL
        )
        if response is not None and response.status >= HTTP_SERVER_ERROR:
            raise BankPageError(f'Bank page answered {response.status}')

    def _action_timeout_ms(self) -> float:
        return self.config.ACTION_TIMEOUT_SECONDS * MILLISECONDS_IN_SECOND
