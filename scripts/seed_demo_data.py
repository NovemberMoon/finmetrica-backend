import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import asyncio
import uuid
import calendar
from datetime import datetime, date, time, timedelta

import asyncpg
import redis.asyncio as redis

from core.config import settings


USERNAME = "testuser2"


async def get_or_create_category(conn, name: str):
    row = await conn.fetchrow(
        "SELECT id FROM categories WHERE name = $1 LIMIT 1",
        name,
    )
    if row:
        return row["id"]

    category_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO categories (id, name, is_system, icon_url)
        VALUES ($1, $2, true, null)
        """,
        category_id,
        name,
    )
    return category_id


async def main():
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(dsn)

    user = await conn.fetchrow(
        "SELECT id FROM users WHERE username = $1",
        USERNAME,
    )

    if not user:
        raise RuntimeError(f"Пользователь {USERNAME} не найден. Сначала зарегистрируйся.")

    user_id = user["id"]

    account_rows = await conn.fetch(
        "SELECT id FROM accounts WHERE client_id = $1",
        user_id,
    )
    account_ids = [row["id"] for row in account_rows]

    if account_ids:
        await conn.execute(
            "DELETE FROM transactions WHERE account_id = ANY($1::uuid[])",
            account_ids,
        )

    await conn.execute("DELETE FROM budget_limits WHERE client_id = $1", user_id)
    await conn.execute("DELETE FROM financial_goals WHERE client_id = $1", user_id)
    await conn.execute("DELETE FROM investment_recommendations WHERE client_id = $1", user_id)
    await conn.execute("DELETE FROM accounts WHERE client_id = $1", user_id)

    await conn.execute(
        "UPDATE users SET risk_profile = 'MODERATE', access_level = 2 WHERE id = $1",
        user_id,
    )

    category_names = [
        "Зарплата",
        "Подработка",
        "Продукты",
        "Кафе и рестораны",
        "Транспорт",
        "Жильё",
        "Развлечения",
        "Здоровье",
        "Образование",
    ]

    categories = {}
    for name in category_names:
        categories[name] = await get_or_create_category(conn, name)

    main_account = uuid.uuid4()
    savings_account = uuid.uuid4()
    cash_account = uuid.uuid4()

    await conn.execute(
        """
        INSERT INTO accounts (id, client_id, name, type, currency, balance)
        VALUES
        ($1, $4, 'Основная карта', 'DEBIT_CARD', 'RUB', 0),
        ($2, $4, 'Накопительный счёт', 'DEPOSIT', 'RUB', 60000),
        ($3, $4, 'Наличные', 'CASH', 'RUB', 10000)
        """,
        main_account,
        savings_account,
        cash_account,
        user_id,
    )

    today = date.today()

    def tx_date(days_ago: int):
        return datetime.combine(today - timedelta(days=days_ago), time(hour=12))

    transactions = [
        (120000, "INCOME", "Зарплата за месяц", main_account, categories["Зарплата"], tx_date(20)),
        (25000, "INCOME", "Фриланс-проект", main_account, categories["Подработка"], tx_date(10)),

        (45000, "EXPENSE", "Аренда квартиры", main_account, categories["Жильё"], tx_date(18)),
        (18000, "EXPENSE", "Продукты за месяц", main_account, categories["Продукты"], tx_date(7)),
        (9500, "EXPENSE", "Кафе и рестораны", main_account, categories["Кафе и рестораны"], tx_date(5)),
        (6000, "EXPENSE", "Транспорт", main_account, categories["Транспорт"], tx_date(4)),
        (12000, "EXPENSE", "Развлечения", main_account, categories["Развлечения"], tx_date(3)),
        (4000, "EXPENSE", "Аптека и здоровье", main_account, categories["Здоровье"], tx_date(2)),
        (7500, "EXPENSE", "Курс по backend-разработке", main_account, categories["Образование"], tx_date(1)),
    ]

    for amount, tx_type, note, account_id, category_id, created_at in transactions:
        await conn.execute(
            """
            INSERT INTO transactions (id, amount, type, note, account_id, category_id, date)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            uuid.uuid4(),
            amount,
            tx_type,
            note,
            account_id,
            category_id,
            created_at,
        )

    await conn.execute(
        """
        UPDATE accounts
        SET balance = (
            SELECT COALESCE(SUM(
                CASE
                    WHEN type = 'INCOME' THEN amount
                    ELSE -amount
                END
            ), 0)
            FROM transactions
            WHERE account_id = $1
        )
        WHERE id = $1
        """,
        main_account,
    )

    month_start = date(today.year, today.month, 1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    month_end = date(today.year, today.month, last_day)

    limits = [
        (20000, categories["Продукты"]),
        (7000, categories["Кафе и рестораны"]),
        (7000, categories["Транспорт"]),
        (8000, categories["Развлечения"]),
        (50000, categories["Жильё"]),
    ]

    for amount_limit, category_id in limits:
        await conn.execute(
            """
            INSERT INTO budget_limits (id, amount_limit, client_id, category_id, start_date, end_date)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            uuid.uuid4(),
            amount_limit,
            user_id,
            category_id,
            month_start,
            month_end,
        )

    goals = [
        ("Финансовая подушка", 180000, 60000, date(today.year, 12, 31)),
        ("Новый ноутбук", 160000, 45000, date(today.year, 10, 1)),
        ("Путешествие", 120000, 20000, date(today.year + 1, 6, 1)),
    ]

    for title, target_amount, current_amount, target_date in goals:
        await conn.execute(
            """
            INSERT INTO financial_goals (id, title, target_amount, current_amount, target_date, client_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            uuid.uuid4(),
            title,
            target_amount,
            current_amount,
            target_date,
            user_id,
        )

    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.delete(f"ai_rec_user_{user_id}")
        await redis_client.aclose()
    except Exception:
        pass

    await conn.close()

    print("Demo data seeded successfully")
    print("User:", USERNAME)
    print("Risk profile: MODERATE")
    print("Income: 145000")
    print("Expenses: 102000")
    print("Monthly surplus: 43000")
    print("Exceeded limits: Кафе и рестораны, Развлечения")


asyncio.run(main())