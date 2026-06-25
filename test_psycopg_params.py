import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    dbname="finmetrica_db",
    user="finmetrica_user",
    password="finmetrica_password",
    sslmode="disable",
    connect_timeout=5,
)

print("CONNECTED")

cur = conn.cursor()
cur.execute("SELECT 1")
print(cur.fetchone())

cur.close()
conn.close()