import pandas as pd
import sqlite3
import os

DB_FILE = 'database/journals.db'
SCOPUS_FILE = 'data/scopus_list.xlsx'

def get_db_connection():
    """Возвращает соединение с базой данных."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row # Позволяет обращаться к колонкам по имени
    return conn

def clean_issn(issn):
    """Очищает ISSN от лишних символов и приводит к стандартному виду."""
    if isinstance(issn, str):
        return issn.replace('-', '').strip()
    return None

def get_active_scopus_issns(scopus_file_path):
    """
    Читает XLSX файл Scopus и возвращает множество (set) активных ISSN и EISSN.
    """
    try:
        df = pd.read_excel(scopus_file_path)
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл Scopus не найден по пути {scopus_file_path}")
        return set()

    # Фильтруем, оставляя только активные журналы
    active_journals_df = df[df['Active or Inactive'] == 'Active']

    # Собираем все ISSN и EISSN в одно множество для быстрой проверки
    active_issns = set()
    for issn in active_journals_df['ISSN'].dropna():
        cleaned = clean_issn(issn)
        if cleaned:
            active_issns.add(cleaned)
    
    for eissn in active_journals_df['EISSN'].dropna():
        cleaned = clean_issn(eissn)
        if cleaned:
            active_issns.add(cleaned)
            
    return active_issns

def update_database_with_scopus_data(active_issns):
    """
    Обновляет поле scopus_indexed в базе данных на основе списка активных ISSN.
    """
    if not active_issns:
        print("Список активных ISSN пуст. Обновление базы данных не будет произведено.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Сначала сбрасываем флаг для всех журналов
        cursor.execute("UPDATE journals SET scopus_indexed = 0")
        print(f"Поле 'scopus_indexed' сброшено в 0 для всех записей.")

        # Получаем все журналы из нашей базы
        cursor.execute("SELECT id, issn FROM journals")
        all_journals = cursor.fetchall()

        updated_count = 0
        for journal in all_journals:
            journal_issn = clean_issn(journal['issn'])
            if journal_issn and journal_issn in active_issns:
                cursor.execute("UPDATE journals SET scopus_indexed = 1 WHERE id = ?", (journal['id'],))
                updated_count += 1
        
        conn.commit()
        print(f"✅ Обновление завершено. Найдено и помечено {updated_count} журналов, индексируемых в Scopus.")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"❌ Произошла ошибка при обновлении базы данных: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    print("--- Начинаю обработку файла Scopus и обновление базы данных ---")
    
    if not os.path.exists(DB_FILE):
        print(f"❌ База данных '{DB_FILE}' не найдена. Пожалуйста, создайте ее сначала.")
    elif not os.path.exists(SCOPUS_FILE):
        print(f"❌ Файл '{SCOPUS_FILE}' не найден.")
    else:
        active_issns_set = get_active_scopus_issns(SCOPUS_FILE)
        if active_issns_set:
            print(f"Найдено {len(active_issns_set)} уникальных активных ISSN/EISSN в файле Scopus.")
            update_database_with_scopus_data(active_issns_set)
    
    print("--- Обработка завершена ---") 