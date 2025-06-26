import sqlite3
import os

DB_FILE = 'database/journals.db'

def check_database_content():
    """
    Проверяет содержимое базы данных: считает записи и выводит примеры.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 1. Считаем количество журналов
        cursor.execute("SELECT COUNT(*) FROM journals")
        journal_count = cursor.fetchone()[0]
        print(f"✅ Всего журналов в базе: {journal_count}")

        # 2. Считаем количество специальностей
        cursor.execute("SELECT COUNT(*) FROM specialties")
        specialty_count = cursor.fetchone()[0]
        print(f"✅ Всего уникальных специальностей: {specialty_count}")
        
        print("\n--- 5 случайных журналов в базе и их специальности: ---")
        cursor.execute("SELECT id, title, issn FROM journals ORDER BY RANDOM() LIMIT 5")
        journals = cursor.fetchall()
        
        if not journals:
            print("В базе данных не найдено журналов.")
            return

        for journal in journals:
            journal_id, journal_title, journal_issn = journal
            print(f"\n[+] Журнал: {journal_title} (ID: {journal_id}, ISSN: {journal_issn})")

            query = """
            SELECT s.code, s.name 
            FROM specialties s
            JOIN journal_specialties js ON s.id = js.specialty_id
            WHERE js.journal_id = ?
            """
            cursor.execute(query, (journal_id,))
            specs = cursor.fetchall()
            
            if specs:
                for spec in specs:
                    print(f"  - Код: {spec[0]}, Название: {spec[1]}")
            else:
                print("  Специальности не найдены.")

    except sqlite3.Error as e:
        print(f"❌ Произошла ошибка при проверке базы данных: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if os.path.exists(DB_FILE):
        check_database_content()
    else:
        print(f"Файл базы данных '{DB_FILE}' не найден.") 