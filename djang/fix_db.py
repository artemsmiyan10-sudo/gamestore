import sqlite3
import os

# Фиксируем путь к базе в текущей папке
db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Проверяем таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

if 'mfs_news' in tables:
    try:
        cursor.execute("ALTER TABLE mfs_news ADD COLUMN description TEXT DEFAULT '';")
        conn.commit()
        print("Успех! Колонка description создана в основной базе данных.")
    except Exception as e:
        print("Колонка уже существует или другая инфо:", e)
else:
    print("Таблица новостей еще не была создана. Список найденных таблиц:", tables)

conn.close()