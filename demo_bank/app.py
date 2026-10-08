import datetime
import enum
import secrets
from dataclasses import dataclass, field
from typing import Annotated
from urllib.parse import parse_qs

import pydantic
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from . import pages
from .data import PRODUCTS_BY_ID, DemoProduct, DemoTransaction, filter_by_posting_date
from .export import build_export_csv

DEMO_LOGIN = 'demo'
DEMO_PASSWORD = 'demo'
DEMO_ONE_TIME_CODE = '0000'

PENDING_COOKIE = 'demo_pending'
SESSION_COOKIE = 'demo_session'

HISTORY_PORTION_SIZE = 5
STATUS_CODE_BY_LABEL = {'Проведена': 'POSTED', 'В обработке': 'PENDING', 'Отклонена': 'DECLINED'}


class DemoBankMode(enum.StrEnum):
    NORMAL = 'normal'


@dataclass
class DemoBankState:
    mode: DemoBankMode
    pending_logins: set[str] = field(default_factory=set)  # прошли логин и пароль, ждут код
    sessions: set[str] = field(default_factory=set)
    # Запросы порций истории — по ним тест проверяет, что прототип не делает своих запросов
    history_requests: list[dict[str, object]] = field(default_factory=list)


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
    async def show_product(
        product_id: str,
        request: Request,
        # Строки, а не даты: пустое поле формы приходит как 'from='
        date_from: Annotated[str, Query(alias='from')] = '',
        date_to: Annotated[str, Query(alias='to')] = '',
        page: int = 1,
    ) -> Response:
        if not is_signed_in(request):
            return RedirectResponse('/login', status_code=303)
        product = PRODUCTS_BY_ID.get(product_id)
        if product is None:
            return HTMLResponse(pages.layout('Не найдено', '<h1>Продукт не найден</h1>'), status_code=404)
        return HTMLResponse(
            pages.product_page(product, _parse_query_date(date_from), _parse_query_date(date_to), page_number=page)
        )

    @app.get('/products/{product_id}/export.csv')
    async def export_history(
        product_id: str,
        request: Request,
        date_from: Annotated[str, Query(alias='from')] = '',
        date_to: Annotated[str, Query(alias='to')] = '',
    ) -> Response:
        if not is_signed_in(request):
            return RedirectResponse('/login', status_code=303)
        product = PRODUCTS_BY_ID.get(product_id)
        if product is None or not product.has_export:
            return HTMLResponse(pages.layout('Не найдено', '<h1>Экспорт недоступен</h1>'), status_code=404)
        transactions = filter_by_posting_date(
            product.transactions, _parse_query_date(date_from), _parse_query_date(date_to)
        )
        return Response(
            build_export_csv(product, transactions),
            media_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{product_id}.csv"'},
        )

    @app.get('/api/products/{product_id}/transactions')
    async def get_history_portion(
        product_id: str,
        request: Request,
        offset: int = 0,
        date_from: Annotated[str, Query(alias='from')] = '',
        date_to: Annotated[str, Query(alias='to')] = '',
    ) -> Response:
        if not is_signed_in(request):
            return JSONResponse({'detail': 'Not signed in'}, status_code=401)
        product = PRODUCTS_BY_ID.get(product_id)
        if product is None:
            return JSONResponse({'detail': 'Product not found'}, status_code=404)
        state.history_requests.append({'product_id': product_id, 'from': date_from, 'to': date_to, 'offset': offset})
        transactions = filter_by_posting_date(
            product.transactions, _parse_query_date(date_from), _parse_query_date(date_to)
        )
        portion = transactions[offset : offset + HISTORY_PORTION_SIZE]
        return JSONResponse(
            {
                'items': [_build_history_item(transaction, product) for transaction in portion],
                'hasMore': offset + HISTORY_PORTION_SIZE < len(transactions),
            }
        )

    # --- Служебные адреса для тестов ---

    @app.get('/_test/api-calls')
    async def get_api_calls() -> list[dict[str, object]]:
        return state.history_requests

    @app.get('/_test/health')
    async def health() -> dict[str, str]:
        return {'status': 'ok', 'mode': state.mode}

    @app.post('/_test/mode')
    async def set_mode(request: SetModeRequest) -> dict[str, str]:
        state.mode = request.mode
        state.pending_logins.clear()
        state.sessions.clear()
        state.history_requests.clear()
        return {'mode': state.mode}

    return app


async def _read_form(request: Request) -> dict[str, str]:
    """Разбор формы без python-multipart: тело application/x-www-form-urlencoded."""
    body = (await request.body()).decode()
    return {key: values[0] for key, values in parse_qs(body).items()}


def _build_history_item(transaction: DemoTransaction, product: DemoProduct) -> dict[str, object]:
    """Операция в формате сервера: даты ISO, сумма строкой с точкой, статус кодом — не как на странице."""
    return {
        'id': transaction.bank_id,
        'operationDate': transaction.operation_date.isoformat(),
        'postingDate': transaction.posting_date.isoformat() if transaction.posting_date else None,
        'amount': f'{transaction.amount:.2f}',
        'currency': product.currency,
        'description': transaction.description,
        'counterparty': transaction.counterparty,
        'category': transaction.category,
        'status': STATUS_CODE_BY_LABEL[transaction.status],
    }


def _parse_query_date(value: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(value) if value else None
    except ValueError:
        return None
