# -*-coding:utf-8 -*-

from weibo import APIClient
from weibo_code import *
import ossutils
import time
import json
import urllib2
import hashlib
import os
import re
import logging

APP_KEY = "3726251905"
APP_SECRET = "6673ae2beb1d836af4f9142802fa4357"
CALLBACK_URL = 'https://api.weibo.com/oauth2/default.html'
logging.basicConfig(filename='log.log', format='[%(asctime)s]%(levelname)s:%(message)s', filemode='a', stream=True,
                    level='INFO')
logger = logging.getLogger(__name__)


class WeiboCrawl():
    BASE_STORE = 'D:/sinavbo'
    BASE_IMAGES_STORE = BASE_STORE + '/pic'
    IMAGES_STORE = '/sinavbo/pic'
    BASE_HEADPIC_STORE = BASE_STORE + '/headpic'
    HEADPIC_STORE = '/sinavbo/headpic'

    def get_all_new_weibo(self):
        client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
        #         username = "chenfujun@toptimetech.com"
        #         password = "dajun19871104"
        #         API = SinaAPI(CALLBACK_URL, APP_KEY, CALLBACK_URL, username, password)
        #         code = API.get_code_Security()
        file_object = open('D:/weibo_code.txt')
        expires_in = file_object.read()
        #         requests = client.request_access_token(code)
        #         access_token = requests.access_token # 新浪返回的token，类似abc123xyz456
        #         expires_in = requests.expires_in
        client.set_access_token('2.006ctQRCL2yKEE588ff1b69a06mbKW', expires_in)
        statuses = client.statuses__friends_timeline(count=100)['statuses']
        for weiboJson in statuses:
            logging.info(weiboJson)
            self.parse_weibo(weiboJson)

    """
    @param weiboJson: 一条微博的详细信息，取出需要的字段拼接成OnAir数据格式
    """

    def parse_weibo(self, weiboJson):
        result = {}
        timearray = time.strptime(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), "%Y-%m-%d %H:%M:%S")
        currenttime = int(time.mktime(timearray)) * 1000
        temp = '%s%s%s' % ('7ac879e71becb992f3dba8459cc06f61', '80347', currenttime)
        verifycode = self.getMd5Str(temp)
        result["SubscribeID"] = ""
        result["StorageType"] = ""
        result["SecurityCertificate"] = {"userId": "cdvcloud",
                                         "appKey": "5435c69ed3bcc5b2e4d580e393e373d3",
                                         "randomId": "80347",
                                         "currentTime": currenttime,
                                         "verifyCode": verifycode}

        vbo_arry = []
        if 'retweeted_status' in weiboJson.keys():
            retweeted_status = weiboJson['retweeted_status']
            vbo1 = self.parse_detail(retweeted_status)
            result['WBs'] = vbo1
            result['News'] = []
            vbo_arry.append(result)

        vbo = self.parse_detail(weiboJson)
        logging.info("===============%s" % type(vbo))
        result['WBs'] = vbo
        result['News'] = []
        vbo_arry.append(result)
        for weibo in vbo_arry:
            self.http_post("http://mcp.smg.cdvcloud.com/ca/import", weibo)

    def parse_detail(self, weiboJson):
        weibo = []
        vbo = {}
        collect_time = time.strftime("%Y-%m-%d %X", time.localtime())
        try:
            vbo['Images'] = self.parse_image(weiboJson['pic_urls'])
        except:
            vbo['Images'] = []
        vbo['Videos'] = []
        vbo['WeiboID'] = weiboJson['id']
        vbo['WeiboKind'] = "新浪微博"
        weibo_type = self.get_vbo_type(weiboJson)
        vbo['WeiboType'] = weibo_type[0]
        vbo['ParentID'] = weibo_type[1]
        if 'source' in weiboJson.keys():
            vbo['From'] = self.remove_html_tag(weiboJson['source'])
        else:
            vbo['From'] = ''
        vbo['Content'] = weiboJson['text'].replace('\n', '').replace('\r\n', '').replace('\t', '').replace('\"', '\\\"')
        vbo['WeiboLocation'] = ''
        vbo['TopicName'] = ''
        vbo['IsOriginality'] = True if vbo['WeiboType'] == '原创' else False
        vbo['CreateTime'] = self.parse_time(weiboJson['created_at'])
        vbo['CommentUrl'] = ""
        if 'comments_count' in weiboJson.keys():
            vbo['CommentNum'] = weiboJson['comments_count']
        else:
            vbo['CommentNum'] = ''
            
        if 'reposts_count' in weiboJson.keys():
            vbo['Retweet'] = weiboJson['reposts_count']
        else:
            vbo['Retweet'] = ''
            
        if 'attitudes_count' in weiboJson.keys():
            vbo['PraisedCount'] = weiboJson['attitudes_count']
        else:
            vbo['PraisedCount'] = ''
        vbo['CollectTime'] = collect_time
        vbo['Character'] = '中性'
        vbo['Comments'] = []
        vbo['Quality'] = '正常'
        vbo['Author'] = self.get_user(weiboJson)
        weibo.append(vbo)
        return weibo

    """下载微博图片
    @param image_urls: 图片列表
    """

    def parse_image(self, image_urls):
        image_detail = []
        if image_urls:
            date_dir = time.strftime('%Y%m%d', time.localtime(time.time()))
            sub_dir_path = '%s/%s' % (self.IMAGES_STORE, date_dir)
            dir_path = '%s/%s' % (self.BASE_IMAGES_STORE, date_dir)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            for pic in image_urls:
                download_image = {}
                image_url = pic['thumbnail_pic']
                image_url = image_url.replace("thumbnail", "bmiddle")
                image_id = self.getMd5Str(image_url)
                image_file_name = image_id + '.jpg'
                image_path = self.downloadFileNews(image_url, dir_path)
                if image_path is None or len(image_path) == 0:
                    logger.error(" %s download error" % image_url)
                    continue
                thumbnail_image_url = image_url.replace('bmiddle', 'square')
                thumbnail_image_id = self.getMd5Str(thumbnail_image_url)
                thumbnail_file_name = thumbnail_image_id + '.jpg'
                thumbnail_image_path = self.downloadFileNews(thumbnail_image_url, dir_path)
                download_image["ImageUrl"] = image_url
                download_image["ImageId"] = self.getMd5Str(image_url)
                download_image["FilePath"] = image_path
                download_image["ImageName"] = image_file_name
                download_image["ThumbnailPath"] = '' if thumbnail_image_path is None or len(
                    thumbnail_image_path) == 0 else thumbnail_image_path
                image_detail.append(download_image)
        return image_detail

    # 判断该条微博是原创还是转发
    def get_vbo_type(self, weiboJson):
        if weiboJson.has_key('retweeted_status'):
            return ("转发", weiboJson['retweeted_status']['id'])
        else:
            return ("原创", "")

    def remove_html_tag(self, strs):
        if strs is None:
            return ""
        p = re.compile('<[^>]*?>')
        content = p.sub("", strs)
        content = content.replace('\r', '').replace('\n', '').strip()
        return content

    def get_user(self, weiboJson):
        # 获取一个完整的用户信息
        if 'user' not in weiboJson.keys():
            return None
        user = weiboJson['user']
        userInfo = {}
        userInfo["AuthorLocation"] = user['location']
        userInfo["VerifyInfo"] = "W_icon icon_pf_approve_co"
        userInfo["TweetNum"] = user['statuses_count']
        userInfo["HeadPicPath"] = self.downloadHeadPic(user['profile_image_url'])
        userInfo["NickName"] = user['screen_name']
        # 由于通过API获取的时间格式无法解析，所以随机给一个日期
        userInfo["RegisterTime"] = self.parse_time(user['created_at'])
        userInfo["Discription"] = self.remove_html_tag(user['description'])
        userInfo["Tag"] = user['verified_reason']
        userInfo["Accounts"] = str(user['id'])
        userInfo["IdolNum"] = user['friends_count']
        userInfo["IsEnt"] = False
        userInfo["IsVip"] = False
        userInfo['FansNum'] = user['followers_count']
        return userInfo

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
            logging.info("就是这条数据报错的: %s" % data)
            logging.error("post json error : %s" % msg)
        else:
            responsecode = response.getcode()
            logger.info("response code is: %s" % responsecode)

    def parse_time(self, strs):
        MONTHS = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06", "Jul": "07",
                  "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
                  }
        strs = strs.encode('utf-8')
        strs_arry = strs.split(' ')
        month_str = MONTHS[strs_arry[1]]
        day_str = strs_arry[2]
        hms_str = strs_arry[3]
        year_str = strs_arry[5]
        create_time = year_str + "-" + month_str + '-' + day_str + ' ' + hms_str
        return create_time

        # 下载头像

    def downloadHeadPic(self, image_url):
        if not os.path.exists(self.BASE_HEADPIC_STORE):
            os.makedirs(self.BASE_HEADPIC_STORE)
        image_path = self.downloadFileNews(image_url, self.BASE_HEADPIC_STORE)
        return image_path

    def downloadFileNews(self, url, dir_path):
        try:
            osspath = ossutils.upload('zhiyun-portal', 'cdvcloud', 'spider', url, 1, dir_path)
            logger.debug("oss path is %s" % osspath)
            return osspath
        except Exception, e:
            logger.error("oss上传失败 %s" % e)
            return ''

    def getMd5Str(self, strs):
        m = hashlib.md5()
        m.update(strs)
        md5Str = m.hexdigest()
        return md5Str

    def crond(self):
        while True:
            logger.info("更新开始")
            self.get_all_new_weibo()
            logger.info("更新结束")
            # 暂停500s
            time.sleep(3000)


if __name__ == '__main__':
    weibo_crawl = WeiboCrawl()
    weibo_crawl.crond()
