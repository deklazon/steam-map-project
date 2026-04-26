import duckdb
import os

# Имя вашего CSV файла
csv_file_name = 'games_joined.csv'
# Имя файла, в который мы сохраним данные
parquet_file_name = 'steam_games.parquet'

# Проверяем, существует ли CSV-файл
if not os.path.exists(csv_file_name):
    print(f"Ошибка: Файл '{csv_file_name}' не найден.")
    print("Пожалуйста, убедитесь, что файл находится в той же директории, что и скрипт, или укажите правильный путь.")
else:
    try:
        # Устанавливаем соединение с DuckDB (файл базы данных будет временным, в памяти)
        con = duckdb.connect(database=':memory:', read_only=False)
        
        # Используем DuckDB для чтения CSV и записи в Parquet
        # Эта операция очень эффективна по памяти
        print(f"Начинаю конвертацию файла '{csv_file_name}' в '{parquet_file_name}'...")
        
        # Создаем SQL-запрос для чтения CSV и экспорта в Parquet
        query = f"COPY (SELECT * FROM read_csv_auto('{csv_file_name}')) TO '{parquet_file_name}' (FORMAT PARQUET);"
        
        # Выполняем запрос
        con.execute(query)
        
        print("Конвертация успешно завершена!")
        print(f"Ваши данные теперь находятся в файле '{parquet_file_name}'.")

    except Exception as e:
        print(f"Произошла ошибка во время конвертации: {e}")
    finally:
        # Закрываем соединение
        if 'con' in locals():
            con.close()
