import os
from passlib.context import CryptContext
import pymysql

print("Параметры подключения к DB:")
print(f"DB_HOST: {os.environ.get('DB_HOST')}")
print(f"DB_PORT: {os.environ.get('DB_PORT')}")
print(f"DB_USER: {os.environ.get('MYSQL_USER')}")
print(f"DB_PASSWORD: {'*' * len(os.environ.get('MYSQL_PASSWORD', ''))}")
print(f"DB_NAME: {os.environ.get('MYSQL_DATABASE')}")

DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("MYSQL_USER", "myuser")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", "mypassword")
DB_NAME = os.environ.get("MYSQL_DATABASE", "mydb")

SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@teenfreelance.ru")
SUPPORT_NICK = os.environ.get("SUPPORT_NICK", "support")
SUPPORT_NAME = os.environ.get("SUPPORT_NAME", "Service Support")
SUPPORT_PASSWORD = os.environ.get("SUPPORT_PASSWORD", "support123")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = pwd_context.hash(SUPPORT_PASSWORD)

conn = pymysql.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
    )
try:
    with conn.cursor() as cursor:
        # Проверяем существование колонки is_support
        cursor.execute("SHOW COLUMNS FROM users LIKE 'is_support'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN is_support BOOLEAN DEFAULT FALSE")
            conn.commit()
            print("Added is_support column to users table")

        # Продолжаем с созданием пользователя
        cursor.execute("SELECT id FROM users WHERE email=%s", (SUPPORT_EMAIL,))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO users (name, nickname, email, password_hash, is_support, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
                (SUPPORT_NAME, SUPPORT_NICK, SUPPORT_EMAIL, password_hash, True)
            )
            conn.commit()
            print("Support user created.")
        else:
            print("Support user already exists.")
finally:
    conn.close()