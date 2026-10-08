import logging
from html import escape

import pydantic
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from shared.browser_base import BrowserBase, BrowserConfig, BrowserMode
from src import domain
from src.usecase import ClientWindow

log = logging.getLogger(__name__)

MILLISECONDS_IN_SECOND = 1000
DECISION_ALLOW = 'allow'

# Кнопки записывают решение клиента в атрибут body, прототип ждёт его появления
READ_DECISION_SCRIPT = '() => document.body.dataset.decision'


SUMMARY_PAGE_TITLE = 'Выписка сформирована'
FAILURE_PAGE_TITLE = 'Выписка не сформирована'


class BrowserWindowConfig(BrowserConfig):
    CONSENT_TIMEOUT_SECONDS: float = 300
    # Собственный браузер: сколько ждать, пока клиент закроет окно с итогом, прежде чем закрыть его самим
    WINDOW_CLOSE_TIMEOUT_SECONDS: float = pydantic.Field(default=600, gt=0)


class BrowserWindow(BrowserBase, ClientWindow):
    """Страницы прототипа во вкладке клиента: создаются прямо во вкладке, без сервера."""

    def __init__(self, config: BrowserWindowConfig) -> None:
        super().__init__(config)
        self.window_config = config
        self._is_result_shown = False

    async def close(self) -> None:
        """В собственном браузере сначала ждёт, пока клиент закроет окно с итогом; в режиме CDP вкладка остаётся."""
        if self.window_config.MODE == BrowserMode.LAUNCH and self._is_result_shown:
            await self._wait_for_window_closed()
        await super().close()

    async def show_summary(self, bank_name: str, report: domain.ExtractionReport) -> None:
        await self._show_result(build_summary_page(bank_name, report))

    async def show_failure(self, reason: str) -> None:
        await self._show_result(build_failure_page(reason))

    async def _show_result(self, content: str) -> None:
        try:
            await self.page.set_content(content)
            await self.page.bring_to_front()
        except PlaywrightError as error:
            # Клиент мог уже закрыть вкладку: итог есть в консоли оператора и в отчёте
            log.warning('Result page not shown: %s', type(error).__name__)
            return
        self._is_result_shown = True
        log.info('Result page shown')

    async def _wait_for_window_closed(self) -> None:
        if self.page.is_closed():
            return
        log.info('Waiting for client to close the window')
        try:
            await self.page.wait_for_event(
                'close', timeout=self.window_config.WINDOW_CLOSE_TIMEOUT_SECONDS * MILLISECONDS_IN_SECOND
            )
        except PlaywrightTimeoutError:
            log.info('Window was not closed in time, closing browser')
        except PlaywrightError as error:
            log.warning('Waiting for window close failed: %s', type(error).__name__)

    async def ask_consent(self, bank_name: str, period: domain.Period, scope: list[str]) -> bool:
        await self.page.set_content(build_consent_page(bank_name, period, scope))
        await self.page.bring_to_front()
        log.info('Consent page shown')
        try:
            decision = await self.page.wait_for_function(
                READ_DECISION_SCRIPT,
                timeout=self.window_config.CONSENT_TIMEOUT_SECONDS * MILLISECONDS_IN_SECOND,
            )
        except PlaywrightTimeoutError as error:
            raise domain.ConsentTimeout() from error
        is_granted: bool = await decision.json_value() == DECISION_ALLOW
        return is_granted


def build_consent_page(bank_name: str, period: domain.Period, scope: list[str]) -> str:
    scope_items = ''.join(f'<li>{escape(item)}</li>' for item in scope)
    return _build_page(
        'Согласие на чтение данных',
        f"""<p>Банк: <strong>{escape(bank_name)}</strong></p>
<p>Период: <strong>{escape(_format_period(period))}</strong></p>
<p>Будут прочитаны:</p>
<ul>{scope_items}</ul>
<p>Логин, пароль, коды подтверждения и cookies не читаются и не сохраняются.
Вход в кабинет вы выполняете сами на следующем шаге.</p>
<button type="button" onclick="document.body.dataset.decision = 'allow'">Разрешаю</button>
<button type="button" onclick="document.body.dataset.decision = 'deny'">Отказываюсь</button>""",
    )


def build_summary_page(bank_name: str, report: domain.ExtractionReport) -> str:
    """Итог для клиента: количества, предупреждения и ошибки отчёта (в них только идентификаторы, без сумм)."""
    sections = [
        f'<p>Банк: <strong>{escape(bank_name)}</strong></p>',
        f'<p>Период: <strong>{escape(_format_period(report.period))}</strong></p>',
        f'<p>Продуктов: {report.products_count}</p>',
        f'<p>Операций: {report.transactions_count}</p>',
    ]
    if report.warnings:
        sections.append(f'<h2>Предупреждения</h2>{_build_list(report.warnings)}')
    if report.errors:
        sections.append(f'<h2>Ошибки</h2>{_build_list(report.errors)}')
    if report.is_complete():
        sections.append('<p>Все данные извлечены полностью.</p>')
    sections.append('<p>Файлы выписки сохранены. Окно можно закрыть.</p>')
    return _build_page(SUMMARY_PAGE_TITLE, '\n'.join(sections))


def build_failure_page(reason: str) -> str:
    return _build_page(
        FAILURE_PAGE_TITLE,
        f"""<p>Причина: {escape(reason)}.</p>
<p>Файлы выписки не сохранены. Окно можно закрыть.</p>""",
    )


def _build_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>
body {{ font-family: sans-serif; background: #f4f5f7; margin: 0; }}
main {{ max-width: 640px; margin: 48px auto; background: #fff; padding: 32px; border-radius: 8px; }}
button {{ padding: 10px 20px; margin-right: 12px; font-size: 16px; }}
</style>
</head>
<body>
<main>
<h1>{escape(title)}</h1>
{body}
</main>
</body>
</html>"""


def _build_list(items: list[str]) -> str:
    return '<ul>' + ''.join(f'<li>{escape(item)}</li>' for item in items) + '</ul>'


def _format_period(period: domain.Period) -> str:
    return f'{period.date_from:%d.%m.%Y} — {period.date_to:%d.%m.%Y}'
