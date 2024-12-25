import re
import json

with open("config/config_file.json", "r") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]
bot_token = config["bot_token"]
review_chat_id = config["review_chat_id"]
channels_to_monitor = config["channels_to_monitor"]
my_channel = config["my_channel"]
my_channel_id = config["my_channel_id"]

db_name = 'meme_bot.db'
ad_keywords = ["реклама", "спонсор", "поддержи", "подписывайся", "партнёрская", "промо"]
link_pattern = re.compile(r"(t\.me/|@|https?://)")