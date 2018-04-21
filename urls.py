# -*- coding: utf-8 -*-
'''
Created on 2015年12月22日

@author: rhc
'''


import time, json, base64, logging, hashlib,json,sys
from datetime import datetime, tzinfo, timedelta

from transwarp.web import ctx, get, post, route, seeother, jsonresult, forbidden, Template
from selenium_vbo_mongo import SeleniumVboMongo
from selenium_vbo_focus_account import SeleniumVboFocusAccount

default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)
logging.basicConfig(filename='focus_weibo_log.log', format='[%(asctime)s]%(levelname)s:%(message)s', filemode='a',stream=True,level='INFO')
logger=logging.getLogger(__name__)

seleniumVboMongo=SeleniumVboMongo()
#seleniumVboFocusAccount=SeleniumVboFocusAccount()
#seleniumVboFocusAccount.login()
logger.info("start server")

@post('/addFocusWeiboUser')
@jsonresult
def test():
    global seleniumVboMongo
    request=ctx.request
    data=request.get_raw_data()
    logger.info("trans data %s"%data)
    try:
        vboUsers = json.loads(data)
        
        for vboUser in vboUsers:
            exist=seleniumVboMongo.focusWeiboUserExists(vboUser)
            
    except Exception,e:
        logger.error(" 增加关注账号失败，错误为 %s" % e)
        return {'status':500,'message':e.tostring()};
    else:
        return {"status":200,'message':''}