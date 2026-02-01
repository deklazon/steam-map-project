from fastapi import FastAPI, HTTPException
import duckdb
import pandas as pd

# --- Глобальные переменные ---
PARQUET_FILE = 'games_with_coords.parquet'
app = FastAPI(
    title="Steam Games API",
    description="API для получения данных об играх из Steam.",
    version="0.2.0" # Версия обновлена, т.к. изменился способ доступа к данным
)

# --- Маршруты API (Endpoints) ---

@app.get("/api/v1/games")
def get_games(limit: int = 10, offset: int = 0):
    """
    Возвращает список игр с пагинацией, читая данные напрямую из Parquet-файла
    с помощью DuckDB для экономии памяти.

    - **limit**: Количество записей для возврата.
    - **offset**: Смещение (количество записей для пропуска).
    """
    try:
        # Устанавливаем соединение с DuckDB. ':memory:' означает, что база данных
        # работает в оперативной памяти, но сами данные она будет читать потоково с диска.
        con = duckdb.connect(database=':memory:', read_only=False)

        # Формируем SQL-запрос с пагинацией.
        # duckdb.read_parquet() создает "виртуальную" таблицу, к которой можно делать запросы.
        query = f"""
        SELECT *
        FROM read_parquet('{PARQUET_FILE}')
        LIMIT {limit}
        OFFSET {offset}
        """
        
        # Выполняем запрос и получаем результат сразу в виде Pandas DataFrame.
        # Важно: DuckDB сама оптимизирует чтение, и в память попадут только
        # запрошенные строки, а не весь файл.
        result_df = con.execute(query).fetchdf()
        
        # Закрываем соединение
        con.close()

        # --- Пост-обработка данных, как было раньше ---
        # Обрабатываем NaN/NaT значения, чтобы FastAPI мог корректно их сериализовать в JSON
        result_df = result_df.replace({pd.NA: None, pd.NaT: None, float('nan'): None})

        # Конвертируем колонки с датами в строки, если они есть в выборке
        for col in ['release_date', 'latest_review_date', 'latest_followers_recorded_at']:
            if col in result_df.columns:
                result_df[col] = result_df[col].astype(str)

        return result_df.to_dict(orient='records')

    except duckdb.Error as e:
        # Если DuckDB не смог выполнить запрос (например, файл поврежден)
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {e}")
    except FileNotFoundError:
        # Если Parquet-файл отсутствует
        raise HTTPException(status_code=500, detail=f"Критическая ошибка: Файл с данными '{PARQUET_FILE}' не найден.")
    except Exception as e:
        # Другие непредвиденные ошибки
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {e}")


@app.get("/")
def read_root():
    """
    Корневой маршрут, который предоставляет базовую информацию об API.
    """
    return {"message": "Добро пожаловать в Steam Games API. Используйте /docs для просмотра документации."}
