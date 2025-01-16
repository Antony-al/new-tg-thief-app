import aiosqlite
from config.config_ import db_name

async def setup_database():
    """Создаем таблицу для хранения ID сообщений, если ее еще нет"""
    async with aiosqlite.connect(db_name) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS post (
                post_id INTEGER PRIMARY KEY autoincrement,
                channel_id TEXT,
                message_id INTEGER,
                media_path TEXT,
                is_accepted INTEGER,
                download_dt DATETIME,
                posted_dt DATETIME
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS post_queue (
                post_id INTEGER,
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            )
        """)
        await db.commit()
        
async def is_posted(channel_id, message_id):
    async with aiosqlite.connect(db_name) as db:
        async with db.execute("select 1 from post where channel_id = ? and message_id = ?",
                              (channel_id, message_id)) as cursor:
            return await cursor.fetchone()

async def save_post_info(channel_id, message_id, media_path, download_dt):
    async with aiosqlite.connect(db_name) as db:
        await db.execute("""
                         insert into post (
                                channel_id,
                                message_id,
                                media_path,
                                is_accepted,
                                download_dt,
                                posted_dt
                             ) values (
                                ?,
                                ?,
                                ?,
                                null,
                                ?,
                                null
                             )
                         """, (channel_id, message_id, media_path, download_dt))
        await db.commit()
        async with db.execute("select last_insert_rowid()") as cursor:
            return await cursor.fetchone()
            # return cursor.lastrowid()
        
async def add_to_queue(post_id):
    async with aiosqlite.connect(db_name) as db:
        await db.execute("insert into post_queue (post_id) values (?)", (post_id))
        await db.commit() 

async def mark_accepted_or_rejected(post_id, is_accepted):
    async with aiosqlite.connect(db_name) as db:
        await db.execute("update post set is_accepted = ? where post_id = ?", (is_accepted, post_id))
        await db.commit()

async def get_queued_posts():
    async with aiosqlite.connect(db_name) as db:
        async with db.execute("""select post_id, channel_id, message_id, media_path
                              from post_queqe 
                              join post on post.post_id = post_queue.post_id
                              """) as cursor:
            return cursor.fetchall()
        
async def remove_from_queue(post_id):
    async with aiosqlite.connect(db_name) as db:
        await db.execute("delete from post_queue where post_id = ?", (post_id))
        await db.commit()
        
async def mark_as_posted(post_id, posted_dt):
    async with aiosqlite.connect(db_name) as db:
        await db.execute("update post set posted_dt = ? where post_id = ?", (posted_dt, post_id))
        await db.connect()
        
async def get_media_path(post_id):
    async with aiosqlite.connect(db_name) as db:
        async with db.execute("select media_path from post where post_id = ?", (post_id,)) as cursor:
            return await cursor.fetchone()