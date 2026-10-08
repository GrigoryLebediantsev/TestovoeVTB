# Официальный образ Playwright: Chromium и системные библиотеки для него уже установлены.
# Версия совпадает с playwright в uv.lock, иначе библиотека не найдёт свой браузер
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /uvx /bin/

# В образе Python 3.12, проекту нужен 3.14: uv скачивает его сам.
# Окружение — вне папки проекта, чтобы его не перекрыла смонтированная папка с кодом
ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала только зависимости: слой пересобирается лишь при изменении lock-файла
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --python 3.14

COPY --chown=pwuser:pwuser . .
RUN chown pwuser:pwuser /app

# Не root: браузер и прототип работают с правами обычного пользователя образа
USER pwuser

CMD ["python", "-m", "scripts.headless_demo"]
