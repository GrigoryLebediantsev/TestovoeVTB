MASK_PREFIX = '****'
VISIBLE_DIGITS_COUNT = 4


def mask_number(number: str) -> str:
    """Оставляет только последние цифры номера: '2200 7012 3456 9012' → '**** 9012'."""
    digits = ''.join(symbol for symbol in number if symbol.isdigit())
    if not digits:
        return MASK_PREFIX
    return f'{MASK_PREFIX} {digits[-VISIBLE_DIGITS_COUNT:]}'
