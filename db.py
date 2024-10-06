import sqlite3

def create_user_table():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Создание таблицы пользователей с аватарами
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        achievements INTEGER DEFAULT 0,
        avatar_list TEXT NOT NULL DEFAULT 'default.png', -- Список аватаров, по умолчанию 'default.png'
        selected_avatar TEXT NOT NULL DEFAULT 'default.png', -- По умолчанию выбран 'default.png'
        level INTEGER DEFAULT 1,
        points INTEGER DEFAULT 0,
        completed_victories INTEGER DEFAULT 0
    )
    ''')

    # Подтверждение изменений
    conn.commit()
    conn.close()

    print("Таблица users успешно создана!")

if __name__ == "__main__":
    create_user_table()
