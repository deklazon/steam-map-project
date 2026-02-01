import pandas as pd
from umap import UMAP
import numpy as np
from sklearn.preprocessing import normalize
import math

# --- Константы ---
SOURCE_FILE = 'games_cleaned.parquet'
TARGET_FILE = 'games_with_coords.parquet'
EXCLUDED_TAGS = {'Early_Access', 'Free_to_Play', 'Steam_Machine', 'Controller'}


def create_binary_vectors(tags_series):
    """
    Создает бинарные векторы для каждой игры (мешок слов).
    1, если тег присутствует у игры, 0 - в противном случае.
    """
    # get_dummies отлично справляется с этой задачей, создавая бинарную матрицу
    # где строки - это игры, а столбцы - это все уникальные теги.
    binary_matrix = tags_series.str.get_dummies(sep=',')
    
    return binary_matrix.values, binary_matrix.columns.tolist()


def main():
    """
    Основная функция для обработки данных:
    1. Читает данные из Parquet.
    2. Обрабатывает теги.
    3. Создает бинарную матрицу векторов (мешок слов) для каждой игры.
    4. Снижает размерность с помощью UMAP.
    5. Сохраняет результат в новый Parquet файл.
    """
    print("Шаг 1: Чтение данных...")
    try:
        games_df = pd.read_parquet(SOURCE_FILE)
        print(f"Загружено {len(games_df)} игр.")

        # --- Обработка данных ---
        print("Шаг 2: Обработка тегов...")
        # Заменяем пробелы и приводим к единому формату
        games_df['cleaned_tags'] = games_df['tags'].str.replace(' ', '_').str.replace(',_', ',')
        
        # Отфильтровываем игры без тегов
        games_with_tags_df = games_df[games_df['cleaned_tags'].notna() & (games_df['cleaned_tags'] != "")].copy()
        print(f"Найдено {len(games_with_tags_df)} игр с тегами для обработки.")

        if games_with_tags_df.empty:
            print("Ошибка: не найдено ни одной игры с тегами для обработки. Прерывание выполнения.")
            return

        print("Шаг 3: Векторизация тегов (создание бинарной матрицы)...")
        
        # 3.1. Фильтруем теги
        tags_series = games_with_tags_df['cleaned_tags'].apply(
            lambda x: ','.join([tag for tag in x.split(',') if tag not in EXCLUDED_TAGS])
        )
        
        # 3.2. Создаем бинарные векторы
        binary_matrix, all_tags_vocab = create_binary_vectors(tags_series)
        
        # 3.3. Нормализуем векторы (важно для косинусного расстояния)
        normalized_matrix = normalize(binary_matrix, norm='l2', axis=1)

        print("Шаг 4: Снижение размерности (UMAP)...")
        # UMAP хорошо работает с параметрами по умолчанию
        # Используем нормализованную матрицу
        umap_reducer = UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1)
        embedding = umap_reducer.fit_transform(normalized_matrix)

        # Добавляем координаты в DataFrame
        games_with_tags_df['x'] = embedding[:, 0]
        games_with_tags_df['y'] = embedding[:, 1]
        
        # --- Сохранение результата ---
        print(f"Шаг 5: Сохранение результата в '{TARGET_FILE}'...")
        
        # Объединяем результат с исходным DataFrame, чтобы добавить координаты
        # Играм без тегов присвоится NaN в качестве координат
        final_df = pd.merge(games_df, games_with_tags_df[['game_id', 'x', 'y']], on='game_id', how='left')

        # Заменяем исходную колонку 'tags' на очищенную
        final_df['tags'] = final_df['cleaned_tags']
        # Удаляем временную колонку
        final_df = final_df.drop(columns=['cleaned_tags'])
        
        final_df.to_parquet(TARGET_FILE, index=False)
        
        print("-" * 30)
        print("Обработка успешно завершена!")
        print(f"Файл с 2D-координатами сохранен как '{TARGET_FILE}'.")
        print("-" * 30)

    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == '__main__':
    main()