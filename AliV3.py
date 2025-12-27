import json
import os
import random
import subprocess
import time
import sys
import textwrap
from functools import partial

subprocess.Popen = partial(subprocess.Popen, encoding='utf-8', errors='ignore')

import requests
import execjs

from Utils import MatchArgs, pwdEncrypt

proxy = None

class AliV3:
    def __init__(self):
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
        
        # 初始化账号密码变量，用于在 Sumbit_All 中重试时调用
        self.username = None
        self.password = None
        self.cache_file = "cookie_cache.json" # 缓存文件名

        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://account.dji.com',
            'Pragma': 'no-cache',
            'Referer': 'https://account.dji.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

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
            'Timestamp': '2025-12-15T13:30:27Z',
            'Version': '2023-03-05',
            'Action': 'InitCaptchaV3',
            'SceneId': '6mw4mrmg',
            'Language': 'cn',
            'Mode': 'embed',
        }

        DeviceData = self.getDeviceData()
        data['DeviceData'] = DeviceData
        data = self.get_sign(data, self.sign_key1)

        response = requests.post('https://1tbpug.captcha-open.aliyuncs.com/', headers=self.headers, data=data,
                                 proxies=proxy)

        print(response.text)
        self.DeviceConfig = response.json()['DeviceConfig']
        print('DeviceConfig', self.DeviceConfig)
        self.CertifyId = response.json()['CertifyId']
        print('CertifyId', self.CertifyId)
        self.StaticPath = response.json()['StaticPath'] + '.js'
        print('StaticPath', self.StaticPath)

    def decrypt_DeviceConfig(self):
        with open('AliyunCaptcha.js', 'r', encoding='utf-8') as f:
            js = f.read()
        ctx = execjs.compile(js)
        self.Real_Config = ctx.call('getDeviceConfig', self.DeviceConfig)
        print('Real_Config', self.Real_Config)
        self.fenlin_path = self.Real_Config['version'] + '.js'

    def GetDynamic_Key(self):
        self.fenlin = 'https://g.alicdn.com/captcha-frontend/FeiLin/' + self.fenlin_path
        print(self.fenlin)

        fenlin_js = requests.get(self.fenlin).text
        with open('fenlin.js', 'r', encoding='utf-8') as f:
            js = f.read()

        jscode = js.replace('#jscode#', fenlin_js)
        jscode = jscode.replace('#config#', self.DeviceConfig)
        
        filename = f'fenlin_temp_{self.CertifyId}.js'
        filepath = os.path.join('./temp', filename)

        # 确保temp目录存在
        if not os.path.exists('./temp'):
            os.makedirs('./temp')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(jscode)

        result = subprocess.run(
            ["node", filepath],
            capture_output=True,
            text=True
        ).stdout
        self.Dynamic_Key = result.replace('\n', '')
        print(self.Dynamic_Key)

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

        print(f'随机选择的环境文件: {random_json_file}')
        data = ctx.call('getLog2Data', data, self.Dynamic_Key, self.Real_Config, env_data)
        print(data)
        response = requests.post('https://cloudauth-device-dualstack.cn-shanghai.aliyuncs.com/', headers=self.headers,
                                 data=data, proxies=proxy)
        print(response.text)

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
        print(data)

        response = requests.post('https://cloudauth-device-dualstack.cn-shanghai.aliyuncs.com/', headers=self.headers,
                                 data=data, proxies=proxy)
        print(response.text)

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
        print(data)
        return data

    def Sumbit_All(self):
        args = MatchArgs(self.StaticPath)
        if args is None:
            print('StaticPath not found')
            # 重试逻辑：使用保存的 self.username 和 self.password
            if self.username and self.password:
                print("Retry executing main...")
                self.main(self.username, self.password)
            else:
                print("Error: Args missing for retry.")
            return

        print('dyn_key', args)
        _data = self.getData(args)
        deviceToekn = self.GetDeviceData()

        print('deviceToekn', deviceToekn)
        print('_data', _data)

        import requests

        cookies = {
            'device_id': 'c7d0a5f4b554477fae0e1ba29f84fb63',
            'HWWAFSESID': 'bcd7d8b4f625fb57ac',
            'HWWAFSESTIME': '1766299533105',
            'Qs_lvt_290854': '1766237893%2C1766299553',
            'Qs_pv_290854': '2499244294467079700%2C852781256760664000',
            '__sameSiteCheck__': '1',
            '_c_WBKFRo': '03ctatXDH7wXL1GIRpFWI9AUfuGhSVMzyOf5q8oX',
            '_nb_ioWEgULi': '',
        }

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'cache-control': 'no-cache, no-store, must-revalidate',
            'content-type': 'application/json',
            'origin': 'https://passport.jlc.com',
            'referer': 'https://passport.jlc.com/window/login?appId=JLC_PORTAL_PC&redirectUrl=https%3A%2F%2Fwww.jlc.com%2F',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
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

        response = requests.post(
            'https://passport.jlc.com/api/cas/captcha/v2/check-ali-captcha',
            cookies=cookies,
            headers=headers,
            json=json_data
        )

        print(response.status_code)
        
        # 输出请求主体
        print('Request Body:', json.dumps(json_data, indent=4, ensure_ascii=False))
        
        print(response.text)
        
        try:
            self.captchaTicket = response.json()['data']['captchaTicket']
        except Exception as e:
            print("Failed to get captchaTicket:", e)

    def fetch_new_cookies(self):
        """执行脚本获取新的 cookies 和 headers，并保存到缓存文件"""
        print("正在调用 getcookie.py 获取动态 Cookies 和 Headers...")
        cookies = None
        headers = None
        
        try:
            process = subprocess.Popen(
                [sys.executable, 'getcookie.py'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                output_str = stdout
                start_marker = "cookies = {"
                start_index = output_str.find(start_marker)
                
                if start_index != -1:
                    code_block = output_str[start_index:]
                    dedented_code = textwrap.dedent(code_block)
                    
                    local_scope = {}
                    try:
                        exec(dedented_code, {}, local_scope)
                        cookies = local_scope.get('cookies')
                        headers = local_scope.get('headers')
                        print("成功获取动态 Cookies 和 Headers。")
                        
                        # 保存到缓存文件
                        if cookies and headers:
                            cache_data = {
                                "timestamp": time.time(),
                                "cookies": cookies,
                                "headers": headers
                            }
                            # ===================== 修改开始：获取并打印绝对路径 =====================
                            abs_cache_path = os.path.abspath(self.cache_file)
                            with open(self.cache_file, "w", encoding="utf-8") as f:
                                json.dump(cache_data, f, ensure_ascii=False, indent=4)
                            print(f"数据已保存到缓存文件地址: {abs_cache_path}")
                            # ===================== 修改结束 =======================================
                            
                    except Exception as parse_error:
                        print(f"解析 getcookie.py 输出时出错: {parse_error}")
                        # 备用尝试
                        try:
                            exec(code_block, {}, local_scope)
                            cookies = local_scope.get('cookies')
                            headers = local_scope.get('headers')
                        except:
                            pass
                else:
                    print("错误：在 getcookie.py 输出中未找到 'cookies = {' 标记。")
            else:
                print(f"getcookie.py 执行失败: {stderr}")
        except Exception as e:
            print(f"执行 getcookie.py 发生异常: {e}")
            
        return cookies, headers

    def get_cookies_and_headers(self):
        """获取 cookies 和 headers，带缓存逻辑"""
        now = time.time()
        need_refresh = True
        
        cookies = None
        headers = None
        
        abs_cache_path = os.path.abspath(self.cache_file)
        if os.path.exists(self.cache_file):
            print(f"发现缓存文件，正在从以下地址读取: {abs_cache_path}")
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_time = data.get("timestamp", 0)
                    
                    # 检查是否在15分钟内 (15 * 60 = 900秒)
                    if now - saved_time < 900:
                        print("缓存有效，使用缓存的 Cookies 和 Headers。")
                        cookies = data.get("cookies")
                        headers = data.get("headers")
                        if cookies and headers:
                            need_refresh = False
                    else:
                        print("缓存已过期（超过15分钟）。")
            except Exception as e:
                print(f"读取缓存文件出错: {e}")
        else:
            print(f"缓存文件不存在 (路径: {abs_cache_path})，准备新建。")

        if need_refresh:
            cookies, headers = self.fetch_new_cookies()
            
        return cookies, headers

    def Login(self, username, password):
        if not self.captchaTicket:
            print("Skipping login: No captchaTicket acquired.")
            return

        # 使用带缓存的获取方法
        cookies, headers = self.get_cookies_and_headers()

        if cookies is None or headers is None:
            print("错误：未能获取到 Cookies 或 Headers (值为 None)，退出程序。")
            sys.exit(1)

        json_data = {
            'username': username,
            'password': password,
            'isAutoLogin': False,
            'captchaTicket': self.captchaTicket,
        }
        
        import requests
        response = requests.post('https://passport.jlc.com/api/cas/login/with-password', cookies=cookies,
                                 headers=headers, json=json_data)

        print(response.text)

    def test(self):
        pass

    def main(self, username, password):
        # 保存参数到实例变量
        self.username = username
        self.password = password

        # 使用 self 调用实例方法
        self.Req_Init()
        self.decrypt_DeviceConfig()
        self.GetDynamic_Key()
        self.GetLog2()
        self.GetLog3()
        
        res = self.Sumbit_All()
        
        # 传递加密后的账号密码进行登录
        enc_username = pwdEncrypt(username)
        enc_password = pwdEncrypt(password)
        self.Login(enc_username, enc_password)
        return res


if __name__ == '__main__':
    ali = AliV3()
    
    # 检查命令行参数，如果有则使用，如果没有则提示
    if len(sys.argv) >= 3:
        user_arg = sys.argv[1]
        pass_arg = sys.argv[2]
        ali.main(user_arg, pass_arg)
    else:
        print("用法: python AliV3.py <username> <password>")
        print("示例: python AliV3.py 13800138000 MyPassword123")
