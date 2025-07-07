import sqlite3
from contextlib import contextmanager


DATABASE = 'database.db'

@contextmanager
def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()

def init_db():
    with get_db_connection() as connection:
        cursor = connection.cursor()
        # Users DB
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE, 
            email TEXT
        )
        ''')
        # Segments DB
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Segments ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            segment TEXT NOT NULL UNIQUE, 
            description TEXT
        )
        ''')
        # Users and Segments DB
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS U_S ( 
            user_id INTEGER,
            segment_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE, 
            FOREIGN KEY (segment_id) REFERENCES Segments(id) ON DELETE CASCADE, 
            PRIMARY KEY (user_id, segment_id)
        )
        ''')
        # Изначальные значения, который будут в таблицах. Их можно не вносить вовсе
        cursor.executemany(
            'INSERT OR IGNORE INTO Segments (segment, description) VALUES (?, ?)',
            [
                ('MAIL_VOICE_MESSAGES', 'Доступ к голосовым сообщениям'),
                ('CLOUD_DISCOUNT_30', 'Скидка 30% на облачное хранилище'),
                ('MAIL_GPT', 'Интеграция GPT в почту')
            ]
        )

        cursor.executemany(
            'INSERT OR IGNORE INTO Users (name, email) VALUES (?, ?)',
            [
                ('123', 'alex@example.com'),
                ('231', 'max@example.com'),
                ('312', 'anna@example.com'),
                ('456', 'ivan@example.com'),
                ('564', 'olga@example.com')
            ]
        )

        connection.commit()

# Добавление пользователя
def add_user(name: str, email: str = None):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO Users (name, email) VALUES (?, ?)',
            (name, email)
        )
        connection.commit()

# Добавление пользователя в сегмент
def add_user_to_segment(user_id, segment_id):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO U_S (user_id, segment_id) VALUES (?, ?)', (user_id, segment_id)
        )
        connection.commit()

# Удаление пользователя из сегмента
def delete_user_in_segment(user_id, segment_id):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            'DELETE FROM U_S WHERE user_id = ? AND segment_id = ?', (user_id, segment_id)
        )
        connection.commit()

# Добавление сегмента
def add_segment(segment, description):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO Segments (segment, description) VALUES (?, ?)', (segment, description)
        )
        connection.commit()

# Удаление сегмента
def delete_segment(segment):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            'DELETE FROM Segments WHERE segment = ?', (segment,)
        )
        connection.commit()

# Распределение сегмента на N% пользователей
def distribute_segment_to_percent(segment_id, percent):
    with get_db_connection() as connection:
        cursor = connection.cursor()

        # Удаляем всех пользователей из этого сегмента
        cursor.execute(
            'DELETE FROM U_S WHERE segment_id = ?',
            (segment_id,)
        )
        # Получаем общее количество пользователей
        cursor.execute('SELECT COUNT(*) as count FROM Users')
        total_users = cursor.fetchone()['count']

        # Вычисляем количество пользователей для выборки
        sample_size = int(total_users * percent / 100)

        # Выбираем случайных пользователей
        cursor.execute(
            'SELECT id FROM Users ORDER BY RANDOM() LIMIT ?',(sample_size,)
        )
        # Добавляем выбранных пользователей в сегмент
        for user in cursor.fetchall():
            cursor.execute(
                'INSERT OR IGNORE INTO U_S (user_id, segment_id) VALUES (?, ?)',
                (user['id'], segment_id)
            )

        connection.commit()

# Получение сегментов пользователя
def get_user_segments(user_id):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            'SELECT segment FROM Segments JOIN U_S ON Segments.id = U_S.segment_id WHERE user_id = ?', (user_id,)
        )
        return [row['segment'] for row in cursor.fetchall()]

# Получение пользователей в сегменте
def get_users_in_segment(segment):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            '''
            SELECT Users.name
            FROM Users
            JOIN U_S ON Users.id = U_S.user_id
            JOIN Segments ON U_S.segment_id = Segments.id
            WHERE Segments.segment = ?
            ''',
            (segment,)
        )
        return [row['name'] for row in cursor.fetchall()]

# Получение статистики по сегментам
def get_segments_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT 
                Segments.segment,
                COUNT(U_S.user_id) AS user_count
            FROM Segments
            LEFT JOIN U_S ON Segments.id = U_S.segment_id
            GROUP BY Segments.segment
            '''
        )
        return [dict(row) for row in cursor.fetchall()]

#Обновление описания сегмента
def update_segment_description(segment, new_description):
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            'UPDATE Segments SET description = ? WHERE segment = ?',
            (new_description, segment)
        )
        connection.commit()


# Перенос пользователей между сегментами
def move_users_between_segments(from_segment_name, to_segment_name):
    with get_db_connection() as connection:
        cursor = connection.cursor()

        # Получаем ID сегментов
        cursor.execute('SELECT id FROM Segments WHERE segment = ?', (from_segment_name,))
        from_segment_id = cursor.fetchone()['id']

        cursor.execute('SELECT id FROM Segments WHERE segment = ?', (to_segment_name,))
        to_segment_id = cursor.fetchone()['id']

        # Получаем всех пользователей исходного сегмента
        cursor.execute('SELECT user_id FROM U_S WHERE segment_id = ?', (from_segment_id,))
        user_ids = [row['user_id'] for row in cursor.fetchall()]

        # Для каждого пользователя:
        for user_id in user_ids:
            # Удаляем связь с исходным сегментом
            cursor.execute(
                'DELETE FROM U_S WHERE user_id = ? AND segment_id = ?',
                (user_id, from_segment_id)
            )

            # Добавляем связь с новым сегментом (если её нет)
            cursor.execute(
                'INSERT OR IGNORE INTO U_S (user_id, segment_id) VALUES (?, ?)',
                (user_id, to_segment_id)
            )

        connection.commit()

if __name__ == '__main__':
    init_db()