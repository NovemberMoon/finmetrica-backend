import uuid
import enum
from datetime import datetime, date, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class AccountType(str, enum.Enum):
    CASH = "CASH"
    DEBIT_CARD = "DEBIT_CARD"
    CREDIT_CARD = "CREDIT_CARD"
    DEPOSIT = "DEPOSIT"


class TransactionType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class AccountBase(SQLModel):
    name: str
    type: AccountType
    currency: str = Field(default="RUB")


class Account(AccountBase, table=True):
    __tablename__ = "accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="users.id")
    balance: int = Field(default=0)


class AccountCreate(AccountBase):
    balance: int = 0


class AccountUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    currency: Optional[str] = None


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    is_system: bool = Field(default=False)
    icon_url: Optional[str] = Field(default=None)


class CategoryCreate(SQLModel):
    name: str
    icon_url: Optional[str] = None


class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    icon_url: Optional[str] = None


class BudgetLimit(SQLModel, table=True):
    __tablename__ = "budget_limits"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    amount_limit: int
    client_id: uuid.UUID = Field(foreign_key="users.id")
    category_id: uuid.UUID = Field(foreign_key="categories.id")
    start_date: date
    end_date: date


class BudgetLimitCreate(SQLModel):
    amount_limit: int
    category_id: uuid.UUID
    start_date: date
    end_date: date


class BudgetLimitUpdate(SQLModel):
    amount_limit: Optional[int] = None
    category_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class FinancialGoal(SQLModel, table=True):
    __tablename__ = "financial_goals"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    target_amount: int
    current_amount: int = Field(default=0)
    target_date: date
    client_id: uuid.UUID = Field(foreign_key="users.id")


class FinancialGoalCreate(SQLModel):
    title: str
    target_amount: int
    current_amount: int = 0
    target_date: date


class FinancialGoalUpdate(SQLModel):
    title: Optional[str] = None
    target_amount: Optional[int] = None
    current_amount: Optional[int] = None
    target_date: Optional[date] = None


class TransactionBase(SQLModel):
    amount: int
    type: TransactionType
    note: Optional[str] = None
    account_id: uuid.UUID = Field(foreign_key="accounts.id")
    category_id: Optional[uuid.UUID] = Field(default=None, foreign_key="categories.id")


class Transaction(TransactionBase, table=True):
    __tablename__ = "transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class TransactionCreate(TransactionBase):
    date: Optional[datetime] = None


class TransactionUpdate(SQLModel):
    amount: Optional[int] = None
    type: Optional[TransactionType] = None
    note: Optional[str] = None
    account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    date: Optional[datetime] = None