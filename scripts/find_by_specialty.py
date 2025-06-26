import sqlite3
import argparse
import csv
from pathlib import Path

def find_journals_by_specialty(db_path, specialty_code):
    """
    Находит журналы по коду специальности и сохраняет их в CSV-файл.
    """
    # Создаем папку для результатов, если ее нет
    output_dir = Path("search_results")
    output_dir.mkdir(exist_ok=True)

    # Формируем имя файла, делая его безопасным для файловой системы
    safe_code_part = specialty_code.replace('.', '_').replace('/', '_')
    output_filename = output_dir / f"specialty_{safe_code_part}.csv"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Ищем по началу кода, чтобы запрос '5.7' нашел и '5.7.7'
        query_code = f"{specialty_code}%"
        cursor.execute("""
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
                s.code LIKE ?
            ORDER BY
                j.vak_category, j.title;
        """, (query_code,))

        results = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return
    finally:
        if conn:
            conn.close()

    if not results:
        print(f"Журналы по специальности с кодом '{specialty_code}' не найдены.")
        return

    # Преобразуем 0/1 в "Нет/Да" для наглядности
    processed_results = [
        (row[0], row[1], row[2], "Да" if row[3] == 1 else "Нет") for row in results
    ]

    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Название журнала', 'ISSN', 'Категория ВАК', 'Индексируется в Scopus'])  # Заголовки
            csv_writer.writerows(processed_results) # Данные
        
        print(f"✅ Найдено {len(results)} журнал(ов).")
        print(f"Результаты сохранены в файл: {output_filename}")

    except IOError as e:
        print(f"❌ Ошибка при записи в файл {output_filename}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Поиск журналов по коду специальности в базе ВАК и сохранение в CSV."
    )
    parser.add_argument(
        "code",
        type=str,
        help="Код научной специальности для поиска (например, '5.7.7' или '5.7')."
    )
    
    args = parser.parse_args()
    
    DB_FILE = "database/journals.db"
    
    if Path(DB_FILE).exists():
        find_journals_by_specialty(DB_FILE, args.code)
    else:
        print(f"❌ Ошибка: Файл базы данных '{DB_FILE}' не найден.")
        print("Пожалуйста, сначала создайте и наполните базу данных.") 