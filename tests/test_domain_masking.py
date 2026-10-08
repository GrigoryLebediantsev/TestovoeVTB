import pytest

from src import domain


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('2200 7012 3456 9012', '**** 9012'),
        ('2200701234569012', '**** 9012'),
        ('40817810500001234567', '**** 4567'),
        ('•• 4567', '**** 4567'),
        ('12', '**** 12'),
    ],
)
def test_mask_number_keeps_only_last_digits(number: str, expected: str) -> None:
    assert domain.mask_number(number) == expected


def test_mask_number_without_digits_hides_everything() -> None:
    assert domain.mask_number('Договор') == '****'
