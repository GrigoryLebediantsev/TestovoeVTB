import logging
from typing import Literal

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from shared.browser_base import BrowserBase
from src import domain
from src.usecase import Bank

from . import parsing, selectors
from .config import DemoBankConfig

log = logging.getLogger(__name__)

MILLISECONDS_IN_SECOND = 1000
# Достаточно готовой разметки: нужные элементы затем ждём явно
NAVIGATION_WAIT_UNTIL: Literal['domcontentloaded'] = 'domcontentloaded'

# Пары «подпись → значение и ссылка» со страницы продукта
READ_FIELD_ROWS_SCRIPT = """rows => rows.map(row => ({
    label: row.querySelector('dt')?.innerText.trim() ?? '',
    text: row.querySelector('dd')?.innerText.trim() ?? '',
    link: row.querySelector('dd a')?.getAttribute('href') ?? null,
}))"""
READ_LINKS_SCRIPT = 'links => links.map(link => link.getAttribute("href"))'


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
