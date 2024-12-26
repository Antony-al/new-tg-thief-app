import os  # Модуль для работы с файловой системой
import re # Регулярные выражения
import asyncio # Модуль для работы с асинхронным кодом в Python
from config.config_ import api_id, api_hash, bot_token, channels_to_monitor, ad_keywords, link_pattern, review_chat_id, my_channel_id
from aiogram import Bot, Dispatcher, Router, types  # Библиотека для работы с Telegram Bot API
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from telethon import TelegramClient  # Библиотека для работы с Telegram-клиентом
from aiogram.types.input_file import FSInputFile
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument  # Типы медиа в Telethon

# Инициализация Telegram-клиента через Telethon
client = TelegramClient(
    'meme_user',  # Название сессии (файл сессии будет создан в текущей директории)
    api_id,       # API ID из конфигурации
    api_hash,     # API Hash из конфигурации
    device_model="iPhone 13 Pro Max",  # Модель устройства (параметры для маскировки)
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

def get_channel_media_folder(channel_name):
    """
    Создает папку для конкретного канала, чтобы сохранять медиа в отдельные папки.
    
    Аргументы:
    - channel_name: имя канала (или его ссылка).
    
    Возвращает:
    - Путь к папке, где будет храниться медиа.
    """
    # Очищаем имя канала от символов, которые не могут быть в имени папки
    sanitized_name = channel_name.replace("t.me/", "").replace("/", "_").replace(" ", "_")
    channel_folder = os.path.join(BASE_MEDIA_FOLDER, sanitized_name)
    os.makedirs(channel_folder, exist_ok=True)
    return channel_folder

async def save_media(message, channel_name):
    """
    Сохраняет медиа-файлы (фото или документы) из сообщения.
    
    Аргументы:
    - message: объект сообщения Telethon, содержащий медиа.
    
    Действие:
    - Скачивает медиа-файл в папку MEDIA_FOLDER.
    """

    channel_folder = get_channel_media_folder(channel_name)  # Получаем папку для канала

    if isinstance(message.media, MessageMediaPhoto):  # Если медиа является фото
        file_path = await client.download_media(message, file=channel_folder)  # Скачиваем файл
        print(f"Фото сохранено: {file_path}")  # Логируем путь сохранения
    elif isinstance(message.media, MessageMediaDocument):  # Если медиа является документом (включая видео и GIF)
        file_path = await client.download_media(message, file=channel_folder)  # Скачиваем файл
        print(f"Документ сохранен: {file_path}")  # Логируем путь сохранения
    else:
        print("Медиа не распознано.")  # Логируем необработанный тип медиа

async def filter_and_save_messages(channel):
    """
    Фильтрует сообщения из канала и сохраняет медиа.
    
    Аргументы:
    - channel: ссылка на канал, из которого будем получать сообщения.
    
    Действие:
    - Получаем последние 5 сообщений из канала.
    - Пропускаем рекламные сообщения.
    - Сохраняем медиа, если оно есть.
    """
    print(f"Получаем сообщения из канала: {channel}")
    
    # Получаем последние 5 сообщений из канала
    async for message in client.iter_messages(channel, limit=5):  
        # Фильтруем рекламные сообщения
        if message.text:  # Проверяем, есть ли текст в сообщении
            if any(keyword.lower() in message.text.lower() for keyword in ad_keywords):  # Проверка на ключевые слова
                print(f"Рекламное сообщение пропущено: {message.text[:30]}...")  # Логируем
                continue  # Пропускаем сообщение

            # Проверка на наличие внешних ссылок с помощью регулярного выражения
            if re.search(link_pattern, message.text):  
                print(f"Сообщение с внешней ссылкой пропущено: {message.text[:30]}...")  # Логируем
                continue  # Пропускаем сообщение
        
        # Сохраняем медиа, если оно есть
        if message.media:
            await save_media(message, channel)
        else:
            print(f"Текстовое сообщение: {message.text}")  # Логируем текст сообщения

# Обработчик для команды "/start"
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я готов работать.")

# Обработчик для callback-запросов
@callback_router.callback_query()
async def process_callback(callback_query: types.CallbackQuery):
    action = callback_query.data
    if action == 'post':
        # Логика для запостить мем
        await callback_query.message.answer("Мем запощен в канал!")
        await callback_query.message.delete()
    elif action == 'reject':
        # Логика для отклонить мем
        await callback_query.message.delete()
        await callback_query.answer("Мем отклонен.")

# Создание кнопок
def create_approve_reject_keyboard(from_channel_id, message_id):
    # Преобразуем channel_id в строку, если это необходимо
    my_channel_id_str = str(my_channel_id)
    print("my_channel_id_str", my_channel_id_str)
    print("from_channel_id", from_channel_id)
    approve_callback = MemeActionCallback(action="approve", from_channel_id=str(from_channel_id), channel_id=my_channel_id_str, message_id=message_id).pack()
    reject_callback = MemeActionCallback(action="reject", from_channel_id=str(from_channel_id), channel_id=my_channel_id_str, message_id=message_id).pack()

    approve_button = InlineKeyboardButton(text="Запостить", callback_data=approve_callback)
    reject_button = InlineKeyboardButton(text="Отклонить", callback_data=reject_callback)
    return InlineKeyboardMarkup(inline_keyboard=[[approve_button, reject_button]])

# Асинхронная логика бота для обработки сообщений с кнопками
async def send_message_with_buttons(chat_id, message, media_path):
    """
    Отправка сообщения с кнопками "Запостить" и "Отклонить".
    """
    # keyboard = InlineKeyboardMarkup(row_width=2)
    # keyboard.add(
    #     InlineKeyboardButton("Запостить", callback_data="post"),
    #     InlineKeyboardButton("Отклонить", callback_data="reject")
    # )

    markup = create_approve_reject_keyboard(review_chat_id, message.id)
    
    if media_path:
        with open(media_path, 'rb') as media_file:
            await bot.send_photo(chat_id, media_file, caption=message.text, reply_markup=markup)
    else:
        await bot.send_message(chat_id, message.text, reply_markup=markup)

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
                file_path = await client.download_media(message)
                # Отправляем мем в личку с кнопками
                await send_message_with_buttons(chat_id=review_chat_id, message=message, media_path=file_path)
            else:
                print(f"Текстовое сообщение: {message.text}")

async def main():
    """
    Основная точка входа в асинхронную логику программы.
    
    Действия:
    - Вызывает функцию для получения и обработки сообщений.
    """
    await fetch_latest_messages()

    """for test"""
    # channel = "t.me/dvachannel"
    # await filter_and_save_messages(channel)


async def main():
    await client.start()  # Подключаем и авторизуем клиента
    await fetch_latest_messages()  # Асинхронный код для получения сообщений

if __name__ == '__main__':

    # Регистрируем роутеры для обработчиков
    dp.include_router(message_router)
    dp.include_router(callback_router)

    # Запускаем бота и Telethon одновременно через asyncio
    loop = asyncio.get_event_loop()  # Получаем текущий цикл событий
    loop.create_task(main())  # Запускаем основную функцию Telethon (получение сообщений)
    loop.run_until_complete(dp.start_polling(bot))  # Запуск бота с опросом серверов Telegram