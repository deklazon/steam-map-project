from fastapi import FastAPI
import pandas as pd

# --- Глобальные переменные ---
PARQUET_FILE = 'games_with_coords.parquet'
app = FastAPI(
    title="Steam Games API",
    description="API для получения данных об играх из Steam.",
    version="0.1.0"
)

# --- Кэширование данных ---
# Загружаем данные один раз при старте приложения, чтобы не читать файл при каждом запросе
try:
    games_data = pd.read_parquet(PARQUET_FILE)
    # Сразу обработаем NaN, чтобы не делать это при каждом запросе
    games_data = games_data.replace({pd.NA: None, float('nan'): None})
    # Конвертируем колонки с датами в строки
    for col in ['release_date', 'latest_review_date', 'latest_followers_recorded_at']:
        if col in games_data.columns:
            games_data[col] = games_data[col].astype(str)

except FileNotFoundError:
    print(f"КРИТИЧЕСКАЯ ОШИБКА: Файл с данными '{PARQUET_FILE}' не найден. API не сможет возвращать данные.")
    games_data = pd.DataFrame()


# --- Маршруты API (Endpoints) ---
@app.get("/api/v1/games")
def get_games(limit: int = 10, offset: int = 0):
    """
    Возвращает список игр с пагинацией.
    - **limit**: Количество записей для возврата.
    - **offset**: Смещение (количество записей для пропуска).
    """
    if games_data.empty:
        return {"error": "Данные не загружены на сервере."}
    
    # Применяем пагинацию к загруженному DataFrame
    paginated_df = games_data.iloc[offset : offset + limit]
    
    return paginated_df.to_dict(orient='records')

@app.get("/")
def read_root():
    """
    Корневой маршрут, который предоставляет базовую информацию об API.
    """
    return {"message": "Добро пожаловать в Steam Games API. Используйте /docs для просмотра документации."}
