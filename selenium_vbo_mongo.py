# -*- coding: utf-8 -*-
'''
Created on 2015年10月12日

@author: rhc
'''

import time, re, json, logging, os, urllib2, datetime, hashlib, copy, requests
from urlparse import urljoin, urlparse, urlunparse
from selenium import webdriver
from vbo3.mongo import Mongo
from selenium.webdriver.common.action_chains import ActionChains
from posixpath import normpath

logging.basicConfig(filename='log.log', format='[%(asctime)s]%(levelname)s:%(message)s', filemode='a', stream=True, level='INFO')
logger = logging.getLogger(__name__)

NEED_UPDATE_ACCOUNTS=['1575527140','1713458220','1068246700','2043351562','3562298415','1796087453','2755030790','2625504257','2521748280','1926786203','2790685082','1269647104','5344043453','2527687040','5157042636','1967164180','1917433500','1999404300','1840551510','1919291765','2321615032','2790685082','2683625641','2527687040','2127403275','1269647104']

class SeleniumVboMongo(object):
    
    #存储微博的MONGO数据库
    VBO_DB='vbo'
    #存储微博内容
    VBO_VBO_CONTENT_TABLE='vbo'
    #存储微博评论更新时间的表
    VBO_VBO_COMMENT_UPDATE_TABLE='vbo_update'
    '''
    {"WeiboID":id,"CommentUrl":url,"NextUpdateTime":time}
    '''
    #微博评论id表
    VBO_VBO_COMMENTS_TABLE='vbo_comments'
    '''
    {"WeiboID":id,"Comments":[commentId,]}
    '''
    
    #微博关注列表
    VBO_VBO_FOCUS_VBO='vbo_focus_account'
    
    def __init__(self):
        self.mongo=Mongo()
    
    
    # 检查微博是否已经存在，如果存在返回true，
    def vboExists(self, vbo):
        if self.mongo.db[self.VBO_VBO_CONTENT_TABLE].find_one({'WeiboID':vbo['WeiboID']},{"WeiboID":1}):
            return True
        
        self.saveVboToMongo(vbo)
        author=vbo['Author']
        account=author['Accounts']
        self.addVboUpdateTime(vbo['WeiboID'], 0, vbo['CommentUrl'],vbo['CreateTime'],account)
        
        return False
    
    #查看vboIdList中的是否有存在的
    def vboIdListHaveExists(self,vboIdList):
        
        if self.mongo.db[self.VBO_VBO_CONTENT_TABLE].find_one({'WeiboID':{"$in":vboIdList}},{"WeiboID":1}):
            return True
        return False
    
    # 将微博存入mongo
    def saveVboToMongo(self, vbo):
        # 深度拷贝，然后将Comments制空，方便后面的评论更新
        copy_vbo = copy.deepcopy(vbo)
        copy_vbo['Comments'] = []
        self.mongo.insert_value(copy_vbo,self.VBO_VBO_CONTENT_TABLE)
        logger.info("%s save to mongo" % copy_vbo)
    
    # 更新微博评论更新时间
    def addVboUpdateTime(self, vbo_id, next_update_time, comment_url,create_time,account):
        self.mongo.insert_value({'WeiboID':vbo_id, 'NextUpdateTime':next_update_time, 'CommentUrl':comment_url,'CreateTime':create_time,'Accounts':account}, self.VBO_VBO_COMMENT_UPDATE_TABLE)
        logger.info("add one update_time vbo_id:%s,comment_url:%s,update_time:%s,create_time:%s" % (vbo_id, comment_url, next_update_time,create_time))
    
    # 更新微博下一次的更新时间
    def updateVboUpdateTime(self, vbo_id, update_comment_num):
        con = self.mongo.db[self.VBO_VBO_COMMENT_UPDATE_TABLE]
        
        next_update_time = time.time() + 3600
        
        con.update({"WeiboID":vbo_id}, {"$set":{"NextUpdateTime":next_update_time}})
        
        logger.info("vob_id:%s update %s comment,update vbo_update_time:%s "% (vbo_id,update_comment_num,next_update_time))
    
    #更新微博信息
    def updateVboInfo(self,vbo_id,key,value):
        con=self.mongo.db[self.VBO_VBO_CONTENT_TABLE]
        
        con.update({"WeiboID":vbo_id},{"$set":{key:value}})
        
        logger.info('vbo_id:%s update %s:%s' % (vbo_id,key,value))
        
    #更新微博信息
    def updateVboInfos(self,vbo_id,key_value):
        con=self.mongo.db[self.VBO_VBO_CONTENT_TABLE]
        
        con.update({"WeiboID":vbo_id},{"$set":key_value})
        
        logger.info('vbo_id:%s update %s' % (vbo_id,key_value))
    
    # 查看一条微博的评论是否存在
    def commentExixts(self, vbo_id, comment_id):
        con = self.mongo.db[self.VBO_VBO_COMMENTS_TABLE]
        if con.find_one({"WeiboID":vbo_id, 'Commments':comment_id}, {"WeiboID":1}):
            return True
        return False
    
    # 存入一条新的微博评论
    def addNewComment(self, vbo_id, comment):
        collect_time = time.strftime("%Y-%m-%d %X", time.localtime())
        comment['CollectTime'] = collect_time
        comment['Quality'] = '正常'
        comment['Character'] = '中性'
        # 将评论内容加入微博表 
        con = self.mongo.db[self.VBO_VBO_CONTENT_TABLE]
        con.update({"WeiboID":vbo_id}, {'$push':{"Comments":comment}})
        # 将评论id加入评论表
        con = self.mongo.db[self.VBO_VBO_COMMENTS_TABLE]
        con.update({"WeiboID":vbo_id}, {'$push':{"Comments":comment["WeiboID"]}})
        
        logger.debug("vbo_id:%s add one comment %s" % (vbo_id, comment))
    
    # 获取这个时间点应该更新的微博
    def getNeedUpdateVo(self, update_time):
        con = self.mongo.db[self.VBO_VBO_COMMENT_UPDATE_TABLE]

        second = 7*24 * 60*60
        currentSecond = int(time.time())
        beforeSecond = currentSecond - second
        before_time=time.strftime("%Y-%m-%d %X", time.localtime(beforeSecond))
        current_time=time.strftime("%Y-%m-%d %X", time.localtime(currentSecond))

        return [comment_id_url for comment_id_url in con.find({"CreateTime":{"$gte":before_time},"NextUpdateTime":{"$lt":update_time},"Accounts":{"$in":NEED_UPDATE_ACCOUNTS}})]

        
    # 从mongo里获取一条微博
    def fromMongoGetOneVbo(self, vbo_id):
        con = self.mongo.db[self.VBO_VBO_CONTENT_TABLE]
        
        vbo = con.find_one({"WeiboID":vbo_id}, {"_id":0})
        
        if vbo is None:
            logger.error("%s vbo not found" % vbo_id)
        return vbo
    
    
    
    
    #以下为微博关注相关
    
    #获取需要关注的微博
    def getNeedFocusWeibos(self):
        
        con=self.mongo.db[self.VBO_VBO_FOCUS_VBO]
        
        weibos=con.find({"$or":[{"status":{"$exists":False}},{"status":{"$ne":1}}]})
        
        return [weibo for weibo in weibos]
     
    #更新一条关注微博的信息
    def updateFocusWeiboInfo(self,account,key_values):
        
        con=self.mongo.db[self.VBO_VBO_FOCUS_VBO]
        
        con.update({"account":account},{"$set":key_values})
        
        logger.info('account:%s update %s' % (account,key_values))
    
    
    #查看一个关注微博是否已经存在，不存在则保存
    def focusWeiboUserExists(self,focusWeibo):
        if self.mongo.db[self.VBO_VBO_FOCUS_VBO].find_one({'account':focusWeibo['account']},{"account":1}):
            return True
        
        self.saveFocusVboUserToMongo(focusWeibo)
        return False
    
    
    # 将微博存入mongo
    def saveFocusVboUserToMongo(self, focusVbo):
        # 深度拷贝，然后将Comments制空，方便后面的评论更新
        copy_focusVbo = copy.deepcopy(focusVbo)
        focusVbo['create_time'] = time.strftime("%Y-%m-%d %X", time.localtime())
        self.mongo.insert_value(copy_focusVbo,self.VBO_VBO_FOCUS_VBO)
        logger.info("%s save to mongo" % copy_focusVbo)
    
    
        
    # 将类似于20万这样的转换为数字
    def digitaUnitToNum(self, digita):
        num = -1
        numPattern = re.search('(\d+)', digita)
        if numPattern:
            num = int(numPattern.group(numPattern.lastindex))
        
        # 为0则直接返回
        if num == 0:
            return num
        
        unit = '1'
        unitPattern = re.search('(亿|千万|百万|万|千)', digita)
        if unitPattern:
            unit = unitPattern.group(unitPattern.lastindex)
        elif num == -1:
            # 没有获取到数字且没有获取到单位
            return 0
        else:
            # 没有获取到单位，直接返回数字
            return num
        
        num = 1 if num == -1 else num
        
        unit_num = {'亿':100000000, '千万':10000000, '百万':1000000, '万':10000, '千':1000}
        
        return num * unit_num[unit]
         
    
    # 获取一个node的文本或属性
    def getNodeText(self, method, path, pattern=None, default=None, raiseException=False, attribute=None):
        ele = self.find_element(method, path, None, raiseException)
        if ele is None:
            return default
        text = ''
        if attribute:
            text = ele.get_attribute(attribute)
        else:
            text = ele.text
        
        if text is None:
            return default
        
        if pattern is None:
            return text
        p = re.search(pattern, text)
        if p:
            return p.group(p.lastindex)
        return default
    
    
    
        
    def myjoin(self, base, url):
        url1 = urljoin(base, url)
        arr = urlparse(url1)
        path = normpath(arr[2])
        return urlunparse((arr.scheme, arr.netloc, path, arr.params, arr.query, arr.fragment))
    
    def close(self):
        self.driver.close()
        self.mongo.close()
    
    # 将微博上传    
    def http_post(self, url, values):
        jdata = json.dumps(dict(values))
        data = jdata.decode("unicode_escape").encode("utf-8")
        headers = {"Content-type": "application/json"}
        request = urllib2.Request(url, data, headers)
        try:
            response = urllib2.urlopen(request, timeout=120)
            logging.info("This item is: %s" % data)
        except Exception, msg:
            print data
            logger.error("post json error : %s" % msg)
        else:
            responsecode = response.getcode()
            logger.info("response code is: %s" % responsecode)
            
            
    def login(self):
        
        if self.isLogin():
            return
        
        
        self.get('http://weibo.com/login.php')
        
        
        try:
            username=self.find_element(self.driver.find_element_by_name, 'username')
            self.input_key(username, self.username)
            password=self.find_element(self.driver.find_element_by_name, 'password')
            self.input_key(password, self.passwd)
            
            self.click(self.find_element(self.driver.find_element_by_xpath, '//*[@node-type="submitBtn"]'))
        except:
            pass
        finally:
            if self.isLogin():
                return
            while True:
                if self.isLogin():
                    return
                time.sleep(7)
        logger.info('loggin finish')
        
    def isLogin(self):
        
        try:
            self.find_element(self.driver.find_element_by_xpath, '//*[@nm="home"]', None, True)
        except:
            return False
        else:
            return True
                
        
    def _verify(self):
        
        pass
    
    def click(self, web_element):
        web_element.click()
        time.sleep(5)
    
    def wait_element_load(self, method, path, timeout=3, raiseException=True):
        begin = time.time()
        while True:
            if self.find_element(method, path, None, False):
                return True
            clock = time.time()
            if clock - begin > timeout:
                logger.error("%s path not on time load" % path)
                if raiseException:
                    raise Exception('%s path not on time load' % path)
                return False
            time.sleep(1)
    
    def get(self, url):
        
        logger.info("get %s" % url)
        self.driver.get(url)
        time.sleep(5)
    
    #向一个输入框输入值
    def input_key(self,web_element,value):
        web_element.clear()
        web_element.send_keys(value)
    
    def find_element(self, method, path, default=None, raiseException=True):
        try:
            element = method(path)
        except Exception, msg:
            if raiseException:
                raise Exception(path + ' not find,%s' % msg)
            element = default
        return element
    
    # 格式化 10秒前，10分钟前，10小时前 等时间格式
    def analysis_time(self, source):
        def beforeSecond(second):
            second = int(second)
            currentSecond = int(time.time())
            beforeSecond = currentSecond - second
            return time.strftime("%Y-%m-%d %X", time.localtime(beforeSecond))
        def beforeMinute(minute):
            second = int(minute) * 60
            currentSecond = int(time.time())
            beforeSecond = currentSecond - second
            return time.strftime("%Y-%m-%d %X", time.localtime(beforeSecond))
        def beforeHour(hour):
            second = int(hour) * 60 * 60
            currentSecond = int(time.time())
            beforeSecond = currentSecond - second
            return time.strftime("%Y-%m-%d %X", time.localtime(beforeSecond))
        def today(t):
            date=time.strftime('%Y-%m-%d', time.localtime())
            return '%s %s:00' %(date,t)
        def date_(date):
            if re.match('\d+月\d+日 \d+:\d+\s*'.decode('utf8'), date):
                date = date.replace('月'.decode('utf8'), '-').replace("\s*$","")
                date = date.replace('日'.decode('utf8'), '-').replace("\s*$","")
                return "%s-%s:00" % (time.strftime('%Y', time.localtime()), date)
            elif re.match('\d+年\d+月\d+日 \d+:\d+\s*'.decode('utf8'), date):
                date = date.replace('年'.decode('utf8'), '-').replace("\s*$","")
                date = date.replace('月'.decode('utf8'), '-').replace("\s*$","")
                date = date.replace('日'.decode('utf8'), '-').replace("\s*$","")
                return "%s:00" % date
            else:
                logger.error('unknow date format %s' % date)
                return time.strftime('%Y-%m-%d %X', time.localtime())
        #source=source.decode('utf8')
        pattern=re.search('(\d+)\s*秒前'.decode('utf8'), source)
        if pattern:
            datetime = beforeSecond(pattern.group(pattern.lastindex))
            return datetime
        pattern=re.search('(\d+)\s*分钟前'.decode('utf8'), source)
        if pattern:
            datetime = beforeMinute(pattern.group(pattern.lastindex))
            return datetime
        pattern=re.search('(\d+)\s*小时前'.decode('utf8'),source)
        if pattern:
            datetime = beforeHour(pattern.group(pattern.lastindex))
            return datetime
        pattern=re.search('今天\s*(\d{1,2}:\d{1,2})'.decode('utf8'),source)
        if pattern:
            t=today(pattern.group(pattern.lastindex))
            return t
        else:
            datetime = date_(source)
            return datetime
    #文件夹不存在时创建
    def create_directory(self,directory):
        if not os.path.isdir(directory):
            os.makedirs(directory)
