import datetime
import enum
from dataclasses import dataclass, field
from decimal import Decimal


class ProductType(enum.StrEnum):
    ACCOUNT = 'account'
    CARD = 'card'
    DEPOSIT = 'deposit'
    LOAN = 'loan'


@dataclass
class ProductRequisites:
    account_number: str | None = None
    bic: str | None = None
    correspondent_account: str | None = None
    bank_name: str | None = None


@dataclass
class ProductDetails:
    interest_rate: Decimal | None = None
    opened_at: datetime.date | None = None
    credit_limit: Decimal | None = None
    debt: Decimal | None = None


@dataclass
class Product:
    product_id: str
    type: ProductType
    name: str
    masked_number: str
    currency: str
    balance: Decimal | None = None
    available_balance: Decimal | None = None
    linked_account_id: str | None = None
    requisites: ProductRequisites | None = None
    details: ProductDetails = field(default_factory=ProductDetails)
