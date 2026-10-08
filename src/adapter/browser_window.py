import logging
from html import escape

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from shared.browser_base import BrowserBase, BrowserConfig
from src import domain
from src.usecase import ClientWindow

log = logging.getLogger(__name__)

MILLISECONDS_IN_SECOND = 1000
DECISION_ALLOW = 'allow'

# Кнопки записывают решение клиента в атрибут body, прототип ждёт его появления
READ_DECISION_SCRIPT = '() => document.body.dataset.decision'


class BrowserWindowConfig(BrowserConfig):
    CONSENT_TIMEOUT_SECONDS: float = 300


class BrowserWindow(BrowserBase, ClientWindow):
    """Страницы прототипа во вкладке клиента: создаются прямо во вкладке, без сервера."""

    def __init__(self, config: BrowserWindowConfig) -> None:
        super().__init__(config)
        self.window_config = config

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
    period_text = f'{period.date_from:%d.%m.%Y} — {period.date_to:%d.%m.%Y}'
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Согласие на чтение данных</title>
<style>
body {{ font-family: sans-serif; background: #f4f5f7; margin: 0; }}
main {{ max-width: 640px; margin: 48px auto; background: #fff; padding: 32px; border-radius: 8px; }}
button {{ padding: 10px 20px; margin-right: 12px; font-size: 16px; }}
</style>
</head>
<body>
<main>
<h1>Согласие на чтение данных</h1>
<p>Банк: <strong>{escape(bank_name)}</strong></p>
<p>Период: <strong>{escape(period_text)}</strong></p>
<p>Будут прочитаны:</p>
<ul>{scope_items}</ul>
<p>Логин, пароль, коды подтверждения и cookies не читаются и не сохраняются.
Вход в кабинет вы выполняете сами на следующем шаге.</p>
<button type="button" onclick="document.body.dataset.decision = 'allow'">Разрешаю</button>
<button type="button" onclick="document.body.dataset.decision = 'deny'">Отказываюсь</button>
</main>
</body>
</html>"""
