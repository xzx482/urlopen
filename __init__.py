from enum import Enum
from http.client import RemoteDisconnected
import time
from typing import Union
from urllib import request,parse,error,response
from http import cookiejar
from copy import deepcopy
from gzip import decompress,GzipFile
import json


class 长度不一致(error.ContentTooShortError):
	pass

class 不处理异常响应码Handler(request.HTTPDefaultErrorHandler):
	def http_error_default(self, req, fp, code, msg, hdrs):
		return fp

class 不处理重定向Handler(request.HTTPRedirectHandler):
	def http_error_302(self, req, fp, code, msg, headers):
		return fp
	
	http_error_301 = http_error_303 = http_error_307 = http_error_302

opener=request.build_opener()
不处理HTTP响应的opener=request.build_opener(不处理异常响应码Handler,不处理重定向Handler)
不处理异常响应码的opener=request.build_opener(不处理异常响应码Handler)
不处理重定向的opener=request.build_opener(不处理重定向Handler)


def 头部信息解析(值)->dict:
	值_={}
	for i in 值.split(';'):
		k,v=i.split('=',1)
		值_[k.strip()]=v.strip()
	


class 响应内容类型(Enum):
	#自动=0
	json=2
	文本=3
	二进制=4
	二进制流=5

class 响应:
	def __init__(s,原始响应:response.addinfourl):
		s.原始响应=原始响应
		s.实际url=原始响应.url
		s.响应头=原始响应.headers
		s.响应码=原始响应.code
		s.响应内容=None

	
	def 获取内容(s,解码:响应内容类型):
		'''
		if 解码==响应内容类型.自动:
			响应类型=s.响应头['Content-Type']
			if 响应类型 and 'application' in 响应类型:#响应类型可能为 None
				if 'json' in 响应类型:
					解码=响应内容类型.json
				elif 'octet-stream' in 响应类型:
					解码=响应内容类型.二进制
				else:
					解码=响应内容类型.文本
			else:
				解码=响应内容类型.文本
		'''
		二进制流=s.原始响应

		#判断gzip压缩
		if s.响应头['content-encoding']=='gzip':
			二进制流_=GzipFile(fileobj=二进制流)
		else:
			二进制流_=二进制流

		if 解码==响应内容类型.二进制流:
			return 二进制流_
		else:
			二进制数据_=二进制流_.read()
			if 解码==响应内容类型.二进制:
				s.响应内容=二进制数据_
			else:

				编码=json.detect_encoding(二进制数据_)
				文本=二进制数据_.decode(编码)
				if 解码==响应内容类型.文本:
					s.响应内容=文本
				elif 解码==响应内容类型.json:
					s.响应内容=json.loads(文本)
				else:
					raise Exception('未知的响应内容类型')
			return s.响应内容

	def 保存到文件(s,文件名=None):
		if 文件名 is None:
			内容处置=s.响应头['Content-Disposition']
			if 内容处置:
				内容处置_=头部信息解析(内容处置)
				if 'filename' in 内容处置_:
					文件名=内容处置_['filename']
					
		if 文件名 is None:
			文件名=parse.unquote( s.实际url.split('/')[-1] )


		响应流=s.获取内容(响应内容类型.二进制流)
		块大小=1024*1024
		已读=0
		文件大小=-1
		内容长度=s.响应头['Content-Length']
		if 内容长度:
			文件大小=int(内容长度)

		with open(文件名,'wb') as f:
			while True:
				二进制流=响应流.read(块大小)
				if not 二进制流:
					break
				已读+=len(二进制流)
				f.write(二进制流)

		if 文件大小>0 and 文件大小!=已读:
			raise 长度不一致('文件大小不匹配')

		return 文件名

	def __repr__(s):
		return '<响应: {} {}>'.format(s.响应码,s.实际url)


class 请求内容类型(Enum):
	'''
	Content-Type
	'''
	url编码='application/x-www-form-urlencoded'
	json='application/json'



class 请求方法(Enum):
		自动=None
		GET='GET'
		POST='POST'
		PUT='PUT'
		DELETE='DELETE'
		HEAD='HEAD'
		OPTIONS='OPTIONS'
		PATCH='PATCH'
		TRACE='TRACE'
		CONNECT='CONNECT'


class 重试_倍数延迟_修饰器:
	'''
	@重试_倍数延迟_修饰器(12,3) #括号内可以为空, 但括号不能省略   \n
	def func(a,b,c):
		...
	'''
	def __init__(s,最大延迟=10,延迟基数=2):
		s.函数=None
		s.最大延迟=最大延迟
		s.延迟基数=延迟基数*2
		s.计数=-1
	def __call__(s,*args,**kwargs):
		if s.计数==-1:
			s.函数=args[0]
			s.计数=0
			return s
		s.计数+=1
		延迟=s.延迟基数*s.计数
		if 延迟>s.最大延迟:
			延迟=s.最大延迟
		返回值=s.函数(*args,**kwargs)
		time.sleep(延迟)
		return 返回值


@重试_倍数延迟_修饰器(8,3) #括号内可以为空, 但括号不能省略
def 打开url_自动重试_失败回调(错误,计数):
	print('打开url失败,第'+str(计数)+'次:'+str(错误))

