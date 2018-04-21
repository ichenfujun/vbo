# -*- coding: utf-8 -*-
'''
Created on 2015年9月28日

@author: rhc
'''

import sys,os
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
import time,logging,os,hashlib,requests
from selenium import webdriver
from vbo3.mongo import Mongo
from vbo3.selenium_vbo_mongo import SeleniumVboMongo
from selenium.webdriver.common.action_chains import ActionChains
import ossutils

logging.basicConfig(filename='log.log', format='[%(asctime)s]%(levelname)s:%(message)s', filemode='a',stream=True,level='INFO')
logger=logging.getLogger(__name__)

APP_CODE="zhiyun-portal"
COMPANY_ID="cdvcloud"
USER_ID="spider"


class SeleniumVbo(SeleniumVboMongo):
    
    debug=False
    
    username='wangfuxiang@cdvcloud.com'
    passwd='wfx0713'
    MAX_PAGE=5
    current_page=1
    has_nextpage=True
    post_url='http://mcp.smg.cdvcloud.com/ca/import'
    vbo_kind='新浪微博'
    
    BASE_STORE='D:/sinavbo'
    
    BASE_IMAGES_STORE=BASE_STORE+'/pic'
    IMAGES_STORE='/sinavbo/pic'
    
    BASE_VIDEOS_STORE=BASE_STORE+'/video'
    VIDEOS_STORE='/sinavbo/video'
    
    BASE_HEADPIC_STORE=BASE_STORE+'/headpic'
    HEADPIC_STORE='/sinavbo/headpic'
    
    def __init__(self):
        self.driver=webdriver.Chrome()
        self.mongo=Mongo()
    
    #附加信息
    def addExtrasInfoToVo(self, vbolist):
        timearray = time.strptime(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), "%Y-%m-%d %H:%M:%S")
        currenttime = int(time.mktime(timearray)) * 1000
        temp = '%s%s%s' % ('7ac879e71becb992f3dba8459cc06f61', '80347', currenttime)
        verifycode = self.getMd5Str(temp)
        
        result={}
        result["SubscribeID"] = ""
        result["StorageType"] = ""
        result["SecurityCertificate"] = {"userId": "cdvcloud",
                                       "appKey": "5435c69ed3bcc5b2e4d580e393e373d3",
                                       "randomId": "80347",
                                       "currentTime": currenttime,
                                       "verifyCode": verifycode}
        
        vbolist = vbolist if isinstance(vbolist, list) else [vbolist]
        
        result["WBs"] = vbolist
        
        collect_time=time.strftime("%Y-%m-%d %X", time.localtime())
        
        for vbo in vbolist:
            vbo['CollectTime']=collect_time
            vbo['Quality']='正常'
            vbo['Character']='中性'
            
            for comment in vbo['Comments']:
                comment['CollectTime']=vbo['CollectTime']
                comment['Quality']=vbo['Quality']
                comment['Character']=vbo['Character']
        
        result['News']=[]
        return result
    
    #单给评论列表加上附加信息
    def addCommentExtrasInfo(self,comment):
        
        if comment is None:
            return
        
        collect_time=time.strftime("%Y-%m-%d %X", time.localtime())
        quality='正常'
        character='中性'
        comment['CollectTime']=collect_time
        comment['Quality']=quality
        comment['Character']=character
        
    
    def getMd5Str(self, strs):
        m = hashlib.md5()
        m.update(strs)
        md5Str = m.hexdigest()
        return md5Str
    
    
    
    def getCommentType(self,web_element):
        return '评论'
    
    def getCommentIsOriginality(self,web_element):
        return True
    
    def getCommentContent(self,web_element,comment):
        content=self.getNodeText(web_element.find_element_by_xpath, './/*[@class="WB_text"]', None, '', True)
        return content
    
    #移动鼠标到指定元素上
    def mouseOverElement(self,web_element):
        #mouseHoverjs = "var evObj = document.createEvent('MouseEvents');evObj.initMouseEvent('mouseover',true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);arguments[0].dispatchEvent(evObj);"
        mouseHoverjs="""
                var evt = document.createEvent("MouseEvents");
                evt.initMouseEvent("mouseover",true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                
                return arguments[0].dispatchEvent(evt);
            
        """ 
        self.driver.execute_script(mouseHoverjs,web_element)
        
        ActionChains(self.driver).move_to_element(web_element).perform()
        
        time.sleep(2)
    
    #用于取消显示用户信息
    def cancelShowUser(self,web_element):
        xpath='.//a[@action-type="fl_menu"]/i'
        element=self.find_element(web_element.find_element_by_xpath,xpath,None,False)
        
        if element:
            self.mouseOverElement(element)
    
    #传入元素的方法和要寻找的元素的路径    
    def catchUserInfo(self,method,path,user_id):
        #先获取到头像标签，然后将鼠标移到头像会悬浮出个人信息
        face_element=self.find_element(method, path, None, True)
        
        self.mouseOverElement(face_element)
        self.mouseOverElement(face_element)
        time.sleep(1)
        
        self.wait_element_load(self.driver.find_element_by_xpath, '//body/div[@class="W_layer W_layer_pop "]//div[@class="nc_content"]', 15)
        
        userDiv=self.find_element(self.driver.find_element_by_xpath, '//body/div[@class="W_layer W_layer_pop "]//div[@class="layer_personcard"]', None, False)
        
        if userDiv is None:
            logger.error('catch user info error %s'%user_id)
            return None
        
        accounts=self.getNodeText(userDiv.find_element_by_xpath, './/div[@class="mask"]/div[@class="name"]/a[@uid]', None, '0', True, 'uid')
        nick_name=self.getNodeText(userDiv.find_element_by_xpath, './/div[@class="mask"]/div[@class="name"]/a[@uid]', None, '0', True, 'title')
        author_location=self.getNodeText(userDiv.find_element_by_xpath, './/a[@class="interval W_autocut S_txt1"]', None, '', False, 'title')
        is_vip=False
        is_ent=False
        discription=self.getNodeText(userDiv.find_element_by_xpath, './/div[@class="mask"]/div[@class="intro W_autocut"]/span', None, '', False, 'title')
        tag=discription
        verify_info=self.getNodeText(userDiv.find_element_by_xpath, './/a[@href="http://verified.weibo.com/verify"]/i', None, '', False, 'class')
        if verify_info=='W_icon icon_approve_co':
            verify_info='微博机构认证'
        elif verify_info=='W_icon icon_approve':
            verify_info='微博个人认证'
        elif verify_info=='W_icon icon_pf_approve':
            verify_info='微博自媒体认证'
        
        fans_num=self.digitaUnitToNum(self.getNodeText(userDiv.find_element_by_xpath, './/span[@class="c_fans W_fb"]//em', None, 0, False))
        
        idol_num=self.digitaUnitToNum(self.getNodeText(userDiv.find_element_by_xpath, './/span[@class="c_follow W_fb"]//em', None, 0, False))
        
        tweet_num=self.digitaUnitToNum(self.getNodeText(userDiv.find_element_by_xpath, './/span[@class="c_weibo W_fb"]//em', None, 0, False))
        
        register_time='2010-01-01 00:00:00'
        head_pic_path=self.downloadHeadPic(userDiv.find_element_by_xpath, './/img[@imgtype="head"]')
        
        userInfo={}
        userInfo['Accounts']=accounts
        userInfo['NickName']=nick_name
        userInfo['AuthorLocation']=author_location
        userInfo['IsVip']=is_vip
        userInfo['IsEnt']=is_ent
        userInfo['Discription']=discription
        userInfo['Tag']=tag
        userInfo['VerifyInfo']=verify_info
        userInfo['FansNum']=fans_num
        userInfo['IdolNum']=idol_num
        userInfo['TweetNum']=tweet_num
        userInfo['RegisterTime']=register_time
        userInfo['HeadPicPath']=head_pic_path
        
        return userInfo
    
    
    #下载头像
    def downloadHeadPic(self,method,xpath):
        picSrc=self.getNodeText(method, xpath, None, None, True, 'src')
        image_url = picSrc
