import enum
import logging
import shutil
import tempfile

import pydantic
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

log = logging.getLogger(__name__)


class BrowserMode(enum.StrEnum):
    LAUNCH = 'launch'  # собственный браузер с окном
    CDP = 'cdp'  # подключение к уже открытому Chrome


class BrowserConfig(pydantic.BaseModel):
    MODE: BrowserMode = BrowserMode.LAUNCH
    PROFILE_DIR: str | None = None  # постоянный профиль; без него — временный, удаляется при закрытии
    CDP_URL: str = 'http://127.0.0.1:9222'


class BrowserBase:
    """Открывает рабочую вкладку браузера и закрывает её, не трогая чужой браузер в режиме CDP."""

    def __init__(self, config: BrowserConfig) -> None:
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._temporary_profile_dir: str | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError('Browser is not connected')
        return self._page

    async def connect(self) -> None:
        self._playwright = await async_playwright().start()
        if self.config.MODE == BrowserMode.CDP:
            await self._connect_over_cdp(self._playwright)
        else:
            await self._launch(self._playwright)

    async def close(self) -> None:
        if self.config.MODE == BrowserMode.LAUNCH and self._context is not None:
            await self._context.close()
        # В режиме CDP браузер клиента не закрываем: остановка Playwright только отключается от него
        if self._playwright is not None:
            await self._playwright.stop()
        if self._temporary_profile_dir is not None:
            shutil.rmtree(self._temporary_profile_dir, ignore_errors=True)
            log.info('Temporary browser profile removed')
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._temporary_profile_dir = None

    async def _connect_over_cdp(self, playwright: Playwright) -> None:
        self._browser = await playwright.chromium.connect_over_cdp(self.config.CDP_URL)
        if self._browser.contexts:
            self._context = self._browser.contexts[0]
        else:
            self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        log.info('Connected to browser over CDP')

    async def _launch(self, playwright: Playwright) -> None:
        profile_dir = self.config.PROFILE_DIR
        if profile_dir is None:
            self._temporary_profile_dir = tempfile.mkdtemp(prefix='browser-profile-')
            profile_dir = self._temporary_profile_dir
        self._context = await playwright.chromium.launch_persistent_context(
            profile_dir, headless=False, no_viewport=True
        )
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        log.info('Browser launched', extra={'temporary_profile': self._temporary_profile_dir is not None})
