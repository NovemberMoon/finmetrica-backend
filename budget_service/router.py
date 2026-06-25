import uuid
from datetime import datetime, timezone, date, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy import func

from dal.database import get_session
from dal.models.users import User
from dal.models.budget import (
    Account,
    AccountCreate,
    AccountUpdate,
    Transaction,
    TransactionCreate,
    TransactionUpdate,
    TransactionType,
    Category,
    CategoryCreate,
    CategoryUpdate,
    BudgetLimit,
    BudgetLimitCreate,
    BudgetLimitUpdate,
    FinancialGoal,
    FinancialGoalCreate,
    FinancialGoalUpdate,
)
from auth_service.security import get_current_user

router = APIRouter()


DEFAULT_CATEGORIES = [
    "Продукты",
    "Кафе и рестораны",
    "Транспорт",
    "Жильё",
    "Здоровье",
    "Одежда",
    "Развлечения",
    "Образование",
    "Подарки",
    "Зарплата",
    "Подработка",
    "Другое",
]


async def ensure_default_categories(session: AsyncSession) -> None:
    count = (await session.exec(select(func.count(Category.id)))).one()
    if count > 0:
        return

    for name in DEFAULT_CATEGORIES:
        session.add(Category(name=name, is_system=True))

    await session.commit()


async def get_user_account_or_404(
    account_id: uuid.UUID,
    current_user: User,
    session: AsyncSession,
) -> Account:
    account = await session.get(Account, account_id)

    if not account or account.client_id != current_user.id:
        raise HTTPException(status_code=404, detail="Счёт не найден")

    return account


def apply_transaction_to_balance(account: Account, tx: Transaction, sign: int = 1) -> None:
    if tx.type == TransactionType.INCOME:
        account.balance += sign * tx.amount
    else:
        account.balance -= sign * tx.amount


@router.get("/categories", response_model=List[Category])
async def get_categories(session: AsyncSession = Depends(get_session)):
    await ensure_default_categories(session)
    categories = (await session.exec(select(Category).order_by(Category.name))).all()
    return categories


