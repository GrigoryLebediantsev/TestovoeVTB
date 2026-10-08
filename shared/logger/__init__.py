import logging
import re
import sys

import pydantic

from .formatters import ConsoleFormatter, JsonFormatter

VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')
UVICORN_LOGGERS = ('uvicorn', 'uvicorn.error', 'uvicorn.access')


class LoggerConfig(pydantic.BaseModel):
    APP_NAME: str = 'app'
    APP_VERSION: str = '0.1.0'
    GIT_COMMIT_COUNT: int | None = None
    LEVEL: str = 'INFO'
    PRETTY_CONSOLE: bool = False

    @pydantic.field_validator('APP_VERSION')
    @classmethod
    def check_version(cls, value: str) -> str:
        if not VERSION_PATTERN.match(value):
            raise ValueError('version must look like 1.2.0')
        return value

    @property
    def full_version(self) -> str:
        """Последняя часть версии заменяется числом коммитов, если оно задано."""
        if self.GIT_COMMIT_COUNT is None:
            return self.APP_VERSION
        major, minor, _ = self.APP_VERSION.split('.')
        return f'{major}.{minor}.{self.GIT_COMMIT_COUNT}'


def init(config: LoggerConfig) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ConsoleFormatter() if config.PRETTY_CONSOLE else JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(config.LEVEL.upper())

    for logger_name in UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

    _add_app_fields(config.APP_NAME, config.full_version)


def _add_app_fields(app_name: str, app_version: str) -> None:
    default_factory = logging.getLogRecordFactory()

    def record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
        record = default_factory(*args, **kwargs)
        record.app_name = app_name
        record.app_version = app_version
        return record

    logging.setLogRecordFactory(record_factory)


__all__ = ['LoggerConfig', 'init']
