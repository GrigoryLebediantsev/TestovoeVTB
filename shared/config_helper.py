import sys

import pydantic
from pydantic_settings import BaseSettings

NESTED_DELIMITER = '__'


def load_settings[T: BaseSettings](settings_class: type[T]) -> T:
    """Создаёт настройки; при ошибке печатает недостающие переменные окружения и завершает процесс с кодом 1."""
    try:
        return settings_class()
    except pydantic.ValidationError as error:
        missing_names, invalid_lines = _describe_errors(settings_class, error)
        lines = ['Не удалось загрузить настройки.']
        if missing_names:
            lines.append('Не заданы переменные окружения:')
            lines.extend(f'  {name}' for name in missing_names)
        if invalid_lines:
            lines.append('Неверные значения:')
            lines.extend(f'  {line}' for line in invalid_lines)
        print('\n'.join(lines), file=sys.stderr)
        sys.exit(1)


def _describe_errors(
    settings_class: type[BaseSettings], error: pydantic.ValidationError
) -> tuple[list[str], list[str]]:
    missing_names: list[str] = []
    invalid_lines: list[str] = []
    for item in error.errors():
        location = [str(part) for part in item['loc']]
        if item['type'] == 'missing':
            missing_names.extend(_required_env_names(settings_class, location))
        else:
            invalid_lines.append(f'{_env_name(location)}: {item["msg"]}')
    return missing_names, invalid_lines


def _required_env_names(model_class: type[pydantic.BaseModel], location: list[str]) -> list[str]:
    """Пропущен целый раздел — раскрываем его обязательные поля, иначе возвращаем имя самого поля."""
    nested_class: object = model_class
    for part in location:
        if not (isinstance(nested_class, type) and issubclass(nested_class, pydantic.BaseModel)):
            return [_env_name(location)]
        nested_field = nested_class.model_fields.get(part)
        if nested_field is None:
            return [_env_name(location)]
        nested_class = nested_field.annotation

    if isinstance(nested_class, type) and issubclass(nested_class, pydantic.BaseModel):
        names: list[str] = []
        for field_name, field_info in nested_class.model_fields.items():
            if field_info.is_required():
                names.extend(_required_env_names(model_class, [*location, field_name]))
        return names
    return [_env_name(location)]


def _env_name(location: list[str]) -> str:
    return NESTED_DELIMITER.join(location).upper()
