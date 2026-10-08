import datetime
import json
import logging
import traceback

# Стандартные атрибуты LogRecord; всё остальное пришло из extra={...}
STANDARD_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__) | {'message', 'asctime', 'app_name', 'app_version'}

SHORT_LEVEL_NAMES = {
    'DEBUG': 'DBG',
    'INFO': 'INF',
    'WARNING': 'WRN',
    'ERROR': 'ERR',
    'CRITICAL': 'CRT',
}

LEVEL_COLORS = {
    'DEBUG': '\033[90m',
    'INFO': '\033[32m',
    'WARNING': '\033[33m',
    'ERROR': '\033[31m',
    'CRITICAL': '\033[41m',
}
RESET_COLOR = '\033[0m'
DIM_COLOR = '\033[2m'


def _extra_fields(record: logging.LogRecord) -> dict[str, object]:
    return {key: value for key, value in record.__dict__.items() if key not in STANDARD_RECORD_FIELDS}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            'time': datetime.datetime.fromtimestamp(record.created, datetime.UTC).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'app_name': getattr(record, 'app_name', None),
            'app_version': getattr(record, 'app_version', None),
        }
        if record.levelno >= logging.ERROR:
            entry['location'] = f'{record.pathname}:{record.lineno}'
        if record.exc_info and record.exc_info[1]:
            error = record.exc_info[1]
            entry['error_type'] = type(error).__name__
            entry['error_message'] = str(error)
            entry['traceback'] = ''.join(traceback.format_exception(error))
        entry.update(_extra_fields(record))
        return json.dumps(entry, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        time_text = datetime.datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        level_name = SHORT_LEVEL_NAMES.get(record.levelname, record.levelname)
        color = LEVEL_COLORS.get(record.levelname, '')
        line = f'{DIM_COLOR}{time_text}{RESET_COLOR} {color}{level_name}{RESET_COLOR} {record.getMessage()}'

        extra = _extra_fields(record)
        if extra:
            line += ' ' + ' '.join(f'{DIM_COLOR}{key}={value}{RESET_COLOR}' for key, value in extra.items())
        if record.levelno >= logging.WARNING:
            line += f' {DIM_COLOR}({record.pathname}:{record.lineno}){RESET_COLOR}'
        if record.exc_info:
            line += '\n' + self.formatException(record.exc_info)
        return line
