import pandas as pd

# --- Настройки ---
SOURCE_FILE = 'steam_games.parquet'
TARGET_FILE = 'games_cleaned.parquet'

# Колонки, которые проверяем на наличие пустых значений или нулей
COLUMNS_TO_VALIDATE = [
    'title',
    'tags',
    'all_reviews_count'
]

def clean_parquet_file():
    """
    Читает исходный Parquet файл, удаляет строки с неполными данными
    и сохраняет результат в новый Parquet файл.
    """
    print(f"Начинаю очистку файла '{SOURCE_FILE}'...")
    
    try:
        # Загружаем данные
        df = pd.read_parquet(SOURCE_FILE)
        initial_rows = len(df)
        print(f"Загружено {initial_rows} строк.")

        # --- Этап 1: Удаление строк с отсутствующими значениями ---
        # --- Этап 1: Удаление строк с отсутствующими значениями ---
        # Удаляем строки, где 'title', 'tags' или 'all_reviews_count' не заполнены
        df.dropna(subset=['title', 'tags', 'all_reviews_count'], inplace=True)

        final_rows = len(df)
        removed_rows = initial_rows - final_rows

        print("-" * 30)
        print("Очистка успешно завершена!")
        print(f"Удалено {removed_rows} строк.")
        print(f"Итоговое количество строк: {final_rows}.")
        
        # Сохраняем очищенный DataFrame
        df.to_parquet(TARGET_FILE, index=False)
        print(f"Новый файл сохранен как '{TARGET_FILE}'.")
        print("-" * 30)

    except FileNotFoundError:
        print(f"Ошибка: Исходный файл '{SOURCE_FILE}' не найден.")
    except Exception as e:
        print(f"Произошла ошибка во время очистки: {e}")

if __name__ == '__main__':
    clean_parquet_file()