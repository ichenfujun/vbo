# -*- coding: utf-8 -*-
'''
Created on 2016年7月21日

@author: rhc
'''
import sys,os
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
from vbo3.selenium_vbo_mongo import SeleniumVboMongo
from vbo3.mongo import Mongo
class TransCreateTime(SeleniumVboMongo):
    
    PAGE_SIZE=100
    
    def __init__(self):
        self.mongo=Mongo()
        
    #获取一页微博数据，只取WeiboID和CreateTime
    def getPageWeibo(self,currentPage):
        con = self.mongo.db[self.VBO_VBO_CONTENT_TABLE]
        
        start=(currentPage-1)*self.PAGE_SIZE
        limit=self.PAGE_SIZE
        
        return [weibo for weibo in con.find({},{"WeiboID":1,"CreateTime":1,"Author.Accounts":1}).limit(limit).skip(start)]
    
    #将微博的CreateTime设置进微博更新表
    def setCreateTimeToVboUpdate(self,weibo):
        if weibo is None:
            return
        
        con=self.mongo.db[self.VBO_VBO_COMMENT_UPDATE_TABLE]
        
        weiboId=weibo['WeiboID']
        createTime=weibo['CreateTime']
        accounts=weibo['Author']['Accounts']
        con.update({"WeiboID":weiboId},{"$set":{"CreateTime":createTime,"Accounts":accounts}})
    
    #将weibo列表里的CreateTime设置进微博更新表    
    def processWeiboList(self,weiboList):
        if weiboList is None or len(weiboList) == 0:
            return
        
        for weibo in weiboList:
            self.setCreateTimeToVboUpdate(weibo)
    
    #将所有微博CreateTime设置到更新表
    def allVboCreateTimeToVboUpdate(self):
        currentPage=1
        
        while True:
            weiboList=self.getPageWeibo(currentPage)
            self.processWeiboList(weiboList)
            
            if weiboList is None or len(weiboList) < self.PAGE_SIZE:
                break
            
            print "%s page finish"%currentPage
            currentPage+=1
        
        
    
if __name__ == '__main__':
    transCreateTime=TransCreateTime()
    transCreateTime.allVboCreateTimeToVboUpdate()
    