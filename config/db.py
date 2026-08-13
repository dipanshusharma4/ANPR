from pymongo import MongoClient
from dotenv import load_dotenv
import os


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
conn = client[os.getenv("MONGO_DB", "admin_dashboard")] 

try:
	from motor.motor_asyncio import AsyncIOMotorClient
	motor_client = AsyncIOMotorClient(MONGO_URI)
	db = motor_client[os.getenv("MONGO_DB", "admin_dashboard")]
except Exception:
	db = None
