import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        user="finmetrica_user",
        password="finmetrica_password",
        database="finmetrica_db",
        host="127.0.0.1",
        port=5433,
    )

    value = await conn.fetchval("SELECT 1")
    print(value)

    await conn.close()

asyncio.run(main())