from config.db import MONGO_URI
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = MONGO_URI

client = MongoClient(uri, server_api=ServerApi('1'))

db = client.inventory_db
user_collection = db["user_inventory"]
