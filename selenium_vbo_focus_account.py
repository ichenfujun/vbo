# -*- coding: utf-8 -*-
'''
Created on 2015年12月21日

@author: rhc
'''
import logging,time,sys
from selenium_vbo import SeleniumVbo

default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)

logging.basicConfig(filename='log.log', format='[%(asctime)s]%(levelname)s:%(message)s', filemode='a',stream=True,level='INFO')
logger=logging.getLogger(__name__)

class SeleniumVboFocusAccount(SeleniumVbo):
    
    #关注一个微博账号
    def focusWeiboUser(self,nick_name,account):
        logger.info("begin focus %s:%s" % (nick_name,account))
        self.urlSerachNickName(nick_name)
        if not self.searchResultIsExistNickName(nick_name,account):
            logger.info("关注 %s 失败" % nick_name)
            return False
        self.focusAccount(nick_name, account)
        logger.info("focus %s:%s success" % (nick_name,account))
        return True
    
    #初始化搜索页面
    def init(self):
        self.get("http://s.weibo.com/")
        
        
        try:
            self.find_element(self.driver.find_element_by_xpath, '//input[@class="searchInp_form"]').send_keys("魏晨")
            self.click(self.find_element(self.driver.find_element_by_xpath, '//*[@node-type="submit"]'))
        except:
            pass
        finally:
            time.sleep(7)
        logger.info('focus init finish')
    
    #是否为找人模式
    def isFindPeople(self):
        return True if self.find_element(self.driver.find_element_by_xpath, '//a[@action-type="searchItem" and @suda-data="key=tblog_search_user&value=user_user" and @class="cur"]', None, False) else False
    
    #设置为找人模式
    def setFindPeople(self):
        if self.isFindPeople():
            return
        for i in range(0,5):
            self.click(self.find_element(self.driver.find_element_by_xpath, '//a[@action-type="searchItem" and @suda-data="key=tblog_search_user&value=user_user"]', None, True))
            if self.isFindPeople():
                return
        raise Exception("设置找人模式出错")
    
    #是否为按昵称找
    def isFindNickName(self):
        if self.isFindPeople() is None:
            return False
        
        return True if self.find_element(self.driver.find_element_by_xpath, '//span[@action-type="search" and @action-data="flag=nickname"]/parent::a/parent::li[@class="cur"]', None, False) else False
    
    #设置按昵称查找
    def sefFindNickName(self):
        self.setFindPeople()
        if self.isFindNickName():
            return
        for i in range(0,5):
            self.click(self.find_element(self.driver.find_element_by_xpath, '//span[@action-type="search" and @action-data="flag=nickname"]/parent::a', None, True))
            if self.isFindNickName():
                return
        raise Exception("设置按昵称查找模式出错")
        
    
    #搜索一个值    
    def inputSearch(self,key):
        
        searchInput=self.find_element(self.driver.find_element_by_xpath, '//input[@class="searchInp_form"]', None, True)
        searchInput.clear()
        searchInput.send_keys(key)
        
        self.click(self.find_element(self.driver.find_element_by_xpath, '//a[@class="searchBtn" and @node-type="submit"]', None, True))

    #用url搜索key
    def urlSerachNickName(self,key):
        self.get("http://s.weibo.com/user/&nickname="+key)
        for i in range(0,5):
            if self.find_element(self.driver.find_element_by_xpath, "//*[@id='pl_common_totalshow']", None, False):
                break
            time.sleep(5)
        time.sleep(2)
        
    #搜索结果中是否包含微博
    def searchResultIsExistNickName(self,nick_name,account):
        weibo_user=self.find_element(self.driver.find_element_by_xpath, '//a[@suda-data="key=tblog_search_user&value=user_feed_1_name" and @uid="%s"]' % account, None, False)
        
        if weibo_user is None:
            logger.info("搜索昵称 %s 未找到微博" % nick_name)
            return False
        logger.info("搜索昵称 %s 找到 微博" % nick_name)
        return True
    
    #关注一个账号
    def focusAccount(self,nick_name,account):
        logger.info("focus %s:%s" %(nick_name,account))
        self.click(self.find_element(self.driver.find_element_by_xpath, '//a[@suda-data="key=tblog_search_user&value=user_feed_1_name" and @uid="%s"]/parent::p/parent::div/parent::div/div[@class="person_adbtn"]/a[@suda-data="key=tblog_search_user&value=user_feed_1_follow"]' % account, None, False))
        time.sleep(5)
    
    #从mongo里取出微博并关注
    def focusWeiboUers(self,weiboUsers):
        logger.info("开始关注微博")
        if weiboUsers is None or len(weiboUsers)==0:
            logger.info("关注we")
            logger.info("关注微博完成")
            return
        
        for weiboUser in weiboUsers:
            account=weiboUser['account']
            result=True
            message=''
            try:
                result=self.focusWeiboUser(weiboUser['nick_name'], account)
                message='成功' if result else '未找到微博'
            except Exception,e:
                logger.error(e)
                message=e
            finally:
                updateInfo={}
                updateInfo['status']= 1 if result else 2
                #updateInfo['message']=message
                updateInfo['again_num']=weiboUser['again_num']+1 if weiboUser.has_key('again_num') else 1
                updateInfo['update_time']=time.strftime("%Y-%m-%d %X", time.localtime())
                if result:
                    updateInfo['focus_time']=time.strftime("%Y-%m-%d %X", time.localtime())
                
                self.updateFocusWeiboInfo(account, updateInfo)
                
        logger.info("关注微博完成")  
    
    #定时执行
    def crond(self):
        
        while True:
            logger.info("开始获取需要关注的微博")
            weiboUsers=self.getNeedFocusWeibos()
             
            if weiboUsers is None or len(weiboUsers)==0:
                logger.info("没有获取到需要关注的微博")
            else:
                self.focusWeiboUers(weiboUsers)
            time.sleep(100)         
              
if  __name__ =='__main__':
    vbo=SeleniumVboFocusAccount()
    vbo.login()
    vbo.crond()
        