#         image_id = self.getMd5Str(image_url)
#         image_file_name = image_id + '.jpg'
#         image_path = '%s/%s' % (self.HEADPIC_STORE, image_file_name)
#         file_path = '%s/%s' % (self.BASE_HEADPIC_STORE, image_file_name)
        
        if not os.path.exists(self.BASE_HEADPIC_STORE):
                os.makedirs(self.BASE_HEADPIC_STORE)
        
        image_path=self.downloadFileNews(image_url, self.BASE_HEADPIC_STORE)
        
#         self.downloadFile(image_url, file_path, self.driver.current_url)
        
        return image_path 
        
    #下载图片到指定文件夹
    def downloadVboImagesFile(self,image_urls,referer):
        image_detail=[]
        if image_urls:
            date_dir = time.strftime('%Y%m%d', time.localtime(time.time()))
            sub_dir_path='%s/%s' % (self.IMAGES_STORE,date_dir)
            dir_path = '%s/%s' % (self.BASE_IMAGES_STORE,date_dir)
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            for image_url in image_urls:
                
                download_image = {}
                image_url = self.myjoin(referer, image_url);
                image_id = self.getMd5Str(image_url)
                image_file_name = image_id + '.jpg'
                
                image_path=self.downloadFileNews(image_url, dir_path)
                
                if image_path is None or len(image_path)==0:
                    logger.error(" %s 下载失败" % image_url)
                    continue
                
#                 image_path = '%s/%s' % (sub_dir_path ,image_file_name)
#                 file_path = '%s/%s' % (dir_path, image_file_name)
#                 #下载原图
#                 source=self.downloadFile(image_url, file_path, referer)
                
                #下载原图失败
