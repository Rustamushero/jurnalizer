import pdfplumber
import pprint
import sqlite3
import re
from thefuzz import fuzz, process
import csv
import os

DB_FILE = 'database/journals.db'
VAK_K_FILE = 'data/vak_k.pdf'
REPORT_FILE = 'matching_report.csv'

def clean_text(text):
    """Очищает текст от лишних пробелов и переносов строк."""
    if text is None:
        return ""
    return ' '.join(text.split())

def normalize_title(title):
    """Приводит название к единому формату для сопоставления."""
    return re.sub(r'[\W_]+', '', title.lower())

def get_journals_from_db():
    """Загружает все журналы (id, title) из базы данных."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM journals")
            return {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.Error as e:
        print(f"❌ Ошибка доступа к базе данных: {e}")
        return {}

def extract_categories_from_pdf():
    """Извлекает {'title': '...', 'category': '...'} из PDF."""
    extracted_data = []
    try:
        with pdfplumber.open(VAK_K_FILE) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables: continue
                for table in tables:
                    for row in table[1:]:
                        if len(row) >= 4 and row[1] and row[3]:
                            extracted_data.append({"title": clean_text(row[1]), "category": clean_text(row[3])})
        return extracted_data
    except Exception: return []

def update_categories_in_db():
    """
    Основная функция: ищет категории и обновляет их в базе данных.
    Для совпадений >= 99% ставит категорию (К1, К2, К3).
    Для всех остальных ставит 'К?'.
    """
    db_journals = get_journals_from_db()
    pdf_data = extract_categories_from_pdf()

    if not db_journals or not pdf_data:
        print("Не удалось получить данные. Выход.")
        return

    pdf_titles = {item['title']: item['category'] for item in pdf_data}
    pdf_titles_normalized = {normalize_title(title): title for title in pdf_titles.keys()}
    pdf_titles_list = list(pdf_titles.keys())
    
    updates_to_perform = []
    
    # Итерируемся по журналам из БАЗЫ ДАННЫХ
    for db_id, db_title in db_journals.items():
        db_title_normalized = normalize_title(db_title)
        
        category_to_set = "К?" # Значение по умолчанию

        # Этап 1: Точное совпадение
        if db_title_normalized in pdf_titles_normalized:
            original_pdf_title = pdf_titles_normalized[db_title_normalized]
            category_to_set = pdf_titles[original_pdf_title]
        else:
            # Этап 2: Нечеткий поиск, если точного нет
            best_matches = process.extract(db_title, pdf_titles_list, scorer=fuzz.ratio, limit=1)
            if best_matches:
                match_title, score = best_matches[0]
                if score >= 99:
                    category_to_set = pdf_titles[match_title]
        
        updates_to_perform.append((category_to_set, db_id))

    # Шаг 3: Массовое обновление базы данных
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.executemany("UPDATE journals SET vak_category = ? WHERE id = ?", updates_to_perform)
            conn.commit()
            
            # Считаем статистику
            updated_count = len([u for u in updates_to_perform if u[0] != 'К?'])
            question_count = len(updates_to_perform) - updated_count
            
            print("\n--- Обновление базы данных завершено ---")
            print(f"✅ Успешно установлено категорий (К1/К2/К3): {updated_count}")
            print(f"❓ Помечено как 'К?': {question_count}")
            print(f"-------------------------------------------")
            print(f"Итого обработано записей: {len(updates_to_perform)}")

    except sqlite3.Error as e:
        print(f"❌ Ошибка при обновлении базы данных: {e}")


if __name__ == "__main__":
    # Убедимся, что файл БД существует
    if not os.path.exists(DB_FILE):
        print(f"Ошибка: Файл базы данных '{DB_FILE}' не найден.")
    elif not os.path.exists(VAK_K_FILE):
        print(f"Ошибка: Файл с категориями '{VAK_K_FILE}' не найден.")
    else:
        # Получаем список журналов из файла категорий
        category_journals = extract_categories_from_pdf()
        # Обновляем базу данных
        update_categories_in_db() 