@router.post("/categories", response_model=Category)
async def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    category = Category(**category_in.model_dump(), is_system=False)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=Category)
async def update_category(
    category_id: uuid.UUID,
    category_update: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    category = await session.get(Category, category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    if category.is_system:
        raise HTTPException(status_code=400, detail="Системную категорию нельзя редактировать")

    for key, value in category_update.model_dump(exclude_unset=True).items():
        setattr(category, key, value)

    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    category = await session.get(Category, category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    if category.is_system:
        raise HTTPException(status_code=400, detail="Системную категорию нельзя удалить")

    tx_count = (await session.exec(
        select(func.count(Transaction.id)).where(Transaction.category_id == category_id)
    )).one()

    if tx_count > 0:
        raise HTTPException(status_code=400, detail="Категория используется в транзакциях")

    await session.delete(category)
    await session.commit()
    return {"status": "success"}


@router.get("/accounts", response_model=List[Account])
async def get_accounts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    accounts = (await session.exec(
        select(Account).where(Account.client_id == current_user.id).order_by(Account.name)
    )).all()
    return accounts


@router.post("/accounts", response_model=Account)
async def create_account(
    account_in: AccountCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    new_account = Account(**account_in.model_dump(), client_id=current_user.id)
    session.add(new_account)
    await session.commit()
    await session.refresh(new_account)
    return new_account


@router.put("/accounts/{account_id}", response_model=Account)
async def update_account(
    account_id: uuid.UUID,
    account_update: AccountUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    account = await get_user_account_or_404(account_id, current_user, session)

    for key, value in account_update.model_dump(exclude_unset=True).items():
        setattr(account, key, value)

    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    account = await get_user_account_or_404(account_id, current_user, session)

    tx_count = (await session.exec(
        select(func.count(Transaction.id)).where(Transaction.account_id == account.id)
    )).one()

    if tx_count > 0:
        raise HTTPException(status_code=400, detail="Нельзя удалить счёт с транзакциями")

    await session.delete(account)
    await session.commit()
    return {"status": "success"}


@router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    account_id: Optional[uuid.UUID] = None,
    category_id: Optional[uuid.UUID] = None,
    tx_type: Optional[TransactionType] = Query(default=None),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    account_ids = (await session.exec(
        select(Account.id).where(Account.client_id == current_user.id)
    )).all()

    if not account_ids:
        return []

    statement = select(Transaction).where(Transaction.account_id.in_(account_ids))

    if account_id:
        if account_id not in account_ids:
            raise HTTPException(status_code=403, detail="Доступ к счёту запрещён")
        statement = statement.where(Transaction.account_id == account_id)

    if category_id:
        statement = statement.where(Transaction.category_id == category_id)

    if tx_type:
        statement = statement.where(Transaction.type == tx_type)

    if date_from:
        statement = statement.where(Transaction.date >= datetime.combine(date_from, time.min))

    if date_to:
        statement = statement.where(Transaction.date <= datetime.combine(date_to, time.max))

    statement = statement.order_by(Transaction.date.desc())

    return (await session.exec(statement)).all()


@router.post("/transactions", response_model=Transaction)
async def create_transaction(
    tx_in: TransactionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    account = await get_user_account_or_404(tx_in.account_id, current_user, session)

    data = tx_in.model_dump(exclude_none=True)
    new_tx = Transaction(**data)

    apply_transaction_to_balance(account, new_tx, sign=1)

    session.add(new_tx)
    session.add(account)
    await session.commit()
    await session.refresh(new_tx)
    return new_tx


@router.put("/transactions/{tx_id}", response_model=Transaction)
async def update_transaction(
    tx_id: uuid.UUID,
    tx_update: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = await session.get(Transaction, tx_id)

    if not tx:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")

    old_account = await get_user_account_or_404(tx.account_id, current_user, session)
    apply_transaction_to_balance(old_account, tx, sign=-1)

    update_data = tx_update.model_dump(exclude_unset=True)

    new_account = old_account
    if "account_id" in update_data and update_data["account_id"] != tx.account_id:
        new_account = await get_user_account_or_404(update_data["account_id"], current_user, session)

    for key, value in update_data.items():
        setattr(tx, key, value)

    apply_transaction_to_balance(new_account, tx, sign=1)

    session.add(tx)
    session.add(old_account)
    session.add(new_account)

    await session.commit()
    await session.refresh(tx)
    return tx


@router.delete("/transactions/{tx_id}")
async def delete_transaction(
    tx_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = await session.get(Transaction, tx_id)

    if not tx:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")

    account = await get_user_account_or_404(tx.account_id, current_user, session)
    apply_transaction_to_balance(account, tx, sign=-1)

    await session.delete(tx)
    session.add(account)
    await session.commit()

    return {"status": "success", "detail": "Транзакция удалена"}


@router.post("/limits", response_model=BudgetLimit)
async def create_limit(
    limit_in: BudgetLimitCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    category = await session.get(Category, limit_in.category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    limit = BudgetLimit(**limit_in.model_dump(), client_id=current_user.id)

    session.add(limit)
    await session.commit()
    await session.refresh(limit)
    return limit


@router.get("/limits", response_model=List[BudgetLimit])
async def get_limits(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return (await session.exec(
        select(BudgetLimit).where(BudgetLimit.client_id == current_user.id)
    )).all()


@router.put("/limits/{limit_id}", response_model=BudgetLimit)
async def update_limit(
    limit_id: uuid.UUID,
    limit_update: BudgetLimitUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = await session.get(BudgetLimit, limit_id)

    if not limit or limit.client_id != current_user.id:
        raise HTTPException(status_code=404, detail="Лимит не найден")

    for key, value in limit_update.model_dump(exclude_unset=True).items():
        setattr(limit, key, value)

    session.add(limit)
    await session.commit()
    await session.refresh(limit)
    return limit


@router.delete("/limits/{limit_id}")
async def delete_limit(
    limit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = await session.get(BudgetLimit, limit_id)

    if not limit or limit.client_id != current_user.id:
        raise HTTPException(status_code=404, detail="Лимит не найден")

    await session.delete(limit)
    await session.commit()
    return {"status": "success"}


@router.get("/limits/progress")
async def get_limits_progress(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limits = (await session.exec(
        select(BudgetLimit).where(BudgetLimit.client_id == current_user.id)
    )).all()

    account_ids = (await session.exec(
        select(Account.id).where(Account.client_id == current_user.id)
    )).all()

    result = []

    for limit in limits:
        spent = 0

        if account_ids:
            spent = (await session.exec(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.account_id.in_(account_ids),
                    Transaction.category_id == limit.category_id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.date >= datetime.combine(limit.start_date, time.min),
                    Transaction.date <= datetime.combine(limit.end_date, time.max),
                )
            )).one()

        result.append({
            "limit_id": str(limit.id),
            "category_id": str(limit.category_id),
            "start_date": str(limit.start_date),
            "end_date": str(limit.end_date),
            "amount_limit": limit.amount_limit,
            "amount_spent": spent,
            "amount_left": limit.amount_limit - spent,
            "is_exceeded": spent > limit.amount_limit,
            "progress_percent": round((spent / limit.amount_limit) * 100, 2) if limit.amount_limit else 0,
        })

    return {"progress": result}


@router.post("/goals", response_model=FinancialGoal)
async def create_goal(
    goal_in: FinancialGoalCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    goal = FinancialGoal(**goal_in.model_dump(), client_id=current_user.id)

    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


@router.get("/goals", response_model=List[FinancialGoal])
async def get_goals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return (await session.exec(
        select(FinancialGoal).where(FinancialGoal.client_id == current_user.id)
    )).all()


@router.put("/goals/{goal_id}", response_model=FinancialGoal)
async def update_goal(
    goal_id: uuid.UUID,
    goal_update: FinancialGoalUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    goal = await session.get(FinancialGoal, goal_id)

    if not goal or goal.client_id != current_user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    for key, value in goal_update.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)

    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    goal = await session.get(FinancialGoal, goal_id)

    if not goal or goal.client_id != current_user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    await session.delete(goal)
    await session.commit()
    return {"status": "success"}


@router.get("/analytics/summary")
async def get_summary_analytics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    account_ids = (await session.exec(
        select(Account.id).where(Account.client_id == current_user.id)
    )).all()

    if not account_ids:
        return {
            "total_balance": 0,
            "total_income": 0,
            "total_expense": 0,
            "surplus": 0,
            "expenses_by_category": [],
            "recent_transactions": [],
        }

    tx_filter = [
        Transaction.account_id.in_(account_ids)
    ]

    if date_from:
        tx_filter.append(Transaction.date >= datetime.combine(date_from, time.min))

    if date_to:
        tx_filter.append(Transaction.date <= datetime.combine(date_to, time.max))

    total_balance = (await session.exec(
        select(func.coalesce(func.sum(Account.balance), 0)).where(Account.client_id == current_user.id)
    )).one()

    total_income = (await session.exec(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *tx_filter,
            Transaction.type == TransactionType.INCOME,
        )
    )).one()

    total_expense = (await session.exec(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *tx_filter,
            Transaction.type == TransactionType.EXPENSE,
        )
    )).one()

    expenses_raw = (await session.exec(
        select(Category.name, func.coalesce(func.sum(Transaction.amount), 0)).join(
            Category,
            Category.id == Transaction.category_id,
            isouter=True,
        ).where(
            *tx_filter,
            Transaction.type == TransactionType.EXPENSE,
        ).group_by(Category.name)
    )).all()

    recent_transactions = (await session.exec(
        select(Transaction).where(*tx_filter).order_by(Transaction.date.desc()).limit(10)
    )).all()

    return {
        "total_balance": total_balance,
        "total_income": total_income,
        "total_expense": total_expense,
        "surplus": total_income - total_expense,
        "expenses_by_category": [
            {"category": row[0] or "Без категории", "total": row[1]}
            for row in expenses_raw
        ],
        "recent_transactions": recent_transactions,
    }


@router.post("/sync", response_model=dict)
async def sync_offline_transactions(
    transactions_in: List[TransactionCreate],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    added_count = 0

    for tx_in in transactions_in:
        account = await session.get(Account, tx_in.account_id)

        if account and account.client_id == current_user.id:
            new_tx = Transaction(**tx_in.model_dump(exclude_none=True))
            apply_transaction_to_balance(account, new_tx, sign=1)

            session.add(new_tx)
            session.add(account)
            added_count += 1

    await session.commit()

    return {"status": "success", "synced_transactions": added_count}

@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    today = date.today()
    month_start = date(today.year, today.month, 1)

    account_ids = (await session.exec(
        select(Account.id).where(Account.client_id == current_user.id)
    )).all()

    accounts = (await session.exec(
        select(Account).where(Account.client_id == current_user.id).order_by(Account.name)
    )).all()

    goals = (await session.exec(
        select(FinancialGoal).where(FinancialGoal.client_id == current_user.id)
    )).all()

    limits = (await session.exec(
        select(BudgetLimit).where(BudgetLimit.client_id == current_user.id)
    )).all()

    total_balance = (await session.exec(
        select(func.coalesce(func.sum(Account.balance), 0)).where(
            Account.client_id == current_user.id
        )
    )).one()

    if not account_ids:
        return {
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "username": current_user.username,
                "risk_profile": current_user.risk_profile,
            },
            "total_balance": 0,
            "month_income": 0,
            "month_expense": 0,
            "month_surplus": 0,
            "accounts": [],
            "goals": [],
            "limits_progress": [],
            "expenses_by_category": [],
            "recent_transactions": [],
        }

    month_filter = [
        Transaction.account_id.in_(account_ids),
        Transaction.date >= datetime.combine(month_start, time.min),
        Transaction.date <= datetime.combine(today, time.max),
    ]

    month_income = (await session.exec(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *month_filter,
            Transaction.type == TransactionType.INCOME,
        )
    )).one()

    month_expense = (await session.exec(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *month_filter,
            Transaction.type == TransactionType.EXPENSE,
        )
    )).one()

    expenses_raw = (await session.exec(
        select(Category.name, func.coalesce(func.sum(Transaction.amount), 0)).join(
            Category,
            Category.id == Transaction.category_id,
            isouter=True,
        ).where(
            *month_filter,
            Transaction.type == TransactionType.EXPENSE,
        ).group_by(Category.name)
    )).all()

    recent_transactions = (await session.exec(
        select(Transaction).where(
            Transaction.account_id.in_(account_ids)
        ).order_by(Transaction.date.desc()).limit(10)
    )).all()

    limits_progress = []

    for limit in limits:
        spent = (await session.exec(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.account_id.in_(account_ids),
                Transaction.category_id == limit.category_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.date >= datetime.combine(limit.start_date, time.min),
                Transaction.date <= datetime.combine(limit.end_date, time.max),
            )
        )).one()

        category = await session.get(Category, limit.category_id)

        limits_progress.append({
            "limit_id": str(limit.id),
            "category_id": str(limit.category_id),
            "category_name": category.name if category else "Без категории",
            "amount_limit": limit.amount_limit,
            "amount_spent": spent,
            "amount_left": limit.amount_limit - spent,
            "progress_percent": round((spent / limit.amount_limit) * 100, 2) if limit.amount_limit else 0,
            "is_exceeded": spent > limit.amount_limit,
            "start_date": str(limit.start_date),
            "end_date": str(limit.end_date),
        })

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "username": current_user.username,
            "risk_profile": current_user.risk_profile,
        },
        "total_balance": total_balance,
        "month_income": month_income,
        "month_expense": month_expense,
        "month_surplus": month_income - month_expense,
        "accounts": accounts,
        "goals": [
            {
                "id": str(goal.id),
                "title": goal.title,
                "target_amount": goal.target_amount,
                "current_amount": goal.current_amount,
                "progress_percent": round((goal.current_amount / goal.target_amount) * 100, 2)
                if goal.target_amount else 0,
                "target_date": str(goal.target_date),
            }
            for goal in goals
        ],
        "limits_progress": limits_progress,
        "expenses_by_category": [
            {
                "category": row[0] or "Без категории",
                "total": row[1],
            }
            for row in expenses_raw
        ],
        "recent_transactions": recent_transactions,
    }