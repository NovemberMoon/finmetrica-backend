# test_psycopg_ip.py
import psycopg2

conn = psycopg2.connect(
    host="172.19.0.3",
    port=5432,
    dbname="finmetrica_db",
    user="finmetrica_user",
    password="finmetrica_password",
)

print("CONNECTED")