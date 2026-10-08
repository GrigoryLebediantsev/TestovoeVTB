import enum
import secrets
from dataclasses import dataclass, field
from urllib.parse import parse_qs

import pydantic
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from . import pages
from .data import PRODUCTS_BY_ID

DEMO_LOGIN = 'demo'
DEMO_PASSWORD = 'demo'
DEMO_ONE_TIME_CODE = '0000'

PENDING_COOKIE = 'demo_pending'
SESSION_COOKIE = 'demo_session'


class DemoBankMode(enum.StrEnum):
    NORMAL = 'normal'


@dataclass
class DemoBankState:
    mode: DemoBankMode
    pending_logins: set[str] = field(default_factory=set)  # прошли логин и пароль, ждут код
    sessions: set[str] = field(default_factory=set)


class SetModeRequest(pydantic.BaseModel):
    mode: DemoBankMode


def create_app(mode: DemoBankMode = DemoBankMode.NORMAL) -> FastAPI:
    app = FastAPI(title='Демо-банк', docs_url=None, redoc_url=None)
    state = DemoBankState(mode=mode)

    def is_signed_in(request: Request) -> bool:
        return request.cookies.get(SESSION_COOKIE) in state.sessions

    @app.get('/')
    async def index() -> Response:
        return RedirectResponse('/products', status_code=303)

    @app.get('/login')
    async def show_login(request: Request) -> Response:
        if is_signed_in(request):
            return RedirectResponse('/products', status_code=303)
        return HTMLResponse(pages.login_page())

    @app.post('/login')
    async def submit_login(request: Request) -> Response:
        form = await _read_form(request)
        if form.get('login') != DEMO_LOGIN or form.get('password') != DEMO_PASSWORD:
            return HTMLResponse(pages.login_page(error='Неверный логин или пароль'), status_code=401)
        token = secrets.token_urlsafe(16)
        state.pending_logins.add(token)
        response = RedirectResponse('/otp', status_code=303)
        response.set_cookie(PENDING_COOKIE, token, httponly=True)
        return response

    @app.get('/otp')
    async def show_one_time_code(request: Request) -> Response:
        if request.cookies.get(PENDING_COOKIE) not in state.pending_logins:
            return RedirectResponse('/login', status_code=303)
        return HTMLResponse(pages.one_time_code_page())

    @app.post('/otp')
    async def submit_one_time_code(request: Request) -> Response:
        pending_token = request.cookies.get(PENDING_COOKIE)
        if pending_token not in state.pending_logins:
            return RedirectResponse('/login', status_code=303)
        form = await _read_form(request)
        if form.get('code') != DEMO_ONE_TIME_CODE:
            return HTMLResponse(pages.one_time_code_page(error='Неверный код'), status_code=401)
        state.pending_logins.discard(pending_token)
        session_token = secrets.token_urlsafe(16)
        state.sessions.add(session_token)
        response = RedirectResponse('/products', status_code=303)
        response.delete_cookie(PENDING_COOKIE)
        response.set_cookie(SESSION_COOKIE, session_token, httponly=True)
        return response

    @app.get('/products')
    async def show_products(request: Request) -> Response:
        if not is_signed_in(request):
            return RedirectResponse('/login', status_code=303)
        return HTMLResponse(pages.products_page())

    @app.get('/products/{product_id}')
    async def show_product(product_id: str, request: Request) -> Response:
        if not is_signed_in(request):
            return RedirectResponse('/login', status_code=303)
        product = PRODUCTS_BY_ID.get(product_id)
        if product is None:
            return HTMLResponse(pages.layout('Не найдено', '<h1>Продукт не найден</h1>'), status_code=404)
        return HTMLResponse(pages.product_page(product))

    # --- Служебные адреса для тестов ---

    @app.get('/_test/health')
    async def health() -> dict[str, str]:
        return {'status': 'ok', 'mode': state.mode}

    @app.post('/_test/mode')
    async def set_mode(request: SetModeRequest) -> dict[str, str]:
        state.mode = request.mode
        state.pending_logins.clear()
        state.sessions.clear()
        return {'mode': state.mode}

    return app


async def _read_form(request: Request) -> dict[str, str]:
    """Разбор формы без python-multipart: тело application/x-www-form-urlencoded."""
    body = (await request.body()).decode()
    return {key: values[0] for key, values in parse_qs(body).items()}
