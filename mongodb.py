from pymongo import MongoClient
from config import MONGO_URL


"""
    日志告警项目使用的是mongo数据库。
"""
mdb = MongoClient(MONGO_URL, connect=False)

db = mdb['logAlert']

LOGINFO = db['logInfo']
USER = db['adminUser']
PROJECT = db['project']
HANDLERECORD = db['handleRecord']
TASK = db['tasks']
