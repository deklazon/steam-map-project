import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- Настройки страницы ---
st.set_page_config(
    page_title="Карта Игр Steam",
    page_icon="🗺️",
    layout="wide"
)

# --- Константы ---
# Запрашиваем большое количество игр, чтобы получить всю базу
# API вернет столько, сколько есть, если их меньше
API_BASE_URL = "https://steam-map-project.onrender.com/api/v1/games"

# --- Подключение к данным ---
@st.cache_data
def load_data_from_api():
    """
    Загружает все данные по играм из нашего API, используя пагинацию,
    чтобы избежать таймаутов на больших объемах данных.
    Кэширование не будет перезагружать данные при каждом действии пользователя.
    """
    all_games = []
    offset = 0
    limit = 5000  # Загружаем по 5000 игр за раз
    
    with st.spinner("Загрузка данных об играх... Это может занять некоторое время."):
        while True:
            try:
                # Формируем URL с пагинацией
                paginated_url = f"{API_BASE_URL}?limit={limit}&offset={offset}"
                
                # Устанавливаем разумный таймаут для одного чанка
                response = requests.get(paginated_url, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                
                # Если API вернул пустой список, значит, мы загрузили все данные
                if not data:
                    break
                
                all_games.extend(data)
                offset += limit
                
            except requests.exceptions.RequestException as e:
                st.error(f"Не удалось подключиться к API: {e}. Убедитесь, что FastAPI сервер запущен.")
                return pd.DataFrame()

    if not all_games:
        return pd.DataFrame()

    df = pd.DataFrame(all_games)
    # Убираем игры, для которых не удалось рассчитать координаты
    df.dropna(subset=['x', 'y'], inplace=True)
    return df

# --- Основная часть приложения ---
# Загрузка данных
games_df = load_data_from_api()

if not games_df.empty:
    st.sidebar.title("Фильтры")

    # --- Подготовка данных ---
    # --- Подготовка данных для отображения ---
    # Создаем читаемые теги
    games_df['display_tags'] = games_df['tags'].str.replace('_', ' ').str.replace(',', ', ')
    games_df['log_reviews'] = np.log10(games_df['all_reviews_count'] + 1)
    # Преобразуем дату релиза в datetime для корректной сортировки
    games_df['release_date'] = pd.to_datetime(games_df['release_date'], errors='coerce')
    # Убираем строки с некорректными датами, если они есть
    games_df.dropna(subset=['release_date'], inplace=True)
    
    # --- Фильтры ---
    # 1. Фильтр по названию игры (для выделения)
    sorted_game_names = sorted(games_df['title'].unique())
    selected_game = st.sidebar.selectbox("Найти и выделить игру:", options=[""] + sorted_game_names, index=0)

    # 2. Фильтр по тегам
    all_tags_internal = set()
    games_df['tags'].str.split(',').apply(all_tags_internal.update)
    tag_display_map = {tag.replace('_', ' '): tag for tag in all_tags_internal if tag}
    sorted_display_tags = sorted(tag_display_map.keys())
    selected_display_tags = st.sidebar.multiselect("Теги:", options=sorted_display_tags)

    # 2. Фильтр по дате релиза
    min_date, max_date = games_df['release_date'].min().to_pydatetime(), games_df['release_date'].max().to_pydatetime()
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Дата релиза от:", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("Дата релиза до:", value=max_date, min_value=min_date, max_value=max_date)
    start_date, end_date = pd.to_datetime(start_date), pd.to_datetime(end_date)

    # 3. Фильтр по цене
    min_price, max_price = games_df['original_price'].min(), games_df['original_price'].max()
    col1, col2 = st.sidebar.columns(2)
    with col1:
        price_from = st.number_input("Цена от ($):", min_value=min_price, max_value=max_price, value=min_price)
    with col2:
        price_to = st.number_input("Цена до ($):", min_value=min_price, max_value=max_price, value=max_price)

    # 4. Фильтр по количеству отзывов
    min_reviews, max_reviews = int(games_df['all_reviews_count'].min()), int(games_df['all_reviews_count'].max())
    col1, col2 = st.sidebar.columns(2)
    with col1:
        reviews_from = st.number_input("Отзывов от:", min_value=min_reviews, max_value=max_reviews, value=min_reviews)
    with col2:
        reviews_to = st.number_input("Отзывов до:", min_value=min_reviews, max_value=max_reviews, value=max_reviews)

    # --- Применение фильтров ---
    # Начинаем с того, что все игры видимы
    final_mask = pd.Series(True, index=games_df.index)

    # Применяем фильтр по тегам
    if selected_display_tags:
        selected_internal_tags = [tag_display_map[tag] for tag in selected_display_tags]
        tags_mask = games_df['tags'].apply(lambda ts: all(tag in ts.split(',') for tag in selected_internal_tags))
        final_mask &= tags_mask

    # Применяем фильтр по дате
    date_mask = (games_df['release_date'] >= start_date) & (games_df['release_date'] <= end_date)
    final_mask &= date_mask

    # Применяем фильтр по цене
    price_mask = (games_df['original_price'] >= price_from) & (games_df['original_price'] <= price_to)
    final_mask &= price_mask

    # Применяем фильтр по отзывам
    reviews_mask = (games_df['all_reviews_count'] >= reviews_from) & (games_df['all_reviews_count'] <= reviews_to)
    final_mask &= reviews_mask

    # Определяем прозрачность на основе итоговой маски
    games_df['opacity'] = np.where(final_mask, 1.0, 0.03)

    # --- Логика выделения выбранной игры ---
    if selected_game:
        # Увеличиваем размер и добавляем контур для выбранной игры
        games_df['size'] = np.where(games_df['title'] == selected_game, 12, 6)
        games_df['line_color'] = np.where(games_df['title'] == selected_game, 'red', 'rgba(0,0,0,0)')
        games_df['line_width'] = np.where(games_df['title'] == selected_game, 2, 0)
        # Повышаем прозрачность выбранной игры, если она попала в фон
        games_df.loc[games_df['title'] == selected_game, 'opacity'] = 1.0
    else:
        # Стандартные значения, если игра не выбрана
        games_df['size'] = 6
        games_df['line_color'] = 'rgba(0,0,0,0)'
        games_df['line_width'] = 0

    # Сортируем так, чтобы выделенная игра и видимые точки были наверху
    games_df['sort_order'] = np.where(games_df['title'] == selected_game, 2, games_df['opacity'])
    games_df = games_df.sort_values(by=['sort_order', 'release_date'])

    # --- Создание интерактивного графика ---
    # Разделяем данные на видимые и фоновые для разных trace
    visible_games = games_df[games_df['opacity'] == 1.0]
    background_games = games_df[games_df['opacity'] < 1.0]

    # Создаем пустую фигуру
    # Создаем фигуру с рендерингом через WebGL для производительности
    fig = go.Figure()

    # 1. Добавляем фоновые точки (без hover-информации) с WebGL
    fig.add_trace(go.Scattergl(
        x=background_games['x'],
        y=background_games['y'],
        mode='markers',
        marker=dict(
            color=background_games['log_reviews'],
            colorscale=px.colors.sequential.Viridis,
            opacity=0.03,
            size=background_games['size'],
            cmin=games_df['log_reviews'].min(),
            cmax=games_df['log_reviews'].max(),
            showscale=False
        ),
        hoverinfo='none',
        showlegend=False
    ))

    # 2. Добавляем видимые точки (с hover-информацией)
    # 2. Добавляем видимые точки (с hover-информацией) с WebGL для производительности
    fig.add_trace(go.Scattergl(
        x=visible_games['x'],
        y=visible_games['y'],
        customdata=visible_games[['display_tags', 'all_reviews_count']],
        mode='markers',
        marker=dict(
            color=visible_games['log_reviews'],
            colorscale=px.colors.sequential.Viridis,
            opacity=1.0,
            size=visible_games['size'],
            cmin=games_df['log_reviews'].min(),
            cmax=games_df['log_reviews'].max(),
            colorbar=dict(title="Отзывы (log10)"),
            line=dict(
                color=visible_games['line_color'],
                width=visible_games['line_width']
            )
        ),
        hovertemplate="<b>%{text}</b><br><br>" +
                      "Теги: %{customdata[0]}<br>" +
                      "Отзывы: %{customdata[1]}<extra></extra>",
        text=visible_games['title'],
        showlegend=False
    ))

    # Обновляем общие настройки layout
    fig.update_layout(
        title="2D-проекция игрового пространства Steam",
        xaxis_title=None,
        yaxis_title=None,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1,
        ),
        # Убираем фиксированную высоту, чтобы карта занимала все доступное пространство
        dragmode='pan',
        # Отключаем смешивание цветов. Верхняя точка полностью перекрывает нижнюю.
        barmode='overlay',
        showlegend=False,
        height=1200 # Увеличиваем фиксированную высоту для графика
    )

    # --- Стилизация и отображение ---
    # CSS для корректных отступов
    st.markdown("""
        <style>
            /* Убираем лишние отступы у основного блока */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                padding-left: 2rem;
                padding-right: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)

    # Отображение графика в Streamlit
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Не удалось загрузить данные для отображения карты.")
