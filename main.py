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
def load_all_data_in_chunks():
    """
    Загружает все данные с API по частям (пагинация), чтобы избежать таймаутов
    при работе с большими объемами данных. Показывает прогресс-бар.
    """
    all_data = []
    offset = 0
    chunk_size = 10000  # Запрашиваем по 10 000 игр за раз

    with st.spinner("Загрузка данных об играх... Это может занять некоторое время."):
        progress_bar = st.progress(0, text="Начинаем загрузку...")
        total_games_loaded = 0

        while True:
            try:
                # Формируем URL с пагинацией
                paginated_url = f"{API_BASE_URL}?limit={chunk_size}&offset={offset}"
                response = requests.get(paginated_url, timeout=60) # Увеличиваем таймаут на всякий случай
                response.raise_for_status()
                
                chunk = response.json()
                
                # Если API вернул пустой список, значит, мы загрузили все данные
                if not chunk:
                    progress_bar.progress(1.0, text="Загрузка завершена!")
                    break
                
                all_data.extend(chunk)
                total_games_loaded += len(chunk)
                
                # Обновляем прогресс-бар (это примерная оценка, т.к. мы не знаем общего числа)
                # Просто показываем, что процесс идет
                progress_bar.progress(min(1.0, (offset + chunk_size) / 150000), text=f"Загружено {total_games_loaded} игр...")

                offset += chunk_size

            except requests.exceptions.RequestException as e:
                st.error(f"Не удалось подключиться к API: {e}. Убедитесь, что FastAPI сервер запущен.")
                return pd.DataFrame()

    # Вместо создания большого DataFrame, просто отфильтруем "сырой" список
    filtered_data = [item for item in all_data if item.get('x') is not None and item.get('y') is not None]
    return filtered_data

# --- Основная часть приложения ---
# Загрузка данных
games_df = load_all_data_in_chunks()

if games_df: # games_df теперь это список словарей
    st.sidebar.title("Фильтры")

    # --- Преобразуем "сырые" данные в DataFrame только для расчетов ---
    # Это все равно будет занимать память, но мы можем это оптимизировать позже,
    # если это останется проблемой. Основная проблема была в создании DataFrame из ВСЕХ данных.
    df_for_calcs = pd.DataFrame(games_df)
    df_for_calcs['release_date'] = pd.to_datetime(df_for_calcs['release_date'], errors='coerce')
    df_for_calcs.dropna(subset=['release_date'], inplace=True)
    
    # --- Фильтры ---
    # 1. Фильтр по названию игры (для выделения)
    sorted_game_names = sorted(df_for_calcs['title'].unique())
    selected_game = st.sidebar.selectbox("Найти и выделить игру:", options=[""] + sorted_game_names, index=0)

    # 2. Фильтр по тегам
    all_tags_internal = set()
    df_for_calcs['tags'].dropna().str.split(',').apply(all_tags_internal.update)
    tag_display_map = {tag.replace('_', ' '): tag for tag in all_tags_internal if tag}
    sorted_display_tags = sorted(tag_display_map.keys())
    selected_display_tags = st.sidebar.multiselect("Теги:", options=sorted_display_tags)

    # 2. Фильтр по дате релиза
    min_date, max_date = df_for_calcs['release_date'].min().to_pydatetime(), df_for_calcs['release_date'].max().to_pydatetime()
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Дата релиза от:", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("Дата релиза до:", value=max_date, min_value=min_date, max_value=max_date)
    start_date, end_date = pd.to_datetime(start_date), pd.to_datetime(end_date)

    # 3. Фильтр по цене
    # Убедимся, что колонка с ценой числовая
    df_for_calcs['original_price'] = pd.to_numeric(df_for_calcs['original_price'], errors='coerce').fillna(0)
    min_price, max_price = df_for_calcs['original_price'].min(), df_for_calcs['original_price'].max()
    col1, col2 = st.sidebar.columns(2)
    with col1:
        price_from = st.number_input("Цена от ($):", min_value=float(min_price), max_value=float(max_price), value=float(min_price))
    with col2:
        price_to = st.number_input("Цена до ($):", min_value=float(min_price), max_value=float(max_price), value=float(max_price))

    # 4. Фильтр по количеству отзывов
    df_for_calcs['all_reviews_count'] = pd.to_numeric(df_for_calcs['all_reviews_count'], errors='coerce').fillna(0)
    min_reviews, max_reviews = int(df_for_calcs['all_reviews_count'].min()), int(df_for_calcs['all_reviews_count'].max())
    col1, col2 = st.sidebar.columns(2)
    with col1:
        reviews_from = st.number_input("Отзывов от:", min_value=min_reviews, max_value=max_reviews, value=min_reviews)
    with col2:
        reviews_to = st.number_input("Отзывов до:", min_value=min_reviews, max_value=max_reviews, value=max_reviews)

    # --- Применение фильтров (теперь на списке словарей) ---
    filtered_games = []
    for game in games_df:
        # Пропускаем игры с неполными данными
        if not all(k in game and game[k] is not None for k in ['release_date', 'original_price', 'all_reviews_count', 'tags']):
            continue

        # Фильтр по дате
        try:
            game_date = pd.to_datetime(game['release_date'])
            if not (start_date <= game_date <= end_date):
                continue
        except (ValueError, TypeError):
            continue

        # Фильтр по цене
        if not (price_from <= game['original_price'] <= price_to):
            continue
        
        # Фильтр по отзывам
        if not (reviews_from <= game['all_reviews_count'] <= reviews_to):
            continue

        # Фильтр по тегам
        if selected_display_tags:
            selected_internal_tags = {tag_display_map[tag] for tag in selected_display_tags}
            game_tags = set(game['tags'].split(','))
            if not selected_internal_tags.issubset(game_tags):
                continue
        
        filtered_games.append(game)

    # --- Подготовка данных для графика ---
    plot_df = pd.DataFrame(filtered_games) if filtered_games else pd.DataFrame()
    
    if not plot_df.empty:
        plot_df['log_reviews'] = np.log10(plot_df['all_reviews_count'] + 1)
        plot_df['display_tags'] = plot_df['tags'].str.replace('_', ' ').str.replace(',', ', ')

        # --- Логика выделения ---
        if selected_game:
            plot_df['size'] = np.where(plot_df['title'] == selected_game, 12, 6)
            plot_df['line_color'] = np.where(plot_df['title'] == selected_game, 'red', 'rgba(0,0,0,0)')
            plot_df['line_width'] = np.where(plot_df['title'] == selected_game, 2, 0)
        else:
            plot_df['size'] = 6
            plot_df['line_color'] = 'rgba(0,0,0,0)'
            plot_df['line_width'] = 0

        # --- Создание интерактивного графика ---
        fig = go.Figure()
        fig.add_trace(go.Scattergl(
            x=plot_df['x'],
            y=plot_df['y'],
            customdata=plot_df[['display_tags', 'all_reviews_count']],
            mode='markers',
            marker=dict(
                color=plot_df['log_reviews'],
                colorscale=px.colors.sequential.Viridis,
                opacity=1.0,
                size=plot_df['size'],
                colorbar=dict(title="Отзывы (log10)"),
                line=dict(
                    color=plot_df['line_color'],
                    width=plot_df['line_width']
                )
            ),
            hovertemplate="<b>%{text}</b><br><br>" +
                          "Теги: %{customdata[0]}<br>" +
                          "Отзывы: %{customdata[1]}<extra></extra>",
            text=plot_df['title'],
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
