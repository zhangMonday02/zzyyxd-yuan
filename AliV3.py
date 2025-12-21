import json
import os
import random
import subprocess
import time
import sys
from functools import partial

subprocess.Popen = partial(subprocess.Popen, encoding='utf-8', errors='ignore')

import requests
import execjs

from Utils import MatchArgs, pwdEncrypt

# 代理配置 (保持原样)
proxy = None

class AliV3:
    def __init__(self):
        # 1. 初始化 Session，用于自动管理 Cookies
        self.session = requests.Session()
        
        self.captchaTicket = None
        self.StaticPath = None
        self.CertifyId = None
        self.Dynamic_Key = None
        self.fenlin = None
        self.fenlin_path = None
        self.Real_Config = None
        self.DeviceConfig = None
        self.sign_key1 = "YSKfst7GaVkXwZYvVihJsKF9r89koz"
        self.sign_key2 = "fpOKzILEajkqgSpr9VvU98FwAgIRcX"
        self.author = '古月'
        
        self.username = None
        self.password = None

        # 通用 Headers
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        # 更新 Session 的 headers
        self.session.headers.update(self.headers)

    # --- 新增：初始化会话，获取新鲜的 Cookies ---
    def Init_Session(self):
        print("正在初始化会话，获取最新 Cookies...")
        url = "https://passport.jlc.com/window/login?appId=JLC_PORTAL_PC&redirectUrl=https%3A%2F%2Fwww.jlc.com%2F"
        try:
            # 访问登录页，服务器会返回 Set-Cookie (包含最新的 HWWAFSESTIME 等)
            self.session.get(url, verify=False) # 忽略证书错误防止报错
            print("Cookies 获取成功:", self.session.cookies.get_dict())
        except Exception as e:
            print(f"初始化 Cookies 失败: {e}")

    def get_sign(self, params, key):
        with open('sign.js', 'r', encoding='utf-8') as f:
            js = f.read()
        ctx = execjs.compile(js)
        return ctx.call('Sign', params, key)

    def getDeviceData(self, ):
        with open('sign.js', 'r', encoding='utf-8') as f:
            js = f.read()
        ctx = execjs.compile(js)
        return ctx.call('getDeviceData')

    def Req_Init(self):
        data = {
            'AccessKeyId': 'LTAI5tSEBwYMwVKAQGpxmvTd',
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureVersion': '1.0',
            'Format': 'JSON',
            'Timestamp': '2025-12-15T13:30:27Z', # 注意：这里的时间戳可能也会过期，建议动态生成
            'Version': '2023-03-05',
            'Action': 'InitCaptchaV3',
            'SceneId': '6mw4mrmg',
            'Language': 'cn',
            'Mode': 'embed',
        }

        DeviceData = self.getDeviceData()
        data['DeviceData'] = DeviceData
        data = self.get_sign(data, self.sign_key1)

        # 阿里云的请求不通过 JLC 的 session，单独发
        response = requests.post('https://1tbpug.captcha-open.aliyuncs.com/', headers=self.headers, data=data, proxies=proxy)

        # print(response.text)
        self.DeviceConfig = response.json()['DeviceConfig']
        self.CertifyId = response.json()['CertifyId']
        self.StaticPath = response.json()['StaticPath'] + '.js'
        print('CertifyId', self.CertifyId)

    def decrypt_DeviceConfig(self):
        with open('AliyunCaptcha.js', 'r', encoding='utf-8') as f:
            js = f.read()
        ctx = execjs.compile(js)
        self.Real_Config = ctx.call('getDeviceConfig', self.DeviceConfig)
        self.fenlin_path = self.Real_Config['version'] + '.js'

    def GetDynamic_Key(self):
        self.fenlin = 'https://g.alicdn.com/captcha-frontend/FeiLin/' + self.fenlin_path
        
        fenlin_js = requests.get(self.fenlin).text
        with open('fenlin.js', 'r', encoding='utf-8') as f:
            js = f.read()

        jscode = js.replace('#jscode#', fenlin_js)
        jscode = jscode.replace('#config#', self.DeviceConfig)
        
        filename = f'fenlin_temp_{self.CertifyId}.js'
        filepath = os.path.join('./temp', filename)

        if not os.path.exists('./temp'):
            os.makedirs('./temp')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(jscode)

        result = subprocess.run(["node", filepath], capture_output=True, text=True).stdout
        self.Dynamic_Key = result.replace('\n', '')
        # print("Dynamic_Key acquired")

    def GetLog2(self):
        data = {
            'AccessKeyId': 'LTAI5tGjnK9uu9GbT9GQw72p',
            'Version': '2020-10-15',
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureVersion': '1.0',
            'Format': 'JSON',
            'Action': 'Log2',
        }
        with open('Log2_Data.js', 'r', encoding='utf-8') as f:
            js = f.read()
        ctx = execjs.compile(js)

        env_folder = 'env'
        json_files = [f for f in os.listdir(env_folder) if f.endswith('.json')]
        random_json_file = random.choice(json_files)
        json_file_path = os.path.join(env_folder, random_json_file)

        with open(json_file_path, 'r', encoding='utf-8') as f:
            env_data = json.load(f)

        data = ctx.call('getLog2Data', data, self.Dynamic_Key, self.Real_Config, env_data)
        # 阿里云请求独立发送
        requests.post('https://cloudauth-device-dualstack.cn-shanghai.aliyuncs.com/', headers=self.headers, data=data, proxies=proxy)

    def GetLog3(self):
        data = {
            'AccessKeyId': 'LTAI5tGjnK9uu9GbT9GQw72p',
            'Version': '2020-10-15',
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureVersion': '1.0',
            'Format': 'JSON',
            'Action': 'Log3',
        }
        with open('Log3_Data.js', 'r', encoding='utf-8') as f:
            js = f.read()
        ctx = execjs.compile(js)
        data = ctx.call('getLog3Data', data, self.Real_Config)

        requests.post('https://cloudauth-device-dualstack.cn-shanghai.aliyuncs.com/', headers=self.headers, data=data, proxies=proxy)

    def GetDeviceData(self):
        with open('deviceToken.js', 'r', encoding='utf-8') as f:
            js = f.read()
        ctx = execjs.compile(js)
        DeviceToken = ctx.call('getDeviceToken', self.Real_Config, self.Dynamic_Key)
        return DeviceToken

    def getData(self, args):
        with open('data.js', 'r', encoding='utf-8') as f:
            js = f.read()
        ctx = execjs.compile(js)
        data = ctx.call('getData', args, self.CertifyId)
        return data

    def Sumbit_All(self):
        args = MatchArgs(self.StaticPath)
        if args is None:
            print('StaticPath not found, retrying...')
            if self.username and self.password:
                self.main(self.username, self.password)
            return

        _data = self.getData(args)
        deviceToekn = self.GetDeviceData()

        # 修改 headers，去除写死的 cookie
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': 'https://passport.jlc.com',
            'referer': 'https://passport.jlc.com/window/login?appId=JLC_PORTAL_PC&redirectUrl=https%3A%2F%2Fwww.jlc.com%2F',
            # secretkey 可能需要动态获取，这里先保留，如果报错需要更新
            'secretkey': '35616236663038352d643366382d343131662d396239622d366439643132653639373764',
            'x-jlc-clientuuid': '445de653-7a24-4242-88dd-0878479726aa-1766237894098',
        }

        captcha_verify_param = {
            "sceneId": "6mw4mrmg",
            "certifyId": self.CertifyId,
            "deviceToken": deviceToekn,
            "data": _data
        }

        captcha_verify_param_str = json.dumps(captcha_verify_param, separators=(',', ':'))

        json_data = {
            'captchaVerifyParam': captcha_verify_param_str,
            'sceneType': 'pass_word_login',
            'aliyunSceneId': '6mw4mrmg',
        }

        # 使用 session 发送请求，会自动带上 Init_Session 获取到的 Cookies
        response = self.session.post(
            'https://passport.jlc.com/api/cas/captcha/v2/check-ali-captcha',
            headers=headers,
            json=json_data
        )

        print("验证码检查状态:", response.status_code)
        # print(response.text)
        
        try:
            self.captchaTicket = response.json()['data']['captchaTicket']
            print(f"获取到 Ticket: {self.captchaTicket}")
        except Exception as e:
            print("获取 Ticket 失败:", response.text)

    def Login(self, username, password):
        if not self.captchaTicket:
            print("无法登录: 未获取到 captchaTicket")
            return

        # Headers 清理，去除写死的 cookie 和可能过期的 jsec-x-df
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': 'https://passport.jlc.com',
            'referer': 'https://passport.jlc.com/window/login?appId=JLC_PORTAL_PC&redirectUrl=https%3A%2F%2Fwww.jlc.com%2F',
            # 'jsec-x-df': '...', # 这个指纹如果过期也会导致风控，建议先注释掉，如果报错再想办法生成
            'secretkey': '35616236663038352d643366382d343131662d396239622d366439643132653639373764',
            'x-jlc-clientuuid': '445de653-7a24-4242-88dd-0878479726aa-1766237894098',
        }
        
        # 将 headers 更新到 session headers 中（或者直接传参）
        # 这里使用 session 发送，确保和 Sumbit_All 使用的是同一个会话环境
        json_data = {
            'username': username,
            'password': password,
            'isAutoLogin': True,
            'captchaTicket': self.captchaTicket,
        }

        print("正在尝试登录接口...")
        response = self.session.post(
            'https://passport.jlc.com/api/cas/login/with-password', 
            headers=headers, 
            json=json_data
        )

        print("登录结果:", response.text)

    def main(self, username, password):
        self.username = username
        self.password = password

        # 1. 这一步最关键：初始化会话
        self.Init_Session()

        # 2. 正常流程
        self.Req_Init()
        self.decrypt_DeviceConfig()
        self.GetDynamic_Key()
        self.GetLog2()
        self.GetLog3()
        
        self.Sumbit_All()
        
        # 3. 登录
        enc_username = pwdEncrypt(username)
        enc_password = pwdEncrypt(password)
        self.Login(enc_username, enc_password)


if __name__ == '__main__':
    ali = AliV3()
    # 填入测试账号密码
    if len(sys.argv) >= 3:
        user_arg = sys.argv[1]
        pass_arg = sys.argv[2]
        ali.main(user_arg, pass_arg)
    else:
        # 你可以在这里填默认测试账号
        print("请提供账号密码")
        # ali.main("138xxxx", "password") 
