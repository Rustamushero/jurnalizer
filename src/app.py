import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

# --- Настройки ---
# Путь к базе данных относительно корня проекта
DB_FILE = "database/journals.db"
st.set_page_config(page_title="Поиск журналов ВАК", layout="wide")


# --- Функции для работы с данными (с кэшированием) ---

@st.cache_data
def convert_df_to_csv(df):
    """Конвертирует DataFrame в CSV с кодировкой UTF-8."""
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def get_all_specialties():
    """
    Загружает все специальности из базы данных для выпадающего списка.
    Возвращает список строк формата "Код - Название".
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT code, name FROM specialties ORDER BY code")
        # Форматируем в "Код - Название" для удобства пользователя
        specialties_list = [f"{code} - {name}" for code, name in cursor.fetchall()]
        conn.close()
        return specialties_list
    except sqlite3.Error:
        return []

@st.cache_data
def find_journals_by_specialty(specialty_code):
    """
    Находит все журналы по указанному коду специальности.
    Возвращает pandas DataFrame.
    """
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT
            j.title,
            j.issn,
            j.vak_category,
            j.scopus_indexed
        FROM
            journals j
        JOIN
            journal_specialties js ON j.id = js.journal_id
        JOIN
            specialties s ON js.specialty_id = s.id
        WHERE
            s.code = ?
        ORDER BY
            j.title;
    """
    df = pd.read_sql_query(query, conn, params=(specialty_code,))
    conn.close()
    return df


# --- Боковая панель (Sidebar) ---
# st.sidebar.markdown("""
# ### Jurnalizer
# ... (весь текст закомментирован или удален)
# """)


# --- Основная часть приложения ---

# Создаем информационный блок вверху страницы
st.markdown(
    """
    <div style="background-color: #e8f0fe; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    
    ### Jurnalizer
    Интерактивный инструмент для поиска и анализа журналов из перечня ВАК.

    **Автор:** Рустам Назипов  
    По вопросам и предложениям, а также при обнаружении неточностей, пожалуйста, пишите в [Telegram](https://t.me/rustamnazipov).

    ---

    **Приложение позволяет осуществлять быстрый поиск по актуальной базе данных научных журналов и предоставляет следующую информацию:**
    - **Категория ВАК:** Отображение присвоенной категории (К1, К2, К3). Если категория не определена однозначно, ставится пометка "К?".
    - **Индексация в Scopus:** Проверка наличия журнала в активном списке Scopus.

    **Актуальность данных:**
    - **Перечень ВАК РФ:** Редакция, использованная при последнем обновлении базы.
    - **Scopus:** Список активных журналов по состоянию на июнь 2025 г.
    
    </div>
    """,
    unsafe_allow_html=True
)


# Проверяем, существует ли файл базы данных
if not Path(DB_FILE).exists():
    st.error(f"❌ **Ошибка:** Файл базы данных '{DB_FILE}' не найден. Приложение не может запуститься.")
    st.info("Пожалуйста, убедитесь, что база данных создана и находится в той же папке, что и приложение.")
else:
    # Загружаем специальности для выпадающего списка
    specialties = get_all_specialties()

    if not specialties:
        st.warning("В базе данных не найдено ни одной специальности. Невозможно выполнить поиск.")
    else:
        # Создаем выпадающий список с возможностью поиска
        placeholder = "-- Выберите специальность из списка или начните вводить код/название --"
        options = [placeholder] + specialties
        
        selected_option = st.selectbox(
            "Научная специальность:",
            options,
            help="Начните вводить код (например, '1.2.1') или ключевое слово из названия (например, 'Анатомия'), чтобы отфильтровать список."
        )

        # Если пользователь выбрал специальность (а не placeholder)
        if selected_option != placeholder:
            # Извлекаем код из выбранной строки "Код - Название"
            selected_code = selected_option.split(' - ')[0]

            # Ищем журналы и выводим результаты
            results_df = find_journals_by_specialty(selected_code)

            st.markdown("---") # Разделитель

            if results_df.empty:
                st.info("ℹ️ По данной специальности журналы в базе не найдены.")
            else:
                st.success(f"✅ Найдено **{len(results_df)}** журнал(ов).")

                # --- Форматирование данных для отображения ---
                # Переименовываем колонки для наглядности
                results_df.rename(columns={
                    'title': 'Название журнала',
                    'issn': 'ISSN',
                    'vak_category': 'Категория ВАК',
                    'scopus_indexed': 'В Scopus'
                }, inplace=True)
                
                # Заменяем значения для лучшего восприятия
                results_df['В Scopus'] = results_df['В Scopus'].apply(lambda x: 'Да' if x == 1 else 'Нет')
                results_df['Категория ВАК'] = results_df['Категория ВАК'].fillna('Нет данных')
                
                # Выводим DataFrame как интерактивную таблицу
                st.dataframe(results_df, use_container_width=True)

                # --- Кнопка для скачивания ---
                csv_data = convert_df_to_csv(results_df)

                st.download_button(
                   label="📥 Скачать результаты в CSV",
                   data=csv_data,
                   file_name=f'jurnalizer_{selected_code}.csv',
                   mime='text/csv',
                ) 