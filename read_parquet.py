import pandas as pd

# Устанавливаем опции для полного отображения
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

FILE_TO_READ = 'games_with_coords.parquet'

def read_and_display_parquet():
    """
    Читает указанный Parquet файл, выводит информацию о нем
    и первые несколько строк для демонстрации.
    """
    print(f"Читаю файл '{FILE_TO_READ}'...")
    
    try:
        # Загружаем Parquet файл в DataFrame
        df = pd.read_parquet(FILE_TO_READ)

        # Выводим информацию о столбцах и типах данных
        print("\nИнформация о столбцах и типах данных:")
        df.info(verbose=True, show_counts=True)

        # Выводим первые 5 строк DataFrame
        print(f"\nПервые 5 строк из файла '{FILE_TO_READ}':")
        print(df.head())

    except FileNotFoundError:
        print(f"Ошибка: Файл '{FILE_TO_READ}' не найден.")
    except Exception as e:
        print(f"Произошла ошибка при чтении файла: {e}")

if __name__ == '__main__':
    read_and_display_parquet()