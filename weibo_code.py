# -*- coding: utf-8 -*-

from weibo import APIClient

import webbrowser, re, json, time
import urllib, urllib2, urllib3, cookielib
import hashlib, base64, rsa, binascii # encrypt

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):

    def http_error_301(self, cls, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(cls, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_302(self, cls, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(cls, req, fp, code, msg, headers)
        result.status = code
        return result
    
def get_cookie():
    cookies = cookielib.CookieJar()
    return urllib2.HTTPCookieProcessor(cookies)
   
def get_opener(proxy=False):
    rv=urllib2.build_opener(get_cookie(), SmartRedirectHandler())
    rv.addheaders = [('User-agent', 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)')]
    return rv

class SinaAPI():
    
    def __init__(self, CALLBACK_URL, APP_KEY, REDIRECT_URL, USER_ID, USER_PSWD):
        self.CALLBACK_URL = CALLBACK_URL
        self.APP_KEY = APP_KEY
        self.REDIRECT_URL = REDIRECT_URL
        self.USER_ID = USER_ID
        self.USER_PSWD = USER_PSWD
        self.http = urllib3.PoolManager()
        
    def get_username(self, USER_ID):
        # The Encryption Algorithm of username 
        # ssologin.js : ah.su=sinaSSOEncoder.base64.encode(m(aj));
        USER_ID_ = urllib.quote(USER_ID) # encode username, avoid error example:@ &  
        su = base64.encodestring(USER_ID_)[:-1]
        return su
   
    def get_password_rsa(self, USER_PSWD, PUBKEY, servertime, nonce):
        # 密码加密运算sina我已知有两种，这是其中一种。
        # rsa Encrypt :  #when pwencode = "rsa2"
        rsaPubkey = int(PUBKEY, 16)#pubkey from 16 to 10
        key_1 = int('10001', 16) #10001 to 65537 
        key = rsa.PublicKey(rsaPubkey, key_1) #
        message = str(servertime) + "\t" + str(nonce) + "\n" + str(USER_PSWD)
        passwd = rsa.encrypt(message, key)
        passwd = binascii.b2a_hex(passwd) #to 16
        return passwd
      
    def get_parameter(self):
        su = self.get_username(self.USER_ID)
        url = "https://login.sina.com.cn/sso/prelogin.php?entry=openapi&callback=sinaSSOController.preloginCallBack\
&su="+su+"&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.15)"
        r = self.http.request('GET', url)
        p = re.compile('\((.*)\)')
        json_data = p.search(r.data).group(1)
        data = json.loads(json_data)
        
        PUBKEY = data['pubkey']
        pcid = data['pcid']
        servertime = str(data['servertime'])
        nonce = data['nonce']
        rsakv = str(data['rsakv'])
        sp = self.get_password_rsa(self.USER_PSWD, PUBKEY, servertime, nonce)
        return pcid, servertime, nonce, rsakv, sp, su
         
    def get_ticket(self):
        pcid, servertime, nonce, rsakv, sp, su = self.get_parameter()
        fields = urllib.urlencode({
            'entry'        : 'openapi',
            'gateway'      : '1',
            'from'         : '',
            'savestate'    : '0',
            'useticket'    : '1',
            'pagerefer'    :'',
            'pcid'         : pcid,
            'ct'           : '1800',
            's'            : '1',
            'vsnf'         : '1',
            'vsnval'       : '',
            'door'         : '',
            'appkey'       : 'kxR5R',
            'su'           : su,
            'service'      : 'miniblog',
            'servertime'   : servertime,
            'nonce'        : nonce,
            'pwencode'     : 'rsa2',
            'rsakv'        : rsakv,
            'sp'           : sp,
            'sr'           : '1680*1050',
            'encoding'     : 'UTF-8',
            'cdult'        : '2',
            'domain'       : 'weibo.com',
            'prelt'        : '0',
            'returntype'   : 'TEXT',
        })
        headers = {
                   #"请求": "POST /sso/login.php?client=ssologin.js(v1.4.15)&_=1400652171542 HTTP/1.1",
                   #"Accept": "*/*", 
                   "Content-Type": "application/x-www-form-urlencoded",
                   }
        url = "https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.15)"
        req = urllib2.Request(url, fields, headers)
        f = urllib2.urlopen(req)
        data = json.loads(f.read())
        return data["ticket"]
    
    def get_code_Security(self): 
        ticket = self.get_ticket()
        fields = urllib.urlencode({
            'action': 'submit', # 必须
            'display': 'default',
            'withOfficalFlag': '0', # 必须
            'quick_auth': 'null',
            'withOfficalAccount': '',
            'scope': '',
            'ticket': ticket, # 必须
            'isLoginSina': '',  
            'response_type': 'code', # 必须
            'regCallback': 'https://api.weibo.com/2/oauth2/authorize?client_id='+self.APP_KEY+'\
&response_type=code&display=default&redirect_uri='+self.REDIRECT_URL+'&from=&with_cookie=',
            'redirect_uri': self.REDIRECT_URL, # 必须
            'client_id': self.APP_KEY, # 必须
            'appkey62': 'kxR5R',
            'state': '', # 必须
            'verifyToken': 'null',
            'from': '', # 必须
            'userId': "", # 此方法不需要填写明文ID
            'passwd': "", # 此方法不需要填写明文密码
            })
        LOGIN_URL = 'https://api.weibo.com/oauth2/authorize' 
        headers = {"User-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; EIE10;ZHCNMSE; rv:11.0) like Gecko",
                   "Referer": self.CALLBACK_URL,
                   "Content-Type": "application/x-www-form-urlencoded",
                   }
        req = urllib2.Request(LOGIN_URL, fields, headers)
        req_ =urllib2.urlopen(req)
        return_redirect_uri = req_.geturl()
        code = re.findall(r"(?<=code%3D).{32}|(?<=code=).{32}", return_redirect_uri) # url中=用%3D表示或者=直接表示 
        return code 
    
    def get_code_NS(self):
        fields = urllib.urlencode({
            'action': 'submit', # 必须
            'display': 'default',
            'withOfficalFlag': '0', # 必须
            'quick_auth': 'null',
            'withOfficalAccount': '',
            'scope': '',
            'ticket': '', # 必须
            'isLoginSina': '',  
            'response_type': 'code', # 必须
            'regCallback': '',
            'redirect_uri': self.REDIRECT_URL, # 必须
            'client_id': self.APP_KEY, # 必须
            'appkey62': 'kxR5R',
            'state': '', # 必须
            'verifyToken': 'null',
            'from': '', # 必须
            'userId': self.USER_ID, # 必须
            'passwd': self.USER_PSWD, # 必须
            })
        LOGIN_URL = 'https://api.weibo.com/oauth2/authorize' 
        headers = {"User-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; EIE10;ZHCNMSE; rv:11.0) like Gecko",
                   "Referer": self.CALLBACK_URL,
                   "Content-Type": "application/x-www-form-urlencoded",
                   }
        r = urllib2.Request(LOGIN_URL, fields, headers)
        opener = get_opener(False) 
        urllib2.install_opener(opener)
        try:  
            f = opener.open(r)  
            return_redirect_uri = f.url   
            print "NS1", return_redirect_uri             
        except urllib2.HTTPError, e:  
            return_redirect_uri = e.geturl()  
            print "NS2", return_redirect_uri  
        # 取到返回的code  
        code = re.findall(r"(?<=code%3D).{32}|(?<=code=).{32}", return_redirect_uri) # url中=用%3D表示或者=直接表示 
        return code 
 
if __name__ == "__main__":
    APP_KEY = u'3726251905' # app key
    APP_SECRET = u'6673ae2beb1d836af4f9142802fa4357' # app secret
    REDIRECT_URL = 'https://api.weibo.com/oauth2/default.html'
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=REDIRECT_URL)
    CALLBACK_URL = client.get_authorize_url()
    username = "chenfujun@toptimetech.com"
    password = "cfj19871104"
    API = SinaAPI(CALLBACK_URL, APP_KEY, REDIRECT_URL, username, password)
    code = API.get_code_Security()
    #code = API.get_code_NS() http://
    """
    #webbrowser.open_new(url) #获取code=后面的内容  
    code = raw_input('输入url中code后面的内容后按回车键：')  
    print code, "code"
    """
    requests = client.request_access_token(code)
    access_token = requests.access_token # 新浪返回的token，类似abc123xyz456  
    expires_in = requests.expires_in  
    file_object = open('D:/weibo_code.txt', 'w')
    file_object.write(str(expires_in))
    file_object.close()
    time.sleep(1200)