# -*- coding: utf-8 -*-


import sys
import os
from selenium import webdriver
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from vbo3.mongo import Mongo
import logging,time
from vbo3.selenium_vbo_vbo import SeleniumVboVbo

logging.basicConfig(filename='commentlog.log', format='[%(asctime)s]%(levelname)s:%(message)s', filemode='a',stream=True,level='INFO')
logger=logging.getLogger(__name__)

class SeleniumVboComment(SeleniumVboVbo):

    username=''
    passwd=''
    
    MAX_PAGE=500

    debug=False

    def __init__(self):
        option=webdriver.ChromeOptions()
        user_directory='d:chrome-cache/vbocomment-%s/user-data-dir-chrome'%time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
        cache_directory='d:chrome-cache/vbocomment-%s/disk-cache-dir-chrome'%time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
        self.create_directory(user_directory)
        self.create_directory(cache_directory)
        option.add_argument('--user-data-dir=%s'%user_directory)
        option.add_argument('--disk-cache-dir=%s'%cache_directory)
        #option.add_argument('--single-process')
        option.add_argument('--first run')
        self.driver=webdriver.Chrome(chrome_options=option)
        self.mongo=Mongo()
    
    #从微博详情页获取comment
    def getCommentFromCommentPage(self,comment_url,vbo_id):
        
        self.driver.get(comment_url)
        
        self.updateVboData(vbo_id)
        #等待登陆
        #time.sleep(10)
        
        comments=[]
        try:
            for page in range(1,self.MAX_PAGE):
                
                #如果评论数位0
                
                if page==1 and int(self.getNodeText(self.driver.find_element_by_xpath, './/span[@node-type="comment_btn_text"]', '(\d+)', 0))==0:
                    break
                
                if self.wait_element_load(self.driver.find_element_by_xpath, '//*[@comment_id]', 15)==False:
                    break
                
                commentElementList=None
                if page==1:
                    #获取所有的评论列表de 父元素
                    commentElementList=self.find_element(self.driver.find_element_by_xpath, './/div[@node-type="comment_list"]', None, False)
                    
                    if commentElementList and self.find_element(commentElementList.find_element_by_xpath, './div[@class="between_line S_bg1"]', None, False):
                        #评论元素列表
                        commentElementList=self.find_element(commentElementList.find_elements_by_xpath, './/div[@class="between_line S_bg1"]/following-sibling::div[@comment_id]', [], False)
                    else:
                        commentElementList=self.find_element(self.driver.find_elements_by_xpath, '//*[@comment_id]',[],False)
                else:
                    commentElementList=self.find_element(self.driver.find_elements_by_xpath, '//*[@comment_id]',[],False)
                
                commentList=self.getDetailComment(commentElementList,vbo_id)
                comments.extend(commentList)
                
                #如果该页没有获取到评论则结束
                if self.has_nextpage==False or len(commentList)==0:
                    break
                
                next_page_btn=self.find_element(self.driver.find_element_by_xpath, '//a[@class="page next S_txt1 S_line1"]/span',None,False)
                if next_page_btn:
                    self.click(next_page_btn)
                else:
                    break
        except Exception,msg:
            logger.error("vbo_id:%s,comment_url:%s error %s" % (vbo_id,comment_url,msg))
            if self.debug:
                raise Exception
        return comments
    
    #从详情页获取comment，与直接从微博列表页获取评论不同的是从详情页获取的时候遇到已经存在的则停止获取
    def getDetailComment(self,web_element_comment_list,vbo_id):
        
        comments=[]
        if web_element_comment_list is None:
            return comments
        
        for c in web_element_comment_list:
            try:
                
                
                co={}
                
                comment_id=self.getNodeText(c.find_element_by_xpath, '.', None, '0', True, 'comment_id')
                
                if self.commentExixts(vbo_id, comment_id) or True:
                    self.has_nextpage=False
                    break
                
                #user_name=self.getNodeText(c.find_element_by_xpath, './/a[@usercard]', None, '', True)
                
                user_id=self.getNodeText(c.find_element_by_xpath, './/a[@usercard]', '=(\d+)', '', True, 'usercard')
                #content=self.getNodeText(c.find_element_by_xpath, './/*[@class="WB_text"]', None, '', True)
                
                #good_num=int(self.getNodeText(c.find_element_by_xpath, './/span[@node-type="like_status"]/em', '(\d+)', 0, False))
                
                time=self.getNodeText(c.find_element_by_xpath, './/div[@class="WB_from S_txt2"]', None, '', False)
        
                author=self.catchUserInfo(c.find_element_by_xpath,'.//div[@class="WB_text"]/a[@usercard]',user_id)
                
                co['WeiboID']=comment_id
                co['ParentID']=self.getCommentParrentId(c)
                co['WeiboKind']=self.getVboKind()
                co['WeiboType']=self.getCommentType(c)
                co['From']=''
                co['Content']=self.getCommentContent(c, co)
                co['WeiboLocation']=''
                co['TopicName']=''
                co['IsOriginality']=self.getCommentIsOriginality(c)
                
                #co['CreateTime']=time
                co['CreateTime']=self.analysis_time(time)
                
                co['CommentNum']=0
                co['Retweet']=0
                co['PraisedCount']=0
                co['Author']=author

                #当评论数据过多时插入mongo出错，先关闭了插入评论
                #self.addNewComment(vbo_id, co)
                
                comments.append(co)
            
                logger.debug("fetch one comment")
            except Exception,msg:
                logger.error(msg)
                if self.debug:
                    raise Exception
            
            continue
        
        return comments
    
    #更新微博的作者信息以及转发、评论数
    def updateVboData(self,vbo_id):
        try:
            self.wait_element_load(self.driver.find_element_by_xpath, '//div[@class="midbox clearfix"]', 7, True)
            author=self.catchUserInfo(self.driver.find_element_by_xpath, '//div[@class="midbox clearfix"]//a[@usercard]', '11')
            self.updateVboInfo(vbo_id, "Author", author)
        
            web_element=self.find_element(self.driver.find_element_by_xpath, '//div[@action-type="feed_list_item"]', None, True)
        
            retweet=self.getVboRetweet(web_element, None)
            comment_num=self.getVboCommentNum(web_element, None)
            good_num=self.getVboGoodnum(web_element, None)
            
            self.updateVboInfos(vbo_id, {"Retweet":retweet,"CommentNum":comment_num,"PraisedCount":good_num})
            '''
            self.updateVboInfo(vbo_id, "Retweet", retweet)
            self.updateVboInfo(vbo_id, "CommentNum", comment_num)
            self.updateVboInfo(vbo_id, "GoodNum", good_num)
            '''
        except Exception,msg:
            logger.error('update vbo:%s fail:%s' % (vbo_id,msg))
            if self.debug:
                raise Exception
        else:
            logger.info('update vob:%s success' % vbo_id)
    
    #开始更新微博
    def updateVbo(self):
        currentTime=int(time.time())
        
        needUpdateList=self.getNeedUpdateVo(currentTime)
        
        for commentInfo in needUpdateList:
            logger.info("%s begin update" % commentInfo["WeiboID"])
            updateCommentList=self.getCommentFromCommentPage(commentInfo['CommentUrl'], commentInfo['WeiboID'])
            
            self.updateVboUpdateTime(commentInfo['WeiboID'], len(updateCommentList))
            
            logger.info("%s update end,update %s comment" % (commentInfo['WeiboID'],len(updateCommentList)))

            #为了能在微波评论为0时依然更新
            if len(updateCommentList)>0 or True:
                vbo=self.fromMongoGetOneVbo(commentInfo['WeiboID'])
                if vbo:
                    result=self.addExtrasInfoToVo([vbo])
                    self.http_post(self.post_url, result)
            
    def crond(self):
        
        while(True):
            self.login()
            #等待登陆
            time.sleep(30)
            self.updateVbo()
            #暂停一小时
            time.sleep(1800)
    
        
if  __name__ =='__main__':
    vbo_comment=SeleniumVboComment()
    vbo_comment.crond()
    
