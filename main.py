import os  # Модуль для работы с файловой системой
import re  # Регулярные выражения
import db.meme_db
import asyncio  # Модуль для работы с асинхронным кодом в Python
import datetime
import uuid
from config.config_ import api_id, api_hash, bot_token, channels_to_monitor, ad_keywords, link_pattern, review_chat_id, my_channel_id
# Библиотека для работы с Telegram Bot API
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from telethon import TelegramClient  # Библиотека для работы с Telegram-клиентом
from aiogram.types.input_file import FSInputFile
# Типы медиа в Telethon
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument


# Инициализация Telegram-клиента через Telethon
client = TelegramClient(
    # Название сессии (файл сессии будет создан в текущей директории)
    'meme_user',
    api_id,       # API ID из конфигурации
    api_hash,     # API Hash из конфигурации
    # Модель устройства (параметры для маскировки)
    device_model="iPhone 13 Pro Max",
    app_version="8.4",                 # Версия приложения
    lang_code="en",                    # Язык клиента
    system_lang_code="en-US"           # Системный язык
)

# Инициализация Telegram-бота через aiogram
bot = Bot(token=bot_token)
dp = Dispatcher()

# Создаем объект Router для обработки callback-запросов
message_router = Router()
callback_router = Router()

# Папка для сохранения медиа-файлов
BASE_MEDIA_FOLDER = "media"
os.makedirs(BASE_MEDIA_FOLDER, exist_ok=True)  # Создаем папку, если её нет


class MemeActionCallback(CallbackData, prefix="meme"):
    action: str
    from_channel_id: str
    channel_id: str
    message_id: int
    post_id: int

def generate_unique_id():
    return str(uuid.uuid4()) 

def get_channel_media_folder(channel_name):
    """
    Создает папку для конкретного канала, чтобы сохранять медиа в отдельные папки.

    Аргументы:
    - channel_name: имя канала (или его ссылка).

    Возвращает:
    - Путь к папке, где будет храниться медиа.
    """
    # Очищаем имя канала от символов, которые не могут быть в имени папки
    sanitized_name = channel_name.replace(
        "t.me/", "").replace("/", "_").replace(" ", "_")
    channel_folder = os.path.join(BASE_MEDIA_FOLDER, sanitized_name)
    os.makedirs(channel_folder, exist_ok=True)
    return channel_folder


async def save_media(message, channel):
    """
    Сохраняет медиа-файлы (фото или документы) из сообщения.

    Аргументы:
    - message: объект сообщения Telethon, содержащий медиа.

    Действие:
    - Скачивает медиа-файл в папку MEDIA_FOLDER.
    """

    channel_folder = get_channel_media_folder(
        channel)  # Получаем папку для канала

    # Если медиа является фото или документом (включая видео и GIF)
    if (isinstance(message.media, MessageMediaPhoto) or isinstance(message.media, MessageMediaDocument)):
        # Скачиваем файл
        file_path = await client.download_media(message, file=channel_folder)
        # Логируем путь сохранения
        print(f"Пост сохранен на диске: {file_path}")
        return file_path
    else:
        print("Медиа не распознано.")  # Логируем необработанный тип медиа
        return None


async def filter_and_save_message(message, channel):
    """
    Фильтрует сообщение из канала и сохраняет медиа.

    Аргументы:
    - message: сообщение из канала

    """
    
    if await db.meme_db.is_posted(channel, message.id):
        print(f"Сообщение с id {message.id} уже было скачано")
        return
    
    # Проверка на ключевые слова
    if any(keyword.lower() in message.text.lower() for keyword in ad_keywords):
        # Логируем
        print(f"Рекламное сообщение пропущено: {message.text[:30]}...")
        return  # Пропускаем сообщение

        # Проверка на наличие внешних ссылок с помощью регулярного выражения
    if re.search(link_pattern, message.text):
        # Логируем
        print(
            f"Сообщение с внешней ссылкой пропущено: {message.text[:30]}...")
        return  # Пропускаем сообщение

    # Сохраняем медиа, если оно есть
    if message.media:
        media_path = await save_media(message, channel)
        nowDt = datetime.datetime.now()
        post_id = await db.meme_db.save_post_info(channel, message.id, media_path, nowDt)
        if isinstance(post_id, tuple):
            post_id = post_id[0]
        return post_id
    else:
        # Логируем текст сообщения
        print(f"Текстовое сообщение: {message.text}")

# Обработчик для команды "/start"


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я готов работать.")

# Обработчик для callback-запросов


