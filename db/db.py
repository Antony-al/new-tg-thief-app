import sqlite3
from config import db_name

async def setup_database():
    """Создаем таблицу для хранения ID сообщений, если ее еще нет"""
    connection = sqlite3.connect(db_name)

    connection.close()

class DbMaker():
    def __init__(self):
        pass