#                 if(not source):
#                     logger.debug(" %s 下载失败" % image_url)
#                     continue
                
                thumbnail_image_url=image_url.replace('bmiddle','square')
                thumbnail_image_id=self.getMd5Str(thumbnail_image_url)
                thumbnail_file_name=thumbnail_image_id+'.jpg'
                
                thumbnail_image_path=self.downloadFileNews(thumbnail_image_url, dir_path)
                
#                 thumbnail_image_path= '%s/%s' % (sub_dir_path,thumbnail_file_name)
#                 thumbnail_file_path='%s/%s' % (dir_path, thumbnail_file_name)
#                 #下载缩略图
#                 thumbnail=self.downloadFile(thumbnail_image_url, thumbnail_file_path, referer)
                
                #下载原图失败
#                 if(not thumbnail):
#                     logger.debug(" %s 下载失败" % thumbnail_image_url)
#                     continue
                
                download_image["ImageUrl"] = image_url
                download_image["ImageId"] = self.getMd5Str(image_url)
                download_image["FilePath"] = image_path
                download_image["ImageName"] = image_file_name
                download_image["ThumbnailPath"] = '' if thumbnail_image_path is None or len(thumbnail_image_path) == 0 else thumbnail_image_path
                image_detail.append(download_image)
        return image_detail
    
    #下载一个文件并上传到oss
    def downloadFileNews(self,url,dir_path):
        try:
            osspath = ossutils.upload(APP_CODE, COMPANY_ID, USER_ID, url, 1, dir_path)
            logger.debug("oss path is %s" % osspath)
            return osspath
        except Exception,e:
            logger.error("oss上传失败 %s" % e)
            return ''
    
    #下载一个文件到file_path,
    def downloadFile(self,url,file_path,referer=None):
        
        headers={'Referer':referer} if referer else {}
        try:
            with open(file_path, 'wb') as handle:
                    res = requests.get(url, headers=headers, stream=True, timeout=120)
                    for block in res.iter_content(1024):
                        if not block:
                            break
                        handle.write(block)
                    res.close()
        except Exception:
            if self.debug:
                raise Exception
            return False
        else:
            return True
    
    '''
    #打开微博的详情页再获取评论
    def getCommentFromCommentPage(self,web_element,vbo):
        
        self.click(self.find_element(web_element.find_element_by_xpath, './/*[@node-type="feed_list_item_date"]'))
        
        handles=self.driver.window_handles
        main_handle=self.driver.current_window_handle
        
        comment_handle=[h for h in handles if h!=main_handle][0]
        
        self.driver.switch_to_window(comment_handle)
        comments=[]
        try:
            while(True):
                if self.wait_element_load(self.driver.find_element_by_xpath, '//*[@comment_id]', 15)==False:
                    break
                comments.extend(self.getComment(self.find_element(self.driver.find_elements_by_xpath, '//*[@comment_id]'),vbo))
                next_page_btn=self.find_element(self.driver.find_element_by_xpath, '//a[@class="page next S_txt1 S_line1"]/span')
                if next_page_btn:
                    self.click(next_page_btn)
                else:
                    break
        finally:
            
            self.driver.close()
        
            self.driver.switch_to_window(main_handle)
        
        return comments
        
    '''
    #    
    def getComment(self,web_element_comment_list,vbo):
        
        comments=[]
        if web_element_comment_list is None:
            return comments
        
        for c in web_element_comment_list:
            try:
                co={}
                
                comment_id=self.getNodeText(c.find_element_by_xpath, '.', None, '0', True, 'comment_id')
                
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
                
                co['CreateTime']=self.analysis_time(time)
                
                co['CommentNum']=0
                co['Retweet']=0
                co['PraisedCount']=0
                co['Author']=author
                
                
                comments.append(co)
            
                logger.debug("fetch one comment")
            except Exception,msg:
                logger.error(msg)
                if self.debug:
                    raise Exception
            continue
        
        return comments
    
    def getCommentParrentId(self,web_element):
        return ''
    
    #从页面上获取评论    
    def getVboCommentFromNode(self,web_element,vbo):
        self.click(self.find_element(web_element.find_element_by_xpath, './/*[@node-type="comment_btn_text"]'))
        
        if self.wait_element_load(web_element.find_element_by_xpath, './/div[@node-type="feed_list_commentList"]', 15)==False:
            return []
        
        #获取所有的评论列表
        commentElementList=self.find_element(web_element.find_element_by_xpath, './/div[@node-type="feed_list_commentList"]', None, True)
        
        if self.find_element(commentElementList.find_element_by_xpath, './div[@class="between_line S_bg1"]', None, False):
            commentElementList=self.find_element(commentElementList.find_elements_by_xpath, './/div[@class="between_line S_bg1"]/following-sibling::div[@comment_id]', [], False)
        else:
            commentElementList=self.find_element(commentElementList.find_elements_by_xpath, './/div[@comment_id]', [], False)
        return self.getComment(commentElementList,vbo)
    
        
