from pymongo import MongoClient
import os

__todols = None
__client = None


def getDB():
    return __todols


def connectDB():
    global __todols
    global __client

    if __client:
        __client.close()
    DATABASE_URL = os.getenv("MONGO_URL")
    client = MongoClient(DATABASE_URL)
    __todols = client.todols