@dp.callback_query(MemeActionCallback.filter())
async def process_callback(callback_query: types.CallbackQuery, callback_data: MemeActionCallback):
    action = callback_data.action
    channel_id = callback_data.from_channel_id
    message_id = callback_data.message_id
    post_id = callback_data.post_id
    if action == 'approve':
        # async with aiosqlite.connect(db_name) as db:
        #     async with db.execute("SELECT media_path, caption FROM queue WHERE channel_id = ? AND message_id = ?",
        #                           (channel_id, message_id)) as cursor:
        #         result = await cursor.fetchone()
        #         if result:
        #             media_path, caption = result
        media_path = await db.meme_db.get_media_path(post_id)
        if isinstance(media_path, tuple):
            media_path = media_path[0]
    
        file = FSInputFile(media_path)
        await bot.send_document(my_channel_id, file)
        # await mark_as_posted(channel_id, message_id)
        # await db.execute("DELETE FROM queue WHERE channel_id = ? AND message_id = ?", (channel_id, message_id))
        # await db.commit()
        await bot.answer_callback_query(callback_query.id, "Пост опубликован.")
        await asyncio.sleep(15 * 60)  # Задержка 15 минут
    elif action == 'reject':
        # Удаляем сообщение из чата, в котором оно было отправлено
        try:
            await bot.delete_message(review_chat_id, callback_query.message.message_id)
            print(f"Сообщение {message_id} из чата {review_chat_id} удалено.")
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")
        # async with aiosqlite.connect(db_name) as db:
        #     await db.execute("DELETE FROM queue WHERE channel_id = ? AND message_id = ?", (channel_id, message_id))
        #     await db.commit()
        #     await bot.answer_callback_query(callback_query.id, "Пост отклонен.")
# @callback_router.callback_query()
# async def process_callback(callback_query: types.CallbackQuery):
#     action = callback_query.data
#     if action == 'approve':
#         # Логика для запостить мем
#         await callback_query.message.answer("Мем запощен в канал!")
#         await callback_query.message.delete()
#     elif action == 'reject':
#         # Логика для отклонить мем
#         await callback_query.message.delete()
#         await callback_query.answer("Мем отклонен.")

# Создание кнопок


def create_approve_reject_keyboard(from_channel_id, message_id, post_id):
    # Преобразуем channel_id в строку, если это необходимо
    my_channel_id_str = str(my_channel_id)
    print("my_channel_id_str", my_channel_id_str)
    print("from_channel_id", from_channel_id)
    approve_callback = MemeActionCallback(action="approve", from_channel_id=str(
        from_channel_id), channel_id=my_channel_id_str, message_id=message_id, post_id=post_id).pack()
    reject_callback = MemeActionCallback(action="reject", from_channel_id=str(
        from_channel_id), channel_id=my_channel_id_str, message_id=message_id, post_id=post_id).pack()

    approve_button = InlineKeyboardButton(
        text="Запостить", callback_data=approve_callback)
    reject_button = InlineKeyboardButton(
        text="Отклонить", callback_data=reject_callback)
    return InlineKeyboardMarkup(inline_keyboard=[[approve_button, reject_button]])

# Асинхронная логика бота для обработки сообщений с кнопками


async def send_message_with_buttons(from_channel_id, message, post_id):
    """
    Отправка сообщения с кнопками "Запостить" и "Отклонить".
    """
    
    media_path = await db.meme_db.get_media_path(post_id)
    if isinstance(media_path, tuple):
        media_path = media_path[0]
    
    if media_path is None:
        print("Ошибка: media_path отсутствует.")
        return
    
    markup = create_approve_reject_keyboard(from_channel_id, message.id, post_id)

    if media_path:
        print("Media path: ", media_path)
        file = FSInputFile(media_path)
        await bot.send_document(review_chat_id, file, caption=message.text, reply_markup=markup)
    else:
        await bot.send_message(review_chat_id, caption=message.text, reply_markup=markup)


async def fetch_latest_messages():
    """
    Получает последние сообщения из указанных каналов и обрабатывает их.

    Действия:
    - Проходит по всем каналам из списка `channels_to_monitor`.
    - Фильтрует рекламные сообщения, используя список ключевых слов `ad_keywords`.
    - Сохраняет медиа-файлы (фото, документы) из сообщений.
    """
    # for channel in channels_to_monitor:  # Перебираем список каналов
    #     await filter_and_save_messages(channel)  # Вызываем новую функцию для каждого канала

    for channel in channels_to_monitor:

        async for message in client.iter_messages(channel, limit=5):
            if message.media:
                post_id = await filter_and_save_message(message, channel)
                if post_id is None:
                    continue
                # Отправляем мем в личку с кнопками
                print(f"Post_id = {post_id}")
                await send_message_with_buttons(from_channel_id=channel, message=message, post_id=post_id)
            else:
                print(f"Текстовое сообщение: {message.text}")


# async def main():
#     """
#     Основная точка входа в асинхронную логику программы.

#     Действия:
#     - Вызывает функцию для получения и обработки сообщений.
#     """
#     await fetch_latest_messages()

#     """for test"""
#     # channel = "t.me/dvachannel"
#     # await filter_and_save_messages(channel)


async def main():
    await client.start()  # Подключаем и авторизуем клиента
    await db.meme_db.setup_database()
    try:
        await fetch_latest_messages()  # Асинхронный код для получения сообщений
    finally:
        client.disconnect()
        

if __name__ == '__main__':

    # Регистрируем роутеры для обработчиков
    dp.include_router(message_router)
    dp.include_router(callback_router)

    # Запускаем бота и Telethon одновременно через asyncio
    loop = asyncio.get_event_loop()  # Получаем текущий цикл событий
    # Запускаем основную функцию Telethon (получение сообщений)
    loop.create_task(main())
    # Запуск бота с опросом серверов Telegram
    loop.run_until_complete(dp.start_polling(bot))
