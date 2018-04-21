# -*- coding: utf-8 -*-
'''
Created on 2015年10月12日

@author: rhc
'''
import sys
import os
from selenium import webdriver

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
from vbo3.mongo import Mongo
from vbo3.selenium_vbo import SeleniumVbo

import time,json,logging



logging.basicConfig(filename='log.log', format='[%(asctime)s]%(levelname)s:%(message)s', filemode='a',stream=True,level='INFO')
logger=logging.getLogger(__name__)

class SeleniumVboVbo(SeleniumVbo):
    
    debug=False

    alreadyCatch = set()

    def __init__(self):
        option=webdriver.ChromeOptions()
        user_directory='d:chrome-cache/vbovbo-%s/user-data-dir-chrome'%time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
        cache_directory='d:chrome-cache/vbovbo-%s/disk-cache-dir-chrome'%time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
        self.create_directory(user_directory)
        self.create_directory(cache_directory)
        option.add_argument('--user-data-dir=%s'%user_directory)
        option.add_argument('--disk-cache-dir=%s'%cache_directory)
        option.add_argument('–disk-cache-size=1048576')
        #option.add_argument('--single-process')
        option.add_argument('--first run')
        self.driver=webdriver.Chrome(chrome_options=option)
        self.mongo=Mongo()

    def catchVboList(self):
        
        vbolist=[]
        try:
            self.loadFirstPage()
            while(self.has_nextpage):
                
                self.has_nextpage= True if self.needLoadAllVbo() else False
                
                if self.has_nextpage:
                    self.loadOnePageAllVbo()
                    self.movePagehead()
                
                onePageVboList=self.getOnePageVboList()
                
                #vbolist.extend(onePageVboList)
                if self.has_nextpage and self.nextPage():
                    continue
                break
        except Exception,msg:
            logger.error(msg)
            if self.debug:
                raise Exception
        finally:
            self.alreadyCatch.clear()
        return vbolist

    #获取到已经抓取的id的xpath识别条件
    def getAlreadyCatchIdNotXPath(self):
        
        notXpath=''
        for x in self.alreadyCatch:
            notXpath += (' and @mid != "%s" ') % x
        return notXpath

    #获取一页微博
    def getOnePageVboList(self):
        list=self.find_element(self.driver.find_elements_by_xpath,'//*[@node-type="feed_list"]/div[@action-type="feed_list_item" and not(@feedtype) %s ]' % self.getAlreadyCatchIdNotXPath())
        vbolist=[]
        next_vbo=True
        for vbo in list:
            try:
                #这里先抓取原创微波再抓取转发的微波,但抓取完原创微波还是需要将鼠标移动到微波节点,不然不能获取到人物属性,不先抓取转发微波是因为之后再抓取原创微波会有问题
                
                is_forwards=[False,True] if self.getNodeText(vbo.find_element_by_xpath, '.', None, None, False, 'isforward') else [False]
                for is_forward in is_forwards:
                    #必须先将该条微波置于屏幕中央,否则获取不到人物信息会导致抓取该条微波失败
                    contentElement=self.find_element(vbo.find_element_by_xpath,'.//div[@node-type="feed_list_reason"]' if is_forward else './/div[@node-type="feed_list_content"]')
                    self.mouseOverElement(contentElement)
                    content=self.getOneVbo(vbo,is_forward)
                    #由于微博改版会获取到本次已经抓取的微波
                    if content['WeiboID'] in self.alreadyCatch:
                        continue
                    self.alreadyCatch.add(content['WeiboID'])

                    self.cancelShowUser(vbo)
                    result=self.addExtrasInfoToVo(content)
                    #如果抓取的是转发的微博则存在也不会停止
                    if not is_forward and self.vboExists(content):
                        logger.info("%s exist,stop update" % content)
                        next_vbo=False
                        break
                
                    self.http_post(self.post_url, result)
                
                    vbolist.append(result)
                
                if not next_vbo:
                    self.has_nextpage=False
                    break
            except Exception,msg:
                
                logger.error(msg)
                if self.debug:
                    raise Exception
                
                continue
         
        return vbolist   
    
    #加载个人首页
    def loadFirstPage(self):
        firstPageBtn=self.find_element(self.driver.find_element_by_xpath, '//a[@nm="home"]', None, True)
        self.click(firstPageBtn)
    
    #移动鼠标，加载整个页面
    def loadOnePageAllVbo(self):
        for i in range(0,10):
            
            footer=self.find_element(self.driver.find_element_by_xpath, '//*[@class="footer_link clearfix"]', None, False)
            if footer:
                self.driver.execute_script("arguments[0].scrollIntoView();", footer)
            
            if self.find_element(self.driver.find_element_by_xpath, '//*[@class="more_txt W_f14"]', None, False):
                return
            time.sleep(5)
        raise Exception('load all vbo list fail')
    
    #是否需要加载整页数据，当获取到的id中有一个存在时说明不需要加载整个页面
    def needLoadAllVbo(self):
        list=self.find_element(self.driver.find_elements_by_xpath,'//*[@node-type="feed_list"]/div[@action-type="feed_list_item" and not(@feedtype) %s ] '% self.getAlreadyCatchIdNotXPath())
        
        vboIdList=[]
        
        if list:
            for vbo in list:
                vboId=self.getVboId(vbo, vbo, False)
                if vboId and vboId not in self.alreadyCatch:
                    vboIdList.append(vboId)
        
        if len(vboIdList):
            return not self.vboIdListHaveExists(vboIdList)
        return False
    
    #移动到页面顶部
    def movePagehead(self):
        pageHeadElement=self.find_element(self.driver.find_element_by_xpath, '//*[@id="v6_pl_content_publishertop"]', None, True)
        self.mouseOverElement(pageHeadElement)
    
    #加载下一页
    def nextPage(self):
        if self.current_page>self.MAX_PAGE:
            return False
        else:
            self.current_page+=1
        try:
            self.click(self.find_element(self.driver.find_element_by_xpath, '//a[@class="WB_cardmore WB_cardmore_noborder clearfix"]', None, True))
            
        except Exception,msg:
            logger.error('load next page error, %s' % msg)
            if self.debug:
                raise Exception
            return False
        return True
    
    #获取一条微博，当获取的是该条微博转发的微博时is_forward为True
    def getOneVbo(self,web_element,is_forward=False):
        
        weibo_location=''
        topic_name=''
        vbo={}
        
        vbo['Images']=self.catchVboContentPic(web_element, vbo, is_forward)
        vbo['Videos']=self.catchVboContentVideo(web_element, vbo, is_forward)
        vbo['WeiboID']=self.getVboId(web_element, vbo, is_forward)
        vbo['ParentID']=self.getVboParentId(web_element, vbo, is_forward)
        vbo['WeiboKind']=self.getVboKind()
        vbo['WeiboType']=self.getVboType(web_element, is_forward)
        vbo['From']=self.getVboFrom(web_element, vbo, is_forward)
        vbo['Content']=self.getVboContent(web_element,vbo,is_forward).replace('\n','').replace('\r\n','').replace('\t','')
        vbo['WeiboLocation']=weibo_location
        vbo['TopicName']=topic_name
        vbo['IsOriginality']= True if vbo['WeiboType']=='原创' else False 
        vbo['CreateTime']=self.getVboCreatetime(web_element, vbo, is_forward)
        vbo['CommentUrl']=self.getVboCommentUrl(web_element, vbo, is_forward)
        vbo['CommentNum']=self.getVboCommentNum(web_element, vbo, is_forward)
        vbo['Retweet']=self.getVboRetweet(web_element, vbo, is_forward)
        vbo['PraisedCount']=self.getVboGoodnum(web_element, vbo, is_forward)
        vbo['Author']=self.getVboAuthor(web_element, vbo, is_forward)
        
        #如果是获取的是转载的微博的评论，直接是空数组，否则先查看评论个数
        #如果抓取评论容易弹窗
        #comments=[] if is_forward else ( [] if vbo['CommentNum']==0 else self.getVboCommentFromNode(web_element,vbo) )
        comments=[]
        vbo['Comments']=comments
        
        logger.debug("fetch one vbo ")
        
        return vbo
    
    #获取微博id
    def getVboId(self,web_element,vbo,is_forward=False):
        
        vbo_id=self.getNodeText(web_element.find_element_by_xpath, '.', None, '0', True, 'omid' if is_forward else 'mid')
        return vbo_id
    
    #获取转发的微博的id
    def getVboParentId(self,web_element,vbo,is_forward=False):
        
        parent_id='' if is_forward else self.getNodeText(web_element.find_element_by_xpath, '.', None, '', False, 'omid')
        return parent_id
        
    #去识别一条微博是转载或下载里面的图片等
    def getVboContent(self,web_element,vbo,is_forward=False):
        xpath='.//div[@node-type="feed_list_reason"]' if is_forward else './/div[@node-type="feed_list_content"]'
        content=self.getNodeText(web_element.find_element_by_xpath, xpath, None, '', True).replace('"','\"')
        
        return content
    
    #下载微博里的图片
    def catchVboContentPic(self,web_element,vbo,is_forward=False):
        xpath= './/div[@class="WB_detail"]/div[@node-type="feed_list_media_prev"]//div[@node-type="fl_pic_list"]//img[@action-type="fl_pics"]' if is_forward==False else './/div[@node-type="feed_list_forwardContent"]/div[@node-type="feed_list_media_prev"]//div[@node-type="fl_pic_list"]//img[@action-type="fl_pics"]'
        
        picElements=self.find_element(web_element.find_elements_by_xpath, xpath, None, False)
        
        if picElements is None:
            logger.debug('no image')
            return []
        
        picSrcs=[picElement.get_attribute('src').replace('square','bmiddle') for picElement in picElements]
        
        logger.debug('find %s picture' % len(picSrcs))
        
        picDetail=self.downloadVboImagesFile(picSrcs, self.driver.current_url)
        
        logger.debug('download %s picture' % len(picDetail))
        
        return picDetail
    
    #下载微博里的视频
    def catchVboContentVideo(self,web_element,vbo,is_forward=False):
        
        return []
    
    #发出微博时间    
    def getVboCreatetime(self,web_element,vbo,is_forward=False):
        xpath= './/div[@class="WB_feed_expand"]//a[@node-type="feed_list_item_date"]' if is_forward else './/div[@class="WB_detail"]/div[@class="WB_from S_txt2"]//a[@node-type="feed_list_item_date"]'
        create_time=self.getNodeText(web_element.find_element_by_xpath, xpath, None, '', True, 'title')   
        
        return create_time + ':00'
        
    
    #获取微博类型
    def getVboType(self,web_element,is_forward=False):
        
        is_forward=None if is_forward else self.getNodeText(web_element.find_element_by_xpath, '.', None, None, False, 'isforward')
        if is_forward:
            return '转载'
        return '原创'
    
    #获取发出微博的应用名
    def getVboFrom(self,web_element,vbo,is_forward=False):
        xpath= './/div[@class="WB_feed_expand"]//a[@action-type="app_source"]' if is_forward else './/div[@class="WB_detail"]/div[@class="WB_from S_txt2"]//a[@action-type="app_source"]'
        _from=self.getNodeText(web_element.find_element_by_xpath, xpath, None, '', False)
        return _from
    
    #获取微博的详情url
    def getVboCommentUrl(self,web_element,vbo,is_forward=False):
        
        xpath= './/div[@class="WB_feed_expand"]//a[@node-type="feed_list_item_date"]' if is_forward else './/div[@class="WB_detail"]/div[@class="WB_from S_txt2"]//a[@node-type="feed_list_item_date"]'
        comment_url=self.getNodeText(web_element.find_element_by_xpath, xpath, None, '', True, 'href')
        
        return comment_url
    
    #获取微博评论个数
    def getVboCommentNum(self,web_element,vbo,is_forward=False):
        xpath='.//div[@class="WB_feed_expand"]//em[@class="W_ficon ficon_repeat S_ficon"]/following-sibling::em[1]' if is_forward else './div[@class="WB_feed_handle"]//em[@class="W_ficon ficon_repeat S_ficon"]/following-sibling::em[1]'
        comment_num=int(self.getNodeText(web_element.find_element_by_xpath, xpath, '(\d+)', 0))
        
        return comment_num
    
    #获取微博转发数
    def getVboRetweet(self,web_element,vbo,is_forward=False):
        xpath= './/div[@class="WB_feed_expand"]//em[@class="W_ficon ficon_forward S_ficon"]/following-sibling::em[1]' if is_forward else './div[@class="WB_feed_handle"]//em[@class="W_ficon ficon_forward S_ficon"]/following-sibling::em[1]'
        retweet=int(self.getNodeText(web_element.find_element_by_xpath, xpath, '(\d+)', 0))
        
        return retweet
    
    #获取微博点赞数
    def getVboGoodnum(self,web_element,vbo,is_forward=False):
        xpath= './/div[@class="WB_feed_expand"]//em[@class="W_ficon ficon_praised S_txt2"]/following-sibling::em[1]' if is_forward else './div[@class="WB_feed_handle"]//em[@class="W_ficon ficon_praised S_txt2"]/following-sibling::em[1]'
        good_num=int(self.getNodeText(web_element.find_element_by_xpath, xpath, '(\d+)', 0))
        
        return good_num
    
    #获取微博的作者信息
    def getVboAuthor(self,web_element,vbo,is_forward=False):
        xpath= './/div[@node-type="feed_list_forwardContent"]/div[@class="WB_info"]/a[@usercard]' if is_forward else './/div[@node-type="feed_content"]/div[@class="WB_detail"]/div[@class="WB_info"]/a[@usercard]'
        
        author=self.catchUserInfo(web_element.find_element_by_xpath,xpath,'00')
        
        return author
    
    def getVboKind(self):
        return self.vbo_kind
    
    def refresh(self):
        self.has_nextpage=True
        self.current_page=1
    
    def crond(self):
        while True:
            logger.info("更新开始")
            self.login()
            self.catchVboList()
            self.refresh()
            logger.info("更新结束")
            #暂停一小时
            time.sleep(1800)
    
if  __name__ =='__main__':
    vbo=SeleniumVboVbo()
    vbo.crond()
