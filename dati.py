import os
import sys
import time
import json
import tempfile
import subprocess
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 导入SM2加密方法
try:
    from Utils import pwdEncrypt
    print("✅ 成功加载 SM2 加密依赖 (Utils.pwdEncrypt)")
except ImportError:
    print("❌ 错误: 未找到 Utils.py 或 pwdEncrypt 函数，请确保同目录下存在该文件")
    sys.exit(1)


def log(msg):
    """带时间戳的日志输出"""
    full_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(full_msg, flush=True)


def call_aliv3min_with_timeout(timeout_seconds=180, max_retries=3):
    """
    调用 AliV3min.py 获取 captchaTicket
    超时3分钟则打印日志并强制结束，最多重试3次
    返回 captchaTicket 或 None
    """
    for attempt in range(max_retries):
        log(f"📞 调用 AliV3min.py 获取 captchaTicket (尝试 {attempt + 1}/{max_retries})...")
        
        try:
            process = subprocess.Popen(
                [sys.executable, 'AliV3min.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            output_lines = []
            start_time = time.time()
            captcha_ticket = None
            
            while True:
                # 检查超时
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    log(f"⏰ AliV3min.py 超过 {timeout_seconds} 秒未完成，强制终止...")
                    process.kill()
                    process.wait()
                    
                    # 打印所有已收集的日志
                    log("--- AliV3min.py 超时前的日志 ---")
                    for line in output_lines:
                        print(line, end='')
                    log("--- 日志结束 ---")
                    break
                
                # 非阻塞读取输出
                try:
                    line = process.stdout.readline()
                    if line:
                        output_lines.append(line)
                        # 实时打印子进程输出
                        print(f"  [AliV3min] {line.rstrip()}")
                        
                        # 检查是否包含 captchaTicket
                        if "SUCCESS: Obtained CaptchaTicket:" in line:
                            # 下一行应该是 ticket
                            next_line = process.stdout.readline()
                            if next_line:
                                output_lines.append(next_line)
                                captcha_ticket = next_line.strip()
                                log(f"✅ 成功获取 captchaTicket: {captcha_ticket[:20]}...")
                        
                        # 也尝试从JSON响应中提取
                        if '"captchaTicket"' in line:
                            try:
                                json_match = re.search(r'"captchaTicket"\s*:\s*"([^"]+)"', line)
                                if json_match:
                                    captcha_ticket = json_match.group(1)
                                    log(f"✅ 从JSON响应中提取到 captchaTicket: {captcha_ticket[:20]}...")
                            except:
                                pass
                    
                    # 检查进程是否结束
                    if process.poll() is not None:
                        # 读取剩余输出
                        remaining = process.stdout.read()
                        if remaining:
                            output_lines.append(remaining)
                            for rem_line in remaining.split('\n'):
                                if rem_line.strip():
                                    print(f"  [AliV3min] {rem_line}")
                        break
                        
                except Exception as e:
                    time.sleep(0.1)
                    continue
            
            if captcha_ticket:
                return captcha_ticket
            else:
                log(f"❌ 未能从 AliV3min.py 输出中提取到 captchaTicket")
                if attempt < max_retries - 1:
                    log(f"⏳ 等待 3 秒后重试...")
                    time.sleep(3)
                    
        except Exception as e:
            log(f"❌ 调用 AliV3min.py 异常: {e}")
            if attempt < max_retries - 1:
                log(f"⏳ 等待 3 秒后重试...")
                time.sleep(3)
    
    return None


def send_request_via_browser(driver, url, method='POST', body=None):
    """
    通过浏览器控制台发送请求
    返回响应的JSON对象或None
    """
    try:
        if body:
            body_str = json.dumps(body, ensure_ascii=False)
            js_code = """
            var url = arguments[0];
            var bodyData = arguments[1];
            var callback = arguments[2];
            
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/plain, */*'
                },
                body: bodyData,
                credentials: 'include'
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                callback(JSON.stringify(data));
            })
            .catch(function(error) {
                callback(JSON.stringify({error: error.message}));
            });
            """
            result = driver.execute_async_script(js_code, url, body_str)
        else:
            js_code = """
            var url = arguments[0];
            var callback = arguments[1];
            
            fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/plain, */*'
                },
                credentials: 'include'
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                callback(JSON.stringify(data));
            })
            .catch(function(error) {
                callback(JSON.stringify({error: error.message}));
            });
            """
            result = driver.execute_async_script(js_code, url)
        
        if result:
            return json.loads(result)
        return None
    except Exception as e:
        log(f"❌ 浏览器请求失败: {e}")
        return None


def login_with_password(driver, username, password, captcha_ticket):
    """
    使用账号密码登录
    返回: 'success', 'password_error', 'other_error', 响应数据
    """
    url = "https://passport.jlc.com/api/cas/login/with-password"
    
    # SM2加密账号密码
    try:
        encrypted_username = pwdEncrypt(username)
        encrypted_password = pwdEncrypt(password)
        log(f"🔐 账号密码已加密")
    except Exception as e:
        log(f"❌ SM2加密失败: {e}")
        return 'other_error', None
    
    body = {
        'username': encrypted_username,
        'password': encrypted_password,
        'isAutoLogin': False,
        'captchaTicket': captcha_ticket
    }
    
    log(f"📡 发送登录请求...")
    response = send_request_via_browser(driver, url, 'POST', body)
    
    if response:
        log(f"📨 登录响应: {json.dumps(response, ensure_ascii=False)[:300]}...")
        
        # 检查登录成功 (code=2017 表示成功)
        if response.get('success') == True and response.get('code') == 2017:
            auth_code = response.get('data', {}).get('authCode')
            if auth_code:
                log(f"✅ 登录成功! authCode: {auth_code[:20]}...")
                return 'success', response
        
        # 检查密码错误
        if response.get('code') == 10208:
            log(f"❌ 账号或密码不正确: {response.get('message', '')}")
            return 'password_error', response
        
        # 其他情况
        log(f"⚠ 登录返回异常: code={response.get('code')}, message={response.get('message', '')}")
        return 'other_error', response
    
    return 'other_error', None


def verify_login_on_member_page(driver, max_retries=3):
    """
    验证登录成功 - 检查member.jlc.com页面上的客编
    返回True/False
    """
    for attempt in range(max_retries):
        log(f"🔍 验证登录状态 (尝试 {attempt + 1}/{max_retries})...")
        
        try:
            driver.get("https://member.jlc.com/")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            log("⏳ 页面加载完成，额外等待5秒...")
            time.sleep(5)
            
            # 检查是否有客编信息
            page_source = driver.page_source
            
            # 尝试多种匹配方式
            patterns = [
                r'客编\s*[A-Z0-9]+',
                r'customer-popover-title.*?客编\s*[A-Z0-9]+',
                r'customerCode.*?[A-Z0-9]{8}'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_source)
                if match:
                    log(f"✅ 验证登录成功! 找到客编信息: {match.group()}")
                    return True
            
            # 也可以通过元素查找
            try:
                customer_elem = driver.find_element(By.XPATH, '//*[contains(text(), "客编")]')
                if customer_elem:
                    log(f"✅ 验证登录成功! 找到客编元素: {customer_elem.text[:50]}")
                    return True
            except:
                pass
            
            log(f"⚠ 未找到客编信息，当前URL: {driver.current_url}")
            log(f"⚠ 页面标题: {driver.title}")
            
        except Exception as e:
            log(f"❌ 验证登录异常: {e}")
        
        if attempt < max_retries - 1:
            log("🔄 刷新页面重试...")
            time.sleep(2)
    
    return False


def click_start_exam_button(driver, max_retries=3):
    """
    点击开始答题按钮
    返回True/False
    """
    for attempt in range(max_retries):
        log(f"🔍 查找开始答题按钮 (尝试 {attempt + 1}/{max_retries})...")
        
        try:
            # 等待页面稳定
            time.sleep(3)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # 尝试查找按钮 - 方式1: ID
            try:
                start_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "startExamBtn"))
                )
                log("✅ 找到开始答题按钮(ID)，点击中...")
                start_btn.click()
                return True
            except:
                pass
            
            # 方式2: XPath查找按钮
            try:
                start_btn = driver.find_element(By.XPATH, '//button[contains(@class, "btn-primary")]//span[contains(text(), "开始答题")]/..')
                log("✅ 通过XPath找到开始答题按钮，点击中...")
                start_btn.click()
                return True
            except:
                pass
            
            # 方式3: 直接找span
            try:
                start_btn = driver.find_element(By.XPATH, '//span[contains(@class, "startExam")]')
                log("✅ 找到开始答题span，点击中...")
                start_btn.click()
                return True
            except:
                pass
            
            # 方式4: 模糊匹配
            try:
                start_btn = driver.find_element(By.XPATH, '//*[contains(text(), "开始答题")]')
                log("✅ 找到开始答题文本，点击中...")
                start_btn.click()
                return True
            except:
                pass
            
            log(f"⚠ 未找到开始答题按钮")
            log(f"  当前页面标题: {driver.title}")
            log(f"  当前页面URL: {driver.current_url}")
            
        except Exception as e:
            log(f"❌ 查找按钮异常: {e}")
        
        if attempt < max_retries - 1:
            log("🔄 刷新页面重试...")
            driver.refresh()
            time.sleep(3)
    
    return False


