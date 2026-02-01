import os
import pandas as pd
from sqlalchemy import create_engine
import sys

# --- Константы ---
PARQUET_FILE = 'games_with_coords.parquet'
TABLE_NAME = 'games'

def upload_data():
    """
    Загружает данные из Parquet файла в базу данных PostgreSQL.
    Строка подключения к БД берется из переменной окружения DATABASE_URL.
    """
    # 1. Получаем строку подключения из переменных окружения
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Ошибка: Переменная окружения DATABASE_URL не установлена.")
        print("Пожалуйста, установите ее перед запуском скрипта.")
        print("Пример: export DATABASE_URL='postgres://user:pass@host:port/db'")
        sys.exit(1)

    print("Шаг 1: Подключение к базе данных...")
    try:
        # SQLAlchemy использует psycopg2 под капотом
        engine = create_engine(db_url)
        with engine.connect() as connection:
            print("Соединение с базой данных успешно установлено.")
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        sys.exit(1)

    # 2. Читаем данные из Parquet файла
    print(f"Шаг 2: Чтение данных из файла '{PARQUET_FILE}'...")
    try:
        df = pd.read_parquet(PARQUET_FILE)
        print(f"Загружено {len(df)} строк.")
        
        # Очистка названий колонок для совместимости с SQL
        # SQL не любит пробелы, точки и заглавные буквы в названиях
        df.columns = [col.replace(' ', '_').replace('.', '').lower() for col in df.columns]

    except FileNotFoundError:
        print(f"Ошибка: Файл '{PARQUET_FILE}' не найден.")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении Parquet файла: {e}")
        sys.exit(1)

    # 3. Загружаем данные в базу данных
    print(f"Шаг 3: Загрузка данных в таблицу '{TABLE_NAME}'...")
    try:
        # to_sql - мощный метод Pandas для работы с базами данных
        # if_exists='replace' - если таблица уже существует, она будет удалена и создана заново
        # index=False - не сохраняем индекс DataFrame как отдельную колонку
        df.to_sql(TABLE_NAME, engine, if_exists='replace', index=False, chunksize=1000)
        print("Данные успешно загружены в базу данных!")
        
    except Exception as e:
        print(f"Ошибка при загрузке данных в базу: {e}")
        sys.exit(1)

if __name__ == '__main__':
    upload_data()