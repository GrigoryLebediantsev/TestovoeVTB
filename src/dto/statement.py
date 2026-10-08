import datetime
from decimal import Decimal
from typing import Annotated

import pydantic

from src import domain

MONEY_PRECISION = Decimal('0.01')


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


# Денежная сумма всегда с двумя знаками после запятой: 125430.5 → 125430.50
Money = Annotated[Decimal, pydantic.PlainSerializer(_round_money, return_type=Decimal)]


class ExtractStatementInput(pydantic.BaseModel):
    bank: str
    period_from: datetime.date
    period_to: datetime.date
    format: domain.StatementFormat = domain.StatementFormat.BOTH


class ExtractStatementOutput(pydantic.BaseModel):
    output_folder: str
    products_count: int
    transactions_count: int
    warnings_count: int
    errors_count: int
    is_complete: bool = pydantic.Field(description='Нет предупреждений, ошибок и продуктов с пропусками')


class PeriodOutput(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(serialize_by_alias=True)

    date_from: datetime.date = pydantic.Field(serialization_alias='from')
    date_to: datetime.date = pydantic.Field(serialization_alias='to')

    @classmethod
    def from_domain(cls, period: domain.Period) -> PeriodOutput:
        return cls(date_from=period.date_from, date_to=period.date_to)


class ProductRequisitesOutput(pydantic.BaseModel):
    account_number: str | None
    bic: str | None
    correspondent_account: str | None
    bank_name: str | None

    @classmethod
    def from_domain(cls, requisites: domain.ProductRequisites) -> ProductRequisitesOutput:
        return cls(
            account_number=requisites.account_number,
            bic=requisites.bic,
            correspondent_account=requisites.correspondent_account,
            bank_name=requisites.bank_name,
        )


class ProductDetailsOutput(pydantic.BaseModel):
    interest_rate: Decimal | None
    opened_at: datetime.date | None
    credit_limit: Money | None
    debt: Money | None

    @classmethod
    def from_domain(cls, details: domain.ProductDetails) -> ProductDetailsOutput:
        return cls(
            interest_rate=details.interest_rate,
            opened_at=details.opened_at,
            credit_limit=details.credit_limit,
            debt=details.debt,
        )


class ProductOutput(pydantic.BaseModel):
    product_id: str
    type: domain.ProductType
    name: str
    masked_number: str
    currency: str = pydantic.Field(description='Код валюты ISO 4217')
    balance: Money | None
    available_balance: Money | None
    linked_account_id: str | None = pydantic.Field(description='Только у карты: счёт, к которому она привязана')
    requisites: ProductRequisitesOutput | None
    details: ProductDetailsOutput

    @classmethod
    def from_domain(cls, product: domain.Product) -> ProductOutput:
        requisites = ProductRequisitesOutput.from_domain(product.requisites) if product.requisites else None
        return cls(
            product_id=product.product_id,
            type=product.type,
            name=product.name,
            masked_number=product.masked_number,
            currency=product.currency,
            balance=product.balance,
            available_balance=product.available_balance,
            linked_account_id=product.linked_account_id,
            requisites=requisites,
            details=ProductDetailsOutput.from_domain(product.details),
        )


class ProductCsvRowOutput(pydantic.BaseModel):
    """Строка products.csv: вложенные реквизиты и метаданные — плоскими колонками."""

    product_id: str
    type: domain.ProductType
    name: str
    masked_number: str
    currency: str
    balance: Money | None
    available_balance: Money | None
    linked_account_id: str | None
    requisites_account_number: str | None
    requisites_bic: str | None
    requisites_correspondent_account: str | None
    requisites_bank_name: str | None
    details_interest_rate: Decimal | None
    details_opened_at: datetime.date | None
    details_credit_limit: Money | None
    details_debt: Money | None

    @classmethod
    def from_domain(cls, product: domain.Product) -> ProductCsvRowOutput:
        requisites = product.requisites or domain.ProductRequisites()
        return cls(
            product_id=product.product_id,
            type=product.type,
            name=product.name,
            masked_number=product.masked_number,
            currency=product.currency,
            balance=product.balance,
            available_balance=product.available_balance,
            linked_account_id=product.linked_account_id,
            requisites_account_number=requisites.account_number,
            requisites_bic=requisites.bic,
            requisites_correspondent_account=requisites.correspondent_account,
            requisites_bank_name=requisites.bank_name,
            details_interest_rate=product.details.interest_rate,
            details_opened_at=product.details.opened_at,
            details_credit_limit=product.details.credit_limit,
            details_debt=product.details.debt,
        )


class TransactionOutput(pydantic.BaseModel):
    transaction_id: str
    id_source: domain.TransactionIdSource
    product_id: str
    operation_date: datetime.date
    posting_date: datetime.date | None
    amount: Money = pydantic.Field(description='Минус — списание')
    currency: str = pydantic.Field(description='Код валюты ISO 4217')
    type: domain.TransactionType
    description: str
    counterparty: str | None
    category: domain.TransactionCategory
    status: domain.TransactionStatus
    is_duplicate: bool

    @classmethod
    def from_domain(cls, transaction: domain.Transaction) -> TransactionOutput:
        return cls(
            transaction_id=transaction.transaction_id,
            id_source=transaction.id_source,
            product_id=transaction.product_id,
            operation_date=transaction.operation_date,
            posting_date=transaction.posting_date,
            amount=transaction.amount,
            currency=transaction.currency,
            type=transaction.type,
            description=transaction.description,
            counterparty=transaction.counterparty,
            category=transaction.category,
            status=transaction.status,
            is_duplicate=transaction.is_duplicate,
        )


class StatementOutput(pydantic.BaseModel):
    bank: str
    extracted_at: datetime.datetime
    period: PeriodOutput
    products: list[ProductOutput] = pydantic.Field(default_factory=list)
    transactions: list[TransactionOutput] = pydantic.Field(default_factory=list)

    @classmethod
    def from_domain(cls, statement: domain.Statement) -> StatementOutput:
        return cls(
            bank=statement.bank,
            extracted_at=statement.extracted_at,
            period=PeriodOutput.from_domain(statement.period),
            products=[ProductOutput.from_domain(product) for product in statement.products],
            transactions=[TransactionOutput.from_domain(transaction) for transaction in statement.transactions],
        )
