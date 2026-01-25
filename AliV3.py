import json
import os
import subprocess
import time
import sys
import textwrap
from functools import partial

subprocess.Popen = partial(subprocess.Popen, encoding='utf-8', errors='ignore')

import requests

from Utils import pwdEncrypt

proxy = None

class AliV3:
    def __init__(self):
        self.captchaTicket = None
        self.CertifyId = None
        self.author = '古月&zhangMonday'
        
        # 初始化账号密码变量，用于在 Sumbit_All 中重试时调用
        self.username = None
        self.password = None

        # 缓存文件名称
        self.cookie_cache_file = 'cookie_cache.json'
        
        # API获取的验证参数
        self.verifyParam = None
        self.deviceToken = None

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

    def getCap(self):
        API_KEY = 'ak_I9yMvTeRELuUUjiJLyoW9QsXCUzANy7q-h-q91bPWSo'  # jlc 31天

        def get_headers():
            headers = {'Content-Type': 'application/json'}
            if API_KEY:
                headers['X-API-Key'] = API_KEY
            return headers

        url = 'http://144.66.33.227:8000/api/captcha/solve'

        request_data = {
            'type': 'slide',
            'timeout': 60,
            'scene_id': '6mw4mrmg',
            'prefix': '1tbpug',
            'intercept_mode': True  # 启用拦截模式
        }

        try:
            response = requests.post(
                url,
                json=request_data,
                headers=get_headers(),
                timeout=120
            )

            print(response.json())
            
            resp_json = response.json()
            if 'verifyParam' in resp_json:
                verify_param_str = resp_json['verifyParam']
                json_data = json.loads(verify_param_str)
                
                self.verifyParam = json_data['data']
                self.deviceToken = json_data['deviceToken']
                self.CertifyId = json_data['certifyId']
                return True
            else:
                print("Error: verifyParam not found in API response")
                return False

        except Exception as e:
            print(f"getCap Error: {e}")
            return False

    def Sumbit_All(self):
        if not self.verifyParam:
            print("Missing verifyParam, skipping Sumbit_All")
            return

        _data = self.verifyParam
        deviceToekn = self.deviceToken

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
        
        print('Request Body:', json.dumps(json_data, indent=4, ensure_ascii=False))
        print(response.text)
        
        try:
            self.captchaTicket = response.json()['data']['captchaTicket']
        except Exception as e:
            print("Failed to get captchaTicket:", e)

    def get_cached_cookies_headers(self):
        """
        获取Cookies和Headers。
        检查本地缓存，如果存在且未过期（20分钟），则直接使用。
        否则运行 getcookie.py 获取并更新缓存。
        """
        need_refresh = True
        cached_data = {}

        # 尝试读取缓存
        if os.path.exists(self.cookie_cache_file):
            try:
                with open(self.cookie_cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                last_time = cached_data.get('timestamp', 0)
                current_time = time.time()
                
                # 检查时间差是否小于 20 分钟 (1200秒)
                if current_time - last_time < 20 * 60:
                    print("缓存有效 (小于20分钟)，使用缓存的 Cookies 和 Headers。")
                    return cached_data.get('cookies'), cached_data.get('headers')
                else:
                    print(f"缓存已过期 (上次更新: {time.ctime(last_time)})，重新获取...")
            except Exception as e:
                print(f"读取缓存文件出错: {e}，将重新获取。")
        else:
            print("缓存文件不存在，开始获取...")

        # 调用 getcookie.py 获取
        cookies = None
        headers = None
        
        try:
            print("正在调用 getcookie.py 获取动态 Cookies 和 Headers...")
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
                        print("getcookies执行成功，获取到数据。")
                    except Exception as parse_error:
                        print(f"解析 getcookie.py 输出时出错: {parse_error}")
                        # 容错尝试
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
            print(f"动态获取 Cookies/Headers 发生异常: {e}")

        # 保存缓存
        save_data = {
            'timestamp': time.time(),
            'cookies': cookies,
            'headers': headers
        }
        
        try:
            with open(self.cookie_cache_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4)
            print(f"已更新缓存文件: {self.cookie_cache_file}")
        except Exception as e:
            print(f"保存缓存文件失败: {e}")

        return cookies, headers

    def Login(self, username, password):
        if not self.captchaTicket:
            print("跳过登录: No captchaTicket acquired.")
            return

        # 获取 cookies 和 headers
        cookies, headers = self.get_cached_cookies_headers()

        if cookies is None or headers is None:
            print("错误：未能获取到 Cookies 或 Headers (值为 None)，退出程序。")
            sys.exit(1)

        json_data = {
            'username': username,
            'password': password,
            'isAutoLogin': False,
            'captchaTicket': self.captchaTicket,
        }

        try:
            response = requests.post('https://passport.jlc.com/api/cas/login/with-password', cookies=cookies,
                                     headers=headers, json=json_data)
            print("Login Response:", response.text)
        except Exception as e:
            print(f"Login Request Failed: {e}")

    def test(self):
        pass

    def main(self, username, password):
        # 保存参数到实例变量
        self.username = username
        self.password = password

        # 使用 API 获取验证码
        if self.getCap():
            # 提交验证并获取 ticket
            res = self.Sumbit_All()
            
            # 传递加密后的账号密码进行登录
            enc_username = pwdEncrypt(username)
            enc_password = pwdEncrypt(password)
            self.Login(enc_username, enc_password)
            return res
        else:
            print("验证码获取失败，无法继续。")


if __name__ == '__main__':
    ali = AliV3()
    
    # 检查命令行参数
    if len(sys.argv) >= 3:
        user_arg = sys.argv[1]
        pass_arg = sys.argv[2]
        ali.main(user_arg, pass_arg)
    else:
        print("用法: python AliV3.py <username> <password>")
        print("示例: python AliV3.py 13800138000 MyPassword123")