class 请求:
	def __init__(s, url,
		数据:Union[dict,str,bytes,None]=None, 内容类型:Union[请求内容类型,None]=None,
		请求头:Union[dict[str,str],list,None]=None,方法:Union[请求方法,str]=请求方法.自动
	):
		s.url=url
		s.请求头={
			'accept-encoding': 'gzip',
			'accept-language': 'zh-CN,zh;q=0.9',
			#'user-agent':'Mozilla/0 (Winow T 0; Wi4; x4) BananaWebKit/37.6 (KHTML, like A Gecko) GuessWhoIAm/8.0.387.122 Saar/53.6'
		}
		if 数据 is None:
			if 方法==请求方法.自动:
				方法=请求方法.GET
			s.数据=None
		else:
			if 方法==请求方法.自动:
				方法=请求方法.POST
			if isinstance(数据,bytes):
				s.数据=数据
			else:
				if isinstance(数据,dict):
					if 内容类型==请求内容类型.url编码 or 内容类型==None:
						数据_=parse.urlencode(数据)
						s.请求头['Content-Type']=请求内容类型.url编码.value
					elif 内容类型==请求内容类型.json:
						数据_=json.dumps(数据,ensure_ascii=False,Separators= (',',':'))
						s.请求头['Content-Type']=请求内容类型.json.value
					else:
						raise Exception('不支持的内容类型')
				elif isinstance(数据,str):
					数据_=数据
				
				s.数据=bytes(数据_,encoding='utf-8')

		if isinstance(请求头,dict):
			s.请求头.update(请求头)
		elif isinstance(请求头,list):
			for i in 请求头:
				s.请求头[i[0]]=i[1]
		else:
			if 请求头 is not None:
				raise Exception('请求头必须是字典或列表')

		if isinstance(方法,请求方法):
			s.方法=方法.value
		elif isinstance(方法,str):
			s.方法=方法
		else:
			raise Exception('方法必须是字符串或枚举')
		s.r=request.Request(url,data=s.数据,headers=s.请求头,method=s.方法)

	def 获取打开器(s,不处理异常响应码=False,不处理重定向=False):
		if 不处理异常响应码:
			if 不处理重定向:
				return 不处理HTTP响应的opener
			else:
				return 不处理异常响应码的opener
		else:
			if 不处理重定向:
				return 不处理重定向的opener
			else:
				return opener

	def 使用打开器打开(s,打开器:request.OpenerDirector):
		return 响应(打开器.open(s.r))


	def 打开(s,不处理异常响应码=False,不处理重定向=False):
		return s.使用打开器打开(s.获取打开器(不处理异常响应码,不处理重定向))


	def 打开_自动重试(
		s,
		不处理异常响应码=False,不处理重定向=False,
		最大重试次数=-1,重试间隔_秒=1,回调=打开url_自动重试_失败回调
	):
		打开器=s.获取打开器(不处理异常响应码,不处理重定向)

		计数=0
		while True:
			try:
				return s.使用打开器打开(打开器)
			except (error.URLError,RemoteDisconnected) as e:#其他错误重试没有意义
				if isinstance(e,error.HTTPError):
					raise e
				计数+=1
				if 最大重试次数>-1 and 计数>最大重试次数:
					raise e
				回调(e,计数)
				time.sleep(重试间隔_秒)

	def __repr__(s):
		return '<访问: {} {}>'.format(s.方法,s.url)
		

class 请求_会话(请求):
	'''
	可以自动记录和使用cookie的访问类
	'''
	def __init__(
		s,会话_,url,
		数据:Union[dict,str,bytes,None]=None, 内容类型:Union[请求内容类型,None]=None,
		请求头:Union[dict[str,str],list,None]=None,方法:Union[请求方法,str]=请求方法.自动
	):
		s.会话:会话=会话_
		super().__init__(url,数据,内容类型,请求头,方法)


	def 获取打开器(s,不处理异常响应码,不处理重定向):
		if 不处理异常响应码:
			if 不处理重定向:
				return s.会话.不处理HTTP响应的opener
			else:
				return s.会话.不处理异常响应码的opener
		else:
			if 不处理重定向:
				return s.会话.不处理重定向的opener
			else:
				return s.会话.opener



		


class 会话:
	def __init__(s):
		s.cookie=cookiejar.CookieJar()
		s.cookie_handler=request.HTTPCookieProcessor(s.cookie)
		s.opener=request.build_opener(s.cookie_handler)
		s.不处理HTTP响应的opener=request.build_opener(s.cookie_handler,不处理异常响应码Handler,不处理重定向Handler)
		s.不处理异常响应码的opener=request.build_opener(s.cookie_handler,不处理异常响应码Handler)
		s.不处理重定向的opener=request.build_opener(s.cookie_handler,不处理重定向Handler)
	
	def 请求(
		s,url,
		数据:Union[dict,str,bytes,None]=None, 内容类型:Union[请求内容类型,None]=None,
		请求头:Union[dict[str,str],list,None]=None,方法=请求方法.自动
	):
		return 请求_会话(s,url,数据,内容类型,请求头,方法)


	def 导出cookie(s)->dict:
		s.cookie._cookies_lock.acquire()
		try:
			cookies_dict=deepcopy(s.cookie._cookies)
		finally:
			s.cookie._cookies_lock.release()
		return cookies_dict

	def 导入cookie(s,cookie_dict:dict):
		s.cookie._cookies_lock.acquire()
		try:
			s.cookie._cookies.update(deepcopy(cookie_dict))
		finally:
			s.cookie._cookies_lock.release()

	def 清除cookie(s):
		s.cookie._cookies_lock.acquire()
		try:
			s.cookie._cookies.clear()
		finally:
			s.cookie._cookies_lock.release()


if __name__=='__main__':
	q=请求('https://cn.bing.com/')
	x=q.打开()
	s=x.获取内容(响应内容类型.文本)
	print(s)