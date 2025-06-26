import sqlite3
import os

DB_FILE = 'journals.db'

def create_database():
    """
    Создает базу данных SQLite с тремя таблицами: journals, specialties,
    и journal_specialties. Если файл базы данных уже существует, он будет
    удален и создан заново.
    """
    # Удаляем старый файл БД, если он существует
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Старый файл '{DB_FILE}' удален.")

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Включаем поддержку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 1. Создаем таблицу journals
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS journals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            issn TEXT,
            vak_category TEXT,
            scopus_indexed BOOLEAN DEFAULT 0 NOT NULL,
            wos_indexed BOOLEAN DEFAULT 0 NOT NULL,
            included_from TEXT
        )
        ''')

        # 2. Создаем таблицу specialties
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS specialties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL
        )
        ''')

        # 3. Создаем таблицу journal_specialties
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_specialties (
            journal_id INTEGER,
            specialty_id INTEGER,
            PRIMARY KEY (journal_id, specialty_id),
            FOREIGN KEY (journal_id) REFERENCES journals (id) ON DELETE CASCADE,
            FOREIGN KEY (specialty_id) REFERENCES specialties (id) ON DELETE CASCADE
        )
        ''')

        conn.commit()
        print(f"База данных '{DB_FILE}' и таблицы успешно созданы.")

    except sqlite3.Error as e:
        print(f"Произошла ошибка SQLite: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    create_database() 