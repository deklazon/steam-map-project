import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import datetime


# --- Настройки страницы ---
st.set_page_config(
    page_title="Карта Игр Steam",
    page_icon="🗺️",
    layout="wide"
)

# --- Константы ---
DATA_FILE = 'games_with_coords.parquet'

# --- Загрузка данных ---
@st.cache_data
def load_data():
    """
    Загружает все данные по играм из локального файла.
    Кэширование не будет перезагружать данные при каждом действии пользователя.
    """
    try:
        df = pd.read_parquet(DATA_FILE)
        # Убираем игры, для которых не удалось рассчитать координаты
        df.dropna(subset=['x', 'y'], inplace=True)
        return df
    except FileNotFoundError:
        st.error(f"Файл с данными '{DATA_FILE}' не найден.")
        return pd.DataFrame()

# Загрузка данных
games_df = load_data()

if not games_df.empty:
    st.sidebar.title("Фильтры")

    # --- Подготовка данных ---
    games_df['display_tags'] = games_df['tags'].str.replace('_', ' ').str.replace(',', ', ')
    games_df['log_reviews'] = np.log10(games_df['all_reviews_count'] + 1)
    games_df['release_date'] = pd.to_datetime(games_df['release_date'], errors='coerce')
    games_df.dropna(subset=['release_date'], inplace=True)
    
    # --- Фильтры ---
    # 0 Фильтры бесполезного
    zeo_review_count = games_df.query('all_reviews_count == 0').shape[0]
    if zeo_review_count:
        show_zero_review = st.sidebar.checkbox("Учитывать 0 отзывов", help=f"{zeo_review_count} игр", value=False)
        if not show_zero_review:
            games_df = games_df.query('all_reviews_count > 0')

    late_release_count = games_df.query('release_date > datetime.datetime.now()').shape[0]
    if late_release_count:
        show_late_releases = st.sidebar.checkbox("Учитывать релизы после " + datetime.datetime.now().strftime("%Y-%m-%d"), help=f"{late_release_count} игр", value=False)
        if not show_late_releases:
            games_df = games_df.query('release_date <= datetime.datetime.now()')

    st.sidebar.text(f"Всего игр: {games_df.shape[0]}")

    # 1. Фильтр по названию игры (для выделения)
    sorted_game_names = sorted(games_df['title'].unique())
    selected_game = st.sidebar.selectbox("Найти и выделить игру:", options=[""] + sorted_game_names, index=0)

    # 2. Фильтр по тегам
    all_tags_internal = set()
    games_df['tags'].str.split(',').apply(all_tags_internal.update)
    tag_display_map = {tag.replace('_', ' '): tag for tag in all_tags_internal if tag}
    sorted_display_tags = sorted(tag_display_map.keys())
    selected_display_tags = st.sidebar.multiselect("Теги:", options=sorted_display_tags)

    # 3. Фильтр по дате релиза
    min_date, max_date = games_df['release_date'].min().to_pydatetime(), games_df['release_date'].max().to_pydatetime()
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Дата релиза от:", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("Дата релиза до:", value=max_date, min_value=min_date, max_value=max_date)
    start_date, end_date = pd.to_datetime(start_date), pd.to_datetime(end_date)

    # 4. Фильтр по цене
    min_price, max_price = games_df['original_price'].min(), games_df['original_price'].max()
    col1, col2 = st.sidebar.columns(2)
    with col1:
        price_from = st.number_input("Цена от ($):", min_value=min_price, max_value=max_price, value=min_price)
    with col2:
        price_to = st.number_input("Цена до ($):", min_value=min_price, max_value=max_price, value=max_price)

    # 5. Фильтр по количеству отзывов
    # 5.1 Выбор режима фильтрации
    filter_mode_names = ["По кол-ву", "По % отзывов",]
    review_filter_mode = st.sidebar.radio(
        "Фильтр отзывов",
        list(range(len(filter_mode_names))),
        format_func=lambda v: {i: s for i, s in enumerate(filter_mode_names)}[v],
        index = 0,
        captions=[
            "Точное количество отзывов",
            "Например, топ 50% по отзывам",
        ],
    )

    min_reviews, max_reviews = int(games_df['all_reviews_count'].min()), int(games_df['all_reviews_count'].max())
    reviews_from = min_reviews
    reviews_to = max_reviews
    if review_filter_mode == 0:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            reviews_from = st.number_input("Отзывов от:", min_value=min_reviews, max_value=max_reviews, value=500)
        with col2:
            reviews_to = st.number_input("Отзывов до:", min_value=min_reviews, max_value=max_reviews, value=max_reviews)
    elif review_filter_mode == 1:
        reviews_slider_percent = st.sidebar.slider("% отзывов", min_value=0.0, max_value=100.0, value=(90.0, 100.0))
        reviews_from = games_df['all_reviews_count'].quantile(reviews_slider_percent[0] / 100)
        reviews_to = games_df['all_reviews_count'].quantile(reviews_slider_percent[1] / 100)

    # --- Применение фильтров ---
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

    show_grey_filtered = st.sidebar.checkbox(f"Показывать серым не попавшие в фильтр ({final_mask.shape[0] - final_mask.sum()} точек)", help="Слишком много точек для отображения - тяжёлая операция", value=False)
    st.sidebar.text(f"Активных точек графика: {final_mask.sum()}")

    # Определяем прозрачность на основе итоговой маски
    games_df['opacity'] = np.where(final_mask, 1.0, 0.03)

    # --- Логика выделения выбранной игры ---
    if selected_game:
        games_df['size'] = np.where(games_df['title'] == selected_game, 12, 6)
        games_df['line_color'] = np.where(games_df['title'] == selected_game, 'red', 'rgba(0,0,0,0)')
        games_df['line_width'] = np.where(games_df['title'] == selected_game, 2, 0)
        games_df.loc[games_df['title'] == selected_game, 'opacity'] = 1.0
    else:
        games_df['size'] = 6
        games_df['line_color'] = 'rgba(0,0,0,0)'
        games_df['line_width'] = 0

    games_df['sort_order'] = np.where(games_df['title'] == selected_game, 2, games_df['opacity'])
    games_df = games_df.sort_values(by=['sort_order', 'release_date'])

    # --- Создание интерактивного графика ---
    visible_games = games_df[games_df['opacity'] == 1.0]
    background_games = games_df[games_df['opacity'] < 1.0]

    fig = go.Figure()

    # 1. Добавляем фоновые точки (без hover-информации) с WebGL
    if show_grey_filtered:
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
        dragmode='pan',
        barmode='overlay',
        showlegend=False,
        height=1200
    )

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
    st.plotly_chart(fig, width='stretch')

else:
    st.warning("Не удалось загрузить данные для отображения карты.")