def wait_for_exam_completion(driver, timeout_seconds=180):
    """
    等待答题完成（页面重定向）
    返回True/False
    """
    log(f"⏳ 等待答题脚本执行完成 (最长等待 {timeout_seconds} 秒)...")
    
    initial_url = driver.current_url
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        try:
            current_url = driver.current_url
            
            # 检查URL是否变化（重定向到分数页面）
            if current_url != initial_url:
                # 检查是否是分数页面
                if 'result' in current_url.lower() or 'score' in current_url.lower() or 'finish' in current_url.lower():
                    log(f"✅ 检测到页面重定向到分数页面: {current_url}")
                    return True
                # 可能是中间跳转
                log(f"📍 页面跳转: {current_url}")
                initial_url = current_url
        except:
            pass
        
        time.sleep(2)
    
    log(f"⏰ 等待超时 ({timeout_seconds} 秒)，脚本可能未成功执行")
    return False


def get_exam_score(driver):
    """
    获取考试分数
    返回分数(int)或None
    """
    log("🔍 获取考试分数...")
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        
        # 方式1: class="score"
        try:
            score_elem = driver.find_element(By.CLASS_NAME, "score")
            score_text = score_elem.text.strip()
            score = int(re.search(r'\d+', score_text).group())
            log(f"📊 获取到分数: {score}")
            return score
        except:
            pass
        
        # 方式2: XPath
        try:
            score_elem = driver.find_element(By.XPATH, '//span[@class="score"]')
            score_text = score_elem.text.strip()
            score = int(re.search(r'\d+', score_text).group())
            log(f"📊 获取到分数: {score}")
            return score
        except:
            pass
        
        # 方式3: 搜索页面源码
        page_source = driver.page_source
        score_match = re.search(r'<span[^>]*class="score"[^>]*>(\d+)</span>', page_source)
        if score_match:
            score = int(score_match.group(1))
            log(f"📊 从页面源码获取到分数: {score}")
            return score
        
        log("⚠ 未能找到分数元素")
        return None
        
    except Exception as e:
        log(f"❌ 获取分数异常: {e}")
        return None


