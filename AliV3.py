import json
import os
import subprocess
import time
import sys
import textwrap
import random
import math
from functools import partial
from urllib.parse import parse_qs, unquote
from DrissionPage import ChromiumPage, ChromiumOptions

subprocess.Popen = partial(subprocess.Popen, encoding='utf-8', errors='ignore')

import requests

from Utils import pwdEncrypt

proxy = None

class AliV3:
    def __init__(self):
        self.captchaTicket = None
        self.CertifyId = None
        self.author = 'zhangMonday'
        
        # 初始化账号密码变量，用于在 Sumbit_All 中重试时调用
        self.username = None
        self.password = None

        # 缓存文件名称
        self.cookie_cache_file = 'cookie_cache.json'
        
        # 获取的验证参数
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
        
        # 拦截到的数据容器
        self.intercepted_data = None

    def _setup_browser(self):
        """配置并启动 DrissionPage"""
        co = ChromiumOptions()
        co.set_argument('--headless=new')  # 无头模式
        co.set_argument('--no-sandbox')
        co.set_argument('--window-size=415,900') # 页面大小设置为415*900
        
        # 防检测参数
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_pref('credentials_enable_service', False)
        
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-extensions')
        co.set_argument('--disable-logging')
        co.set_argument('--disable-background-networking')
        co.set_argument('--disable-default-apps')
        co.set_argument('--disable-sync')
        co.set_argument('--disable-translate')
        co.set_argument('--no-first-run')
        co.set_argument('--safebrowsing-disable-auto-update')
        co.set_argument('--ignore-certificate-errors')
        co.set_argument('--ignore-ssl-errors')
        co.set_argument('--disable-web-security')
        co.set_argument('--allow-running-insecure-content')
        co.set_argument('--disable-features=IsolateOrigins,site-per-process')
        co.set_argument('--disable-site-isolation-trials')
        co.set_argument('--single-process')
        co.set_argument('--disable-setuid-sandbox')
        co.set_argument('--disable-hang-monitor')
        co.set_argument('--disable-popup-blocking')
        co.set_argument('--disable-prompt-on-repost')
        co.set_argument('--disable-backgrounding-occluded-windows')
        co.set_argument('--disable-renderer-backgrounding')
        co.set_argument('--disable-ipc-flooding-protection')
        co.set_argument('--memory-pressure-off')
        co.set_argument('--js-flags=--max-old-space-size=512')
        
        co.set_timeouts(base=60, page_load=60, script=60)
        
        # 随机 User-Agent
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        co.set_user_agent(random.choice(ua_list))

        page = ChromiumPage(addr_or_opts=co)
        page.set.timeouts(base=60, page_load=60, script=60)
        
        return page

    def _safe_quit_browser(self, page):
        """安全关闭浏览器"""
        if page is None:
            return
        try:
            page.quit()
        except Exception:
            pass
        try:
            if hasattr(page, '_browser') and page._browser:
                page._browser.quit()
        except Exception:
            pass

    def _run_cdp_safe(self, page, method, **kwargs):
        """安全执行 CDP 命令"""
        max_retries = 3
        for i in range(max_retries):
            try:
                return page.run_cdp(method, **kwargs)
            except Exception as e:
                if i < max_retries - 1:
                    time.sleep(0.5)
                else:
                    raise e

    def _slide_logic(self, page):
        """基于JS脚本逻辑的Python实现"""
        try:
            slider = page.ele('#aliyunCaptcha-sliding-slider', timeout=5)
            wrapper = page.ele('#aliyunCaptcha-sliding-wrapper', timeout=5)
            
            if not slider or not wrapper:
                print("❌ 未找到滑块元素")
                return False

            # 获取位置信息
            slider_rect = slider.rect
            wrapper_rect = wrapper.rect
            
            # 计算起点 (slider 中心)
            start_x = slider_rect.location[0] + slider_rect.size[0] / 2
            start_y = slider_rect.location[1] + slider_rect.size[1] / 2
            
            # 需要滑动的距离
            distance_needed = wrapper_rect.size[0] - slider_rect.size[0]
            
            # 1. 过冲: 20-80px
            overshoot = 20 + random.random() * 60
            end_x = start_x + distance_needed + overshoot
            
            # 2. Y轴大幅漂移
            y_drift = (random.random() - 0.5) * 100
            end_y = start_y + y_drift
            
            # 3. 时间: 200ms - 500ms
            total_duration_ms = 200 + random.random() * 300
            start_time = time.time() * 1000
            
            print(f"📍 起点: ({int(start_x)}, {int(start_y)})")
            print(f"🏁 终点 (含过冲 {int(overshoot)}px): ({int(end_x)}, {int(end_y)})")
            
            # 4. 执行滑动 (使用 CDP Input.dispatchMouseEvent 以获得更细粒度的控制)
            
            # MouseDown
            self._run_cdp_safe(page, 'Input.dispatchMouseEvent', type='mousePressed', x=start_x, y=start_y, button='left', clickCount=1)
            
            while True:
                now = time.time() * 1000
                elapsed = now - start_time
                progress = elapsed / total_duration_ms
                
                if progress > 1:
                    progress = 1
                
                # EaseOutQuart
                ease = 1 - pow(1 - progress, 4)
                
                current_x = start_x + (end_x - start_x) * ease
                
                current_y_drift = y_drift * ease
                jitter = (random.random() - 0.5) * 6
                current_y = start_y + current_y_drift + jitter
                
                # MouseMove
                self._run_cdp_safe(page, 'Input.dispatchMouseEvent', type='mouseMoved', x=current_x, y=current_y)
                
                if progress >= 1:
                    break
                
                # 随机间隔 5-10ms
                time.sleep((5 + random.random() * 5) / 1000)
            
            # 4.3 极短停顿
            time.sleep(random.random() * 0.05)
            
            # 4.4 MouseUp (在过冲位置直接松开)
            self._run_cdp_safe(page, 'Input.dispatchMouseEvent', type='mouseReleased', x=end_x, y=end_y, button='left', clickCount=1)
            print(f"🖱️ 滑动完成，耗时 {int(time.time()*1000 - start_time)}ms")
            
            return True

        except Exception as e:
            print(f"滑动过程出错: {e}")
            return False

    def getCap(self):
        page = None
        target_url = "https://aliv3.zhangmonday.top/?prefix=1tbpug&SceneId=6mw4mrmg"
        max_browser_retries = 3
        
        for browser_attempt in range(1, max_browser_retries + 1):
            try:
                print(f"\n🌐 浏览器实例 {browser_attempt}/{max_browser_retries}")
                
                self._safe_quit_browser(page)
                time.sleep(1)
                
                page = self._setup_browser()
                
                # 定义拦截回调
                def on_request_paused(**kwargs):
                    try:
                        req_id = kwargs['requestId']
                        request = kwargs.get('request', {})
                        url = request.get('url', '')
                        
                        # 目标：拦截 https://1tbpug.captcha-open.aliyuncs.com/
                        if '1tbpug.captcha-open.aliyuncs.com' in url:
                            # 获取 Payload
                            post_data = request.get('postData')
                            
                            # 只有当请求包含 CaptchaVerifyParam 时才拦截
                            if post_data and 'CaptchaVerifyParam' in post_data:
                                print(f"🛑 拦截到目标验证请求: {url}")
                                self.intercepted_data = post_data
                                print("✅ 已提取请求载荷")
                                try:
                                    page.run_cdp('Fetch.failRequest', requestId=req_id, errorReason='Aborted')
                                except Exception:
                                    pass
                            else:
                                # 放行初始化请求或其他非验证请求
                                # print(f"⏩ 放行普通请求: {url}")
                                try:
                                    page.run_cdp('Fetch.continueRequest', requestId=req_id)
                                except Exception:
                                    pass
                        else:
                            # 放行其他请求
                            try:
                                page.run_cdp('Fetch.continueRequest', requestId=req_id)
                            except Exception:
                                pass
                    except Exception as e:
                        # 防止回调报错影响流程
                        try:
                            page.run_cdp('Fetch.continueRequest', requestId=kwargs['requestId'])
                        except:
                            pass

                # 启用 Fetch 拦截
                self._run_cdp_safe(page, 'Fetch.enable', patterns=[{'urlPattern': '*'}])
                # 设置回调
                page.driver.set_callback('Fetch.requestPaused', on_request_paused)
                
                max_retries = 10
                for attempt in range(1, max_retries + 1):
                    print(f"\n🔄 第 {attempt}/{max_retries} 次尝试获取验证码...")
                    self.intercepted_data = None
                    self.verifyParam = None
                    self.deviceToken = None
                    self.CertifyId = None
                    
                    try:
                        # 打开/刷新页面
                        page.get(target_url, timeout=30)
                    except Exception as e:
                        print(f"页面加载异常: {e}")
                        if 'timeout' in str(e).lower() or 'stuck' in str(e).lower():
                            print("检测到浏览器超时，准备重启浏览器...")
                            break
                        continue
                    
                    time.sleep(1)
                    
                    # 等待滑块元素出现
                    # 使用 ele_displayed 确保元素可见
                    try:
                        if not page.wait.ele_displayed('#aliyunCaptcha-sliding-slider', timeout=10):
                            print("加载滑块超时，刷新重试...")
                            continue
                    except Exception as e:
                        print(f"等待滑块元素异常: {e}")
                        if 'timeout' in str(e).lower() or 'stuck' in str(e).lower():
                            print("检测到浏览器超时，准备重启浏览器...")
                            break
                        continue
                    
                    time.sleep(0.5)
                    
                    # 执行自动化过滑块逻辑
                    try:
                        if not self._slide_logic(page):
                            continue
                    except Exception as e:
                        print(f"滑块逻辑异常: {e}")
                        if 'timeout' in str(e).lower() or 'stuck' in str(e).lower():
                            print("检测到浏览器超时，准备重启浏览器...")
                            break
                        continue
                    
                    # 等待拦截数据 (最多8秒)
                    print("⏳ 等待拦截 CaptchaVerifyParam...")
                    wait_start = time.time()
                    while time.time() - wait_start < 10:
                        if self.intercepted_data:
                            break
                        time.sleep(0.1)
                    
                    if not self.intercepted_data:
                        print("❌ 超时未拦截到验证数据，重试...")
                        continue
                    
                    # 解析拦截到的数据
                    try:
                        # 数据格式: AccessKeyId=...&CaptchaVerifyParam=...
                        parsed = parse_qs(self.intercepted_data)
                        if 'CaptchaVerifyParam' in parsed:
                            # CaptchaVerifyParam 是 URL 编码的 JSON 字符串
                            verify_param_json = parsed['CaptchaVerifyParam'][0]
                            json_data = json.loads(verify_param_json)
                            
                            self.verifyParam = json_data.get('data')
                            self.deviceToken = json_data.get('deviceToken')
                            self.CertifyId = json_data.get('certifyId')
                            
                            print("🎉 成功解析验证参数")
                            
                            # 立即调用 check-ali-captcha
                            check_res = self.Sumbit_All()
                            
                            # 检查验证结果
                            if check_res and check_res.get('success') and check_res.get('code') == 200:
                                res_data = check_res.get('data', {})
                                if res_data.get('checkSuccess') is False:
                                    print(f"❌ 滑块验证失败: {res_data.get('errMessage')}，重试...")
                                    continue
                                elif 'captchaTicket' in res_data:
                                    print("✅ 滑块验证成功！")
                                    self._safe_quit_browser(page)
                                    return True
                            
                            print(f"❌ 接口验证返回异常: {check_res}，重试...")
                        else:
                            print("❌ 拦截数据中缺失 CaptchaVerifyParam，重试...")
                    
                    except Exception as e:
                        print(f"❌ 解析数据或验证异常: {e}，重试...")
                        continue
                else:
                    continue
                
                print("🔄 浏览器需要重启...")
                continue

            except Exception as e:
                print(f"浏览器实例异常: {e}")
                self._safe_quit_browser(page)
                page = None
                time.sleep(2)
                continue

        print("❌ 达到最大重试次数，获取滑块验证失败。")
        self._safe_quit_browser(page)
        return False

    def Sumbit_All(self):
        if not self.verifyParam:
            print("Missing verifyParam, skipping Sumbit_All")
            return None

        _data = self.verifyParam
        deviceToekn = self.deviceToken

        print('deviceToekn', deviceToekn)
        # print('_data', _data) # 数据太长，注释掉

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

        try:
            response = requests.post(
                'https://passport.jlc.com/api/cas/captcha/v2/check-ali-captcha',
                cookies=cookies,
                headers=headers,
                json=json_data,
                timeout=30
            )

            print(f"Check API Status: {response.status_code}")
            # print('Request Body:', json.dumps(json_data, indent=4, ensure_ascii=False))
            print("Check API Response:", response.text)
            
            resp_json = response.json()
            
            try:
                # 尝试获取 ticket
                if resp_json.get('success') and resp_json.get('data', {}).get('captchaTicket'):
                    self.captchaTicket = resp_json['data']['captchaTicket']
            except Exception as e:
                print("Failed to get captchaTicket from response:", e)

            return resp_json

        except Exception as e:
            print(f"Sumbit_All Error: {e}")
            return None

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
                    print(f"cookie缓存已过期 (上次更新: {time.ctime(last_time)})，重新获取...")
            except Exception as e:
                print(f"读取cookie缓存文件出错: {e}，将重新获取。")
        else:
            print("cookie缓存文件不存在，开始获取...")

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
            stdout, stderr = process.communicate(timeout=120)
            
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
        
        except subprocess.TimeoutExpired:
            print("getcookie.py 执行超时")
            try:
                process.kill()
            except:
                pass
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
            print("检测到 Cookies 或 Headers 为 None，可能是缓存无效，正在删除缓存并重试...")
            
            if os.path.exists(self.cookie_cache_file):
                try:
                    os.remove(self.cookie_cache_file)
                    print(f"已删除无效缓存文件: {self.cookie_cache_file}")
                except Exception as e:
                    print(f"删除缓存文件失败: {e}")
            
            # 重新调用获取
            cookies, headers = self.get_cached_cookies_headers()
            
            if cookies is None or headers is None:
                print("错误：重试后仍未能获取到 Cookies 或 Headers (值为 None)，退出程序。")
                sys.exit(1)

        json_data = {
            'username': username,
            'password': password,
            'isAutoLogin': False,
            'captchaTicket': self.captchaTicket,
        }

        try:
            response = requests.post('https://passport.jlc.com/api/cas/login/with-password', cookies=cookies,
                                     headers=headers, json=json_data, timeout=30)
            print("Login Response:", response.text)
        except Exception as e:
            print(f"Login Request Failed: {e}")

    def test(self):
        pass

    def main(self, username, password):
        # 保存参数到实例变量
        self.username = username
        self.password = password

        # 使用 DrissionPage 获取验证码
        if self.getCap():
            # 传递加密后的账号密码进行登录
            enc_username = pwdEncrypt(username)
            enc_password = pwdEncrypt(password)
            self.Login(enc_username, enc_password)
        else:
            print("验证码流程失败，无法继续登录。")


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
