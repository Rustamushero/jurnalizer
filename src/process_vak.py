import pdfplumber
import re
import sqlite3
import os

DB_FILE = 'database/journals.db'
VAK_LISK_FILE = 'data/vak_lisk.pdf'

def get_db_connection():
    """Возвращает соединение с базой данных."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def clean_text(text):
    """Очищает текст от лишних пробелов и переносов строк."""
    if text is None:
        return ""
    return ' '.join(text.split())

def parse_specialties(text):
    """Извлекает специальности из строки, используя поиск всех совпадений."""
    if not text:
        return []

    # Паттерн для поиска кода и следующего за ним названия.
    # Код: \d{1,2}(?:\.\d{1,2}){1,3}
    # Название: .*? - любое количество символов (нежадный поиск)
    # до тех пор, пока не встретится следующий код (через позитивный просмотр вперед)
    # или до конца строки.
    pattern = re.compile(r'(\d{1,2}(?:\.\d{1,2}){1,3})\s*–?\s*(.*?)(?=\s*\d{1,2}(?:\.\d{1,2}){1,3}\s*–?|$)')

    specialties = []
    for match in pattern.finditer(text):
        code, name = match.groups()
        cleaned_name = clean_text(name).strip(',').strip()
        if cleaned_name:
            specialties.append({
                "code": clean_text(code).strip('.'), # Удаляем точки на конце, если есть
                "name": cleaned_name
            })
            
    return specialties

def process_and_load_vak_lisk():
    """
    Извлекает данные из vak_lisk.pdf, обрабатывает их и загружает в базу данных.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        with pdfplumber.open(VAK_LISK_FILE) as pdf:
            current_journal_data = {}

            for page in pdf.pages:
                table = page.extract_table()
                if not table:
                    continue

                for row in table:
                    # Проверяем, начинается ли строка с номера (например, "1.", "123.")
                    is_new_journal_entry = row[0] and re.match(r'^\d+\.', clean_text(row[0]))

                    if is_new_journal_entry:
                        # Если это новая запись, сохраняем предыдущий журнал (если он был)
                        if current_journal_data:
                            load_journal_to_db(cursor, current_journal_data)
                        
                        # Начинаем собирать данные для нового журнала
                        title = clean_text(row[1])
                        issn = clean_text(row[2]).replace('-', '')
                        specialties_text = clean_text(row[3])
                        
                        current_journal_data = {
                            "title": title,
                            "issn": issn,
                            "specialties": parse_specialties(specialties_text)
                        }
                    elif current_journal_data and (row[3] or row[4]):
                        # Если это продолжение предыдущей записи, добавляем специальности
                        additional_specialties_text = clean_text(row[3])
                        current_journal_data["specialties"].extend(parse_specialties(additional_specialties_text))

            # Сохраняем последний журнал в файле
            if current_journal_data:
                load_journal_to_db(cursor, current_journal_data)

        conn.commit()
        print("Данные из 'vak_lisk.pdf' успешно загружены в базу данных.")

    except Exception as e:
        conn.rollback()
        print(f"Произошла ошибка при загрузке данных: {e}")
    finally:
        conn.close()

def load_journal_to_db(cursor, journal_data):
    """Загружает данные одного журнала в базу данных."""
    try:
        # 1. Добавляем журнал в таблицу journals
        cursor.execute("INSERT INTO journals (title, issn) VALUES (?, ?)", 
                       (journal_data["title"], journal_data["issn"]))
        journal_id = cursor.lastrowid

        # 2. Обрабатываем специальности
        for spec in journal_data["specialties"]:
            # Проверяем, есть ли уже такая специальность
            cursor.execute("SELECT id FROM specialties WHERE code = ?", (spec["code"],))
            result = cursor.fetchone()
            
            if result:
                specialty_id = result[0]
            else:
                # Если нет, добавляем новую специальность
                cursor.execute("INSERT INTO specialties (code, name) VALUES (?, ?)", 
                               (spec["code"], spec["name"]))
                specialty_id = cursor.lastrowid
            
            # 3. Создаем связь в journal_specialties
            cursor.execute("INSERT OR IGNORE INTO journal_specialties (journal_id, specialty_id) VALUES (?, ?)",
                           (journal_id, specialty_id))
    except sqlite3.IntegrityError as e:
        print(f"Ошибка целостности данных для журнала '{journal_data['title']}': {e}")
    except Exception as e:
        print(f"Не удалось загрузить журнал '{journal_data['title']}': {e}")


if __name__ == '__main__':
    # Перед запуском этого скрипта убедитесь, что база данных
    # создана с помощью create_db.py
    process_and_load_vak_lisk() 