def create_chrome_driver(with_extension=False, extension_path=None):
    """
    创建Chrome浏览器实例
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 加载扩展
    if with_extension and extension_path and os.path.exists(extension_path):
        chrome_options.add_extension(extension_path)
        log(f"📦 已加载扩展: {extension_path}")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def process_single_account(username, password, account_index, total_accounts):
    """
    处理单个账号的完整流程
    返回结果字典
    """
    result = {
        'account_index': account_index,
        'username': username,
        'status': '未知',
        'success': False,
        'score': None,
        'highest_score': 0,
        'failure_reason': None,
        'attempts': 0
    }
    
    max_full_retries = 3  # 整个流程最多重试3次
    
    for full_attempt in range(max_full_retries):
        result['attempts'] = full_attempt + 1
        
        if full_attempt > 0:
            log(f"🔄 账号 {account_index} 整体流程第 {full_attempt + 1} 次重试...")
        
        log(f"{'='*60}")
        log(f"📋 开始处理账号 {account_index}/{total_accounts}: {username[:3]}***{username[-3:] if len(username) > 6 else ''}")
        log(f"{'='*60}")
        
        driver = None
        
        try:
            # 步骤1: 创建浏览器并打开passport.jlc.com
            log("🌐 步骤1: 打开 passport.jlc.com...")
            driver = create_chrome_driver()
            driver.get("https://passport.jlc.com")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            log("✅ 页面加载完成")
            
            # 步骤2: 发送初始化会话请求
            log("🌐 步骤2: 初始化会话...")
            init_retry_count = 0
            init_success = False
            
            while init_retry_count < 3:
                response = send_request_via_browser(
                    driver, 
                    "https://passport.jlc.com/api/cas/login/get-init-session",
                    'POST',
                    {"appId": "JLC_PORTAL_PC", "clientType": "PC-WEB"}
                )
                
                if response:
                    log(f"📨 初始化响应: {json.dumps(response, ensure_ascii=False)}")
                    if response.get('success') == True and response.get('code') == 200:
                        log("✅ 初始化会话成功")
                        init_success = True
                        break
                    else:
                        log(f"⚠ 响应异常: {response}")
                else:
                    log("❌ 请求无响应")
                
                init_retry_count += 1
                if init_retry_count < 3:
                    log(f"⚠ 初始化失败，关闭浏览器重试 ({init_retry_count}/3)...")
                    driver.quit()
                    time.sleep(2)
                    driver = create_chrome_driver()
                    driver.get("https://passport.jlc.com")
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    time.sleep(2)
            
            if not init_success:
                log("❌ 初始化会话失败超过3次，退出程序")
                result['status'] = '初始化失败'
                result['failure_reason'] = '初始化会话失败'
                if driver:
                    driver.quit()
                sys.exit(1)
            
            # 步骤3: 调用AliV3min.py获取captchaTicket
            log("🌐 步骤3: 获取验证码Ticket...")
            driver.quit()
            driver = None
            
            captcha_ticket = call_aliv3min_with_timeout(timeout_seconds=180, max_retries=3)
            
            if not captcha_ticket:
                log("❌ 获取captchaTicket失败超过3次，退出程序")
                result['status'] = 'captchaTicket获取失败'
                result['failure_reason'] = '验证码获取失败'
                sys.exit(1)
            
            # 重新创建浏览器
            driver = create_chrome_driver()
            driver.get("https://passport.jlc.com")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            # 步骤4: 发送登录请求
            log("🌐 步骤4: 发送登录请求...")
            login_status, login_response = login_with_password(driver, username, password, captcha_ticket)
            
            if login_status == 'password_error':
                log(f"❌ 账号 {account_index} 账号或密码不正确，跳过该账号")
                result['status'] = '密码错误'
                result['failure_reason'] = '账号或密码不正确'
                driver.quit()
                return result
            
            if login_status == 'other_error':
                log(f"⚠ 登录返回其他错误，将重试整个流程...")
                driver.quit()
                driver = None
                time.sleep(3)
                continue
            
            if login_status != 'success':
                log(f"⚠ 登录未成功，将重试整个流程...")
                driver.quit()
                driver = None
                time.sleep(3)
                continue
            
            # 步骤5: 验证登录成功
            log("🌐 步骤5: 验证登录状态...")
            login_verified = verify_login_on_member_page(driver)
            
            if not login_verified:
                log(f"⚠ 验证登录失败，将重试整个流程...")
                driver.quit()
                driver = None
                time.sleep(3)
                continue
            
            # 步骤6: 安装插件并打开答题页面
            log("🌐 步骤6: 准备答题...")
            driver.quit()
            driver = None
            
            # 检查插件是否存在
            extension_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'JLCTK.crx')
            if not os.path.exists(extension_path):
                log(f"⚠ 警告: 未找到插件文件 {extension_path}")
                extension_path = None
            
            # 重新创建带插件的浏览器
            driver = create_chrome_driver(with_extension=True, extension_path=extension_path)
            
            # 需要重新登录（新的浏览器实例）
            driver.get("https://passport.jlc.com")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            # 重新获取captchaTicket并登录
            log("🔄 重新获取验证码并登录...")
            driver.quit()
            driver = None
            
            captcha_ticket = call_aliv3min_with_timeout(timeout_seconds=180, max_retries=3)
            if not captcha_ticket:
                log("❌ 重新获取captchaTicket失败")
                time.sleep(3)
                continue
            
            # 重新创建带插件的浏览器
            driver = create_chrome_driver(with_extension=True, extension_path=extension_path)
            driver.get("https://passport.jlc.com")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            login_status, _ = login_with_password(driver, username, password, captcha_ticket)
            if login_status != 'success':
                log("❌ 重新登录失败")
                driver.quit()
                driver = None
                time.sleep(3)
                continue
            
            # 答题流程，最多重试3次
            exam_url = "https://member.jlc.com/integrated/exam-center/intermediary?examinationRelationUrl=https%3A%2F%2Fexam.kaoshixing.com%2Fexam%2Fbefore_answer_notice%2F1647581&examinationRelationId=1647581"
            
            for exam_attempt in range(3):
                log(f"📝 答题尝试 {exam_attempt + 1}/3...")
                
                driver.get(exam_url)
                log("⏳ 等待页面加载和重定向...")
                time.sleep(10)
                
                try:
                    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                except:
                    pass
                
                log(f"📍 当前页面: {driver.current_url}")
                log(f"📍 页面标题: {driver.title}")
                
                # 点击开始答题按钮
                if not click_start_exam_button(driver, max_retries=3):
                    log(f"❌ 无法找到开始答题按钮")
                    log(f"  页面标题: {driver.title}")
                    log(f"  页面URL: {driver.current_url}")
                    if exam_attempt < 2:
                        log("🔄 刷新页面重试...")
                        continue
                    else:
                        result['failure_reason'] = '无法找到开始答题按钮'
                        break
                
                log("⏳ 等待组卷 (约10秒)...")
                time.sleep(10)
                
                # 等待答题完成（插件自动运行）
                exam_completed = wait_for_exam_completion(driver, timeout_seconds=180)
                
                if not exam_completed:
                    log(f"⏰ 答题超时 (超过3分钟)，脚本未成功执行")
                    result['failure_reason'] = '脚本超过3分钟未执行成功'
                    if exam_attempt < 2:
                        log("🔄 重新开始答题...")
                        continue
                    else:
                        break
                
                # 获取分数
                time.sleep(3)
                score = get_exam_score(driver)
                
                if score is not None:
                    result['score'] = score
                    if score > result['highest_score']:
                        result['highest_score'] = score
                    
                    if score >= 60:
                        log(f"🎉 答题成功! 分数: {score} 分 (≥60分)")
                        result['status'] = '答题成功'
                        result['success'] = True
                        driver.quit()
                        return result
                    else:
                        log(f"😢 分数不及格: {score} 分 (<60分)")
                        result['failure_reason'] = f'最高得分{result["highest_score"]}'
                        if exam_attempt < 2:
                            log("🔄 重新答题...")
                            continue
                else:
                    log("⚠ 无法获取分数")
                    result['failure_reason'] = '无法获取分数'
                    if exam_attempt < 2:
                        continue
            
            # 答题3次都没过
            if not result['success']:
                result['status'] = '答题失败'
                if result['highest_score'] > 0:
                    result['failure_reason'] = f'最高得分{result["highest_score"]}'
            
            driver.quit()
            return result
            
        except Exception as e:
            log(f"❌ 处理账号时发生异常: {e}")
            result['status'] = '异常'
            result['failure_reason'] = str(e)
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            if full_attempt < max_full_retries - 1:
                log(f"⏳ 等待3秒后重试整个流程...")
                time.sleep(3)
                continue
        
        finally:
            if driver:
                try:
                    driver.quit()
                    log("🔒 浏览器已关闭")
                except:
                    pass
    
    # 3次整体流程都失败
    if not result['success'] and result['status'] == '未知':
        result['status'] = '重试失败'
        result['failure_reason'] = '整体流程重试3次均失败'
    
    return result


def main():
    """主函数"""
    # 解析命令行参数
    if len(sys.argv) < 3:
        print("用法: python jlc.py 账号1,账号2,账号3... 密码1,密码2,密码3... [失败退出标志]")
        print("示例: python jlc.py user1,user2,user3 pwd1,pwd2,pwd3")
        print("示例: python jlc.py user1,user2,user3 pwd1,pwd2,pwd3 true")
        print("失败退出标志: 不传或任意值-关闭, true-开启(任意账号答题失败时返回非零退出码)")
        sys.exit(1)
    
    # 解析账号密码
    usernames = [u.strip() for u in sys.argv[1].split(',') if u.strip()]
    passwords = [p.strip() for p in sys.argv[2].split(',') if p.strip()]
    
    # 解析失败退出标志
    enable_failure_exit = False
    if len(sys.argv) >= 4:
        enable_failure_exit = (sys.argv[3].lower() == 'true')
    
    # 验证账号密码数量匹配
    if len(usernames) != len(passwords):
        log("❌ 错误: 账号和密码数量不匹配!")
        log(f"   账号数量: {len(usernames)}, 密码数量: {len(passwords)}")
        sys.exit(1)
    
    total_accounts = len(usernames)
    
    log("=" * 70)
    log("🚀 立创题库自动答题程序启动")
    log("=" * 70)
    log(f"📊 账号总数: {total_accounts}")
    log(f"🚪 失败退出功能: {'开启' if enable_failure_exit else '关闭'}")
    log("=" * 70)
    
    # 存储所有结果
    all_results = []
    
    # 处理每个账号
    for i, (username, password) in enumerate(zip(usernames, passwords), 1):
        log(f"\n{'#' * 70}")
        log(f"# 账号 {i}/{total_accounts}")
        log(f"{'#' * 70}\n")
        
        result = process_single_account(username, password, i, total_accounts)
        all_results.append(result)
        
        # 账号之间的间隔
        if i < total_accounts:
            wait_time = 5
            log(f"\n⏳ 等待 {wait_time} 秒后处理下一个账号...\n")
            time.sleep(wait_time)
    
    # 输出总结
    log("\n" + "=" * 70)
    log("📊 答题结果总结")
    log("=" * 70)
    
    success_count = 0
    failed_accounts = []
    failed_details = []
    
    for result in all_results:
        account_index = result['account_index']
        username = result['username']
        masked_username = f"{username[:3]}***" if len(username) > 3 else username
        
        log(f"\n账号 {account_index} ({masked_username}):")
        
        if result['success']:
            score = result.get('score', result.get('highest_score', 0))
            log(f"  立创题库答题成功 ✅ 分数: {score}")
            success_count += 1
        else:
            failure_reason = result.get('failure_reason', '未知原因')
            
            # 根据不同情况显示不同信息
            if result['status'] == '密码错误':
                log(f"  立创题库答题失败 ❌ 原因: 账号或密码错误")
                failed_details.append(f"账号{account_index}: 密码错误")
            elif result['highest_score'] > 0:
                log(f"  立创题库答题失败 ❌ 原因: 最高得分 {result['highest_score']}")
                failed_details.append(f"账号{account_index}: 最高得分{result['highest_score']}")
            elif '3分钟' in str(failure_reason):
                log(f"  立创题库答题失败 ❌ 原因: 脚本超过3分钟未执行成功")
                failed_details.append(f"账号{account_index}: 脚本超时")
            else:
                log(f"  立创题库答题失败 ❌ 原因: {failure_reason}")
                failed_details.append(f"账号{account_index}: {failure_reason}")
            
            failed_accounts.append(account_index)
    
    # 统计信息
    log("\n" + "-" * 70)
    pass_rate = (success_count / total_accounts * 100) if total_accounts > 0 else 0
    log(f"📈 答题通过率: {success_count}/{total_accounts} ({pass_rate:.1f}%)")
    
    if failed_accounts:
        log(f"❌ 答题未通过的账号: {', '.join(map(str, failed_accounts))}")
        for detail in failed_details:
            log(f"   - {detail}")
    else:
        log("🎉 所有账号答题全部通过!")
    
    log("=" * 70)
    
    # 根据失败退出标志决定退出码
    if enable_failure_exit and pass_rate < 100:
        log("❌ 检测到有账号答题失败，且开启了失败退出功能，返回退出码 1")
        sys.exit(1)
    else:
        log("✅ 程序执行完成，返回退出码 0")
        sys.exit(0)


if __name__ == "__main__":
    main()
