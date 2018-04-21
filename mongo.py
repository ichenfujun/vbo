# -*-coding: utf-8-*-
'''
Created on 2015年9月22日

@author: rhc
'''
MONGODB_SERVER='localhost'
#MONGODB_SERVER='localhost'
MONGODB_PORT=27017
MONGODB_DB='vbo'
MONGODB_USER='vbo'
MONGODB_PASSWORD='onair123'
import logging
from pymongo import MongoClient

logger=logging.getLogger(__name__)

class Mongo(object):
    def __init__(self):
        self.col = 'vbo'
        self.conn = MongoClient(MONGODB_SERVER, MONGODB_PORT)
        self.db = self.conn[MONGODB_DB]
        self.db.authenticate(MONGODB_USER,MONGODB_PASSWORD)
        self.collection = self.db[self.col]
 
    def insert_value(self,value,collection='vbo'):
        collection = self.collection if collection==self.col else self.db[collection]
        return collection.insert(value)
        
    def close(self):
        if self.conn:
            self.conn.close()
    
