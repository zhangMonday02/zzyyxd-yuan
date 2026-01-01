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


def create_chrome_driver(with_extension=True):
    """
    创建Chrome浏览器实例 - 包含防检测配置和插件加载
    """
    chrome_options = Options()
    
    # --- 防检测核心配置 ---
    # 1. 使用新版无头模式
    chrome_options.add_argument("--headless=new") 
    
    # 2. 伪造 User-Agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 3. 禁用自动化控制特征
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 4. 常规配置
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    
    # --- 插件加载 (启动时即加载) ---
    if with_extension:
        extension_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'JLCTK.crx')
        if os.path.exists(extension_path):
            chrome_options.add_extension(extension_path)
            log(f"📦 已配置加载插件: {extension_path}")
        else:
            log(f"⚠ 警告: 未找到插件文件 {extension_path}，将不加载插件")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # --- CDP 命令防检测 (关键) ---
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })
    
    return driver


def call_aliv3min_with_timeout(timeout_seconds=180, max_retries=3):
    """
    调用 AliV3min.py 获取 captchaTicket
    """
    for attempt in range(max_retries):
        log(f"📞 调用 AliV3min.py 获取 captchaTicket (尝试 {attempt + 1}/{max_retries})...")
        
        try:
            if not os.path.exists('AliV3min.py'):
                log("❌ 错误: 找不到 AliV3min.py")
                return None

            process = subprocess.Popen(
                [sys.executable, 'AliV3min.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            start_time = time.time()
            captcha_ticket = None
            
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    log(f"⏰ AliV3min.py 超过 {timeout_seconds} 秒未完成，强制终止...")
                    process.kill()
                    process.wait()
                    break
                
                try:
                    line = process.stdout.readline()
                    if line:
                        if "SUCCESS: Obtained CaptchaTicket:" in line:
                            next_line = process.stdout.readline()
                            if next_line:
                                captcha_ticket = next_line.strip()
                                log(f"✅ 成功获取 captchaTicket: {captcha_ticket[:20]}...")
                                process.terminate()
                                return captcha_ticket

                        if "captchaTicket" in line:
                            try:
                                match = re.search(r'"captchaTicket"\s*:\s*"([^"]+)"', line)
                                if match:
                                    captcha_ticket = match.group(1)
                                    log(f"✅ 从JSON提取到 captchaTicket: {captcha_ticket[:20]}...")
                                    process.terminate()
                                    return captcha_ticket
                            except:
                                pass
                    
                    if process.poll() is not None:
                        remaining = process.stdout.read()
                        if remaining:
                            if "captchaTicket" in remaining:
                                match = re.search(r'"captchaTicket"\s*:\s*"([^"]+)"', remaining)
                                if match:
                                    return match.group(1)
                        break
                        
                except Exception:
                    time.sleep(0.1)
            
            if captcha_ticket:
                return captcha_ticket
            else:
                log(f"❌ 本次尝试未获取到 Ticket")
                time.sleep(2)
                    
        except Exception as e:
            log(f"❌ 调用 AliV3min.py 异常: {e}")
            time.sleep(2)
    
    return None


def send_request_via_browser(driver, url, method='POST', body=None):
    """通过浏览器控制台发送请求"""
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
                    'Accept': 'application/json, text/plain, */*',
                    'AppId': 'JLC_PORTAL_PC',
                    'ClientType': 'PC-WEB'
                },
                body: bodyData,
                credentials: 'include'
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        try {
                            return JSON.stringify({error: "HTTP Error " + response.status, body: text});
                        } catch(e) {
                            return JSON.stringify({error: "HTTP Error " + response.status});
                        }
                    });
                }
                return response.json().then(data => JSON.stringify(data));
            })
            .then(data => callback(data))
            .catch(error => callback(JSON.stringify({error: error.toString()})));
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
            .then(response => response.json().then(data => JSON.stringify(data)))
            .then(data => callback(data))
            .catch(error => callback(JSON.stringify({error: error.toString()})));
            """
            result = driver.execute_async_script(js_code, url)
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            log(f"❌ 响应不是有效的 JSON: {result[:100]}...")
            return None
            
    except Exception as e:
        log(f"❌ 浏览器请求执行脚本失败: {e}")
        return None


def perform_init_session(driver, max_retries=3):
    """执行 Session 初始化"""
    for i in range(max_retries):
        log(f"📡 初始化会话 (Attempt {i+1})...")
        response = send_request_via_browser(
            driver, 
            "https://passport.jlc.com/api/cas/login/get-init-session",
            'POST',
            {"appId": "JLC_PORTAL_PC", "clientType": "PC-WEB"}
        )
        
        if response and response.get('success') == True and response.get('code') == 200:
            log("✅ 初始化会话成功 (lsId Cookie 已设置)")
            return True
        else:
            log(f"⚠ 初始化响应异常: {response}")
            time.sleep(2)
    return False


def login_with_password(driver, username, password, captcha_ticket):
    """登录"""
    url = "https://passport.jlc.com/api/cas/login/with-password"
    
    try:
        encrypted_username = pwdEncrypt(username)
        encrypted_password = pwdEncrypt(password)
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
    
    if not response:
        return 'other_error', None
        
    log(f"📨 登录响应: {json.dumps(response, ensure_ascii=False)[:200]}...")
    
    if response.get('success') == True and response.get('code') == 2017:
        return 'success', response
    
    if response.get('code') == 10208:
        return 'password_error', response
        
    return 'other_error', response


def verify_login_on_member_page(driver, max_retries=3):
    """验证登录"""
    for attempt in range(max_retries):
        log(f"🔍 验证登录状态 ({attempt + 1}/{max_retries})...")
        try:
            driver.get("https://member.jlc.com/")
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5) 
            
            page_source = driver.page_source
            if "客编" in page_source or "customerCode" in page_source:
                log(f"✅ 验证登录成功")
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def click_start_exam_button(driver, max_retries=3):
    """点击开始答题"""
    for attempt in range(max_retries):
        log(f"🔍 查找开始答题按钮 ({attempt + 1}/{max_retries})...")
        try:
            # 确保页面加载
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            # 尝试多种定位方式
            xpaths = [
                '//*[@id="startExamBtn"]',
                '//button[contains(@class, "btn-primary")]//span[contains(text(), "开始答题")]',
                '//span[contains(text(), "开始答题")]'
            ]
            
            for xpath in xpaths:
                try:
                    elem = driver.find_element(By.XPATH, xpath)
                    if elem.is_displayed():
                        try:
                            elem.click()
                        except:
                            driver.execute_script("arguments[0].click();", elem)
                        log("✅ 点击开始答题按钮")
                        return True
                except:
                    continue
            
            # 如果没找到，打印调试信息
            log(f"⚠ 未找到开始按钮。当前页面信息:")
            log(f"  URL: {driver.current_url}")
            log(f"  标题: {driver.title}")
            # 只截取部分源码防止日志过长
            html_snippet = driver.page_source[:2000]
            log(f"  源码前2000字符: {html_snippet}")
            
        except Exception as e:
            log(f"⚠ 查找按钮出错: {e}")
            
        if attempt < max_retries - 1:
            log("🔄 刷新页面重试...")
            driver.refresh()
            time.sleep(5) # 刷新后多等待一会
            
    return False


def wait_for_exam_completion(driver, timeout_seconds=180):
    """等待答题完成 (URL变化)"""
    log(f"⏳ 等待答题脚本执行 (最长 {timeout_seconds}s)...")
    start_time = time.time()
    initial_url = driver.current_url
    
    while time.time() - start_time < timeout_seconds:
        try:
            current_url = driver.current_url
            # 只要URL变了，且包含结果页特征
            if current_url != initial_url and ('result' in current_url or 'score' in current_url):
                log(f"✅ 检测到跳转至结果页: {current_url}")
                return True
        except:
            pass
        time.sleep(2)
    
    log("⏰ 答题超时")
    return False


def get_exam_score(driver):
    """获取分数"""
    log("🔍 获取分数...")
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        
        # 尝试从页面源码正则提取
        page_source = driver.page_source
        match = re.search(r'class="score"[^>]*>(\d+)', page_source)
        if match:
            score = int(match.group(1))
            log(f"📊 提取到分数: {score}")
            return score
            
        # 尝试元素查找
        try:
            elem = driver.find_element(By.CLASS_NAME, "score")
            return int(re.search(r'\d+', elem.text).group())
        except:
            pass
            
    except Exception as e:
        log(f"❌ 获取分数失败: {e}")
    return None


def process_single_account(username, password, account_index, total_accounts):
    """处理单个账号"""
    result = {
        'account_index': account_index,
        'username': username,
        'status': '未知',
        'success': False,
        'score': 0,
        'highest_score': 0,
        'failure_reason': None
    }
    
    max_process_retries = 3
    
    for process_attempt in range(max_process_retries):
        if process_attempt > 0:
            log(f"\n🔄 账号 {account_index} 全流程重试 ({process_attempt+1}/{max_process_retries})...")
            
        driver = None
        try:
            # 1. 启动浏览器 (带插件 + 防检测)
            log("🌐 启动浏览器...")
            driver = create_chrome_driver(with_extension=True)
            
            # 2. 打开页面
            driver.get("https://passport.jlc.com")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # 3. 初始化 Session
            if not perform_init_session(driver):
                raise Exception("初始化 Session 失败")
            
            # 4. 获取 Ticket
            captcha_ticket = call_aliv3min_with_timeout()
            if not captcha_ticket:
                raise Exception("获取 CaptchaTicket 失败")
            
            # 5. 登录
            status, login_res = login_with_password(driver, username, password, captcha_ticket)
            
            if status == 'password_error':
                result['status'] = '密码错误'
                result['failure_reason'] = '账号或密码不正确'
                return result
                
            if status != 'success':
                raise Exception(f"登录失败: {login_res}")
                
            # 6. 验证登录
            if not verify_login_on_member_page(driver):
                raise Exception("登录验证失败 (未找到客编)")
                
            # 7. 答题流程
            exam_url = "https://member.jlc.com/integrated/exam-center/intermediary?examinationRelationUrl=https%3A%2F%2Fexam.kaoshixing.com%2Fexam%2Fbefore_answer_notice%2F1647581&examinationRelationId=1647581"
            
            for exam_retry in range(3):
                log(f"📝 开始答题 ({exam_retry+1}/3)...")
                driver.get(exam_url)
                
                # 点击开始
                if not click_start_exam_button(driver):
                    log("❌ 找不到开始按钮，刷新重试")
                    continue
                    
                # 等待完成
                if not wait_for_exam_completion(driver):
                    log("❌ 答题超时")
                    result['failure_reason'] = '脚本超过3分钟未执行成功'
                    continue
                    
                # 获取分数
                score = get_exam_score(driver)
                if score is not None:
                    result['score'] = score
                    result['highest_score'] = max(result['highest_score'], score)
                    
                    if score >= 60:
                        log(f"🎉 答题通过! 分数: {score}")
                        result['success'] = True
                        result['status'] = '答题成功'
                        driver.quit()
                        return result
                    else:
                        log(f"😢 分数未达标: {score}")
                        result['failure_reason'] = f"最高得分{result['highest_score']}"
                
            raise Exception("答题多次未通过或超时")

        except Exception as e:
            log(f"❌ 流程异常: {e}")
            result['failure_reason'] = str(e)
            
        finally:
            if driver:
                driver.quit()
                
    result['status'] = '失败'
    return result


def main():
    if len(sys.argv) < 3:
        print("用法: python jlc.py 账号1,账号2... 密码1,密码2... [失败退出标志]")
        sys.exit(1)
        
    usernames = sys.argv[1].split(',')
    passwords = sys.argv[2].split(',')
    fail_exit = len(sys.argv) >= 4 and sys.argv[3].lower() == 'true'
    
    if len(usernames) != len(passwords):
        log("❌ 账号密码数量不匹配")
        sys.exit(1)
        
    all_results = []
    
    for i, (u, p) in enumerate(zip(usernames, passwords), 1):
        log(f"\n{'='*40}\n正在处理账号 {i}/{len(usernames)}: {u}\n{'='*40}")
        res = process_single_account(u, p, i, len(usernames))
        all_results.append(res)
        if i < len(usernames):
            time.sleep(5)
            
    # 总结
    log("\n" + "="*40)
    log("📊 最终结果总结")
    log("="*40)
    
    has_failure = False
    for res in all_results:
        u_mask = res['username'][:3] + "***"
        if res['success']:
            log(f"账号{res['account_index']} ({u_mask}): 立创题库答题成功✅ 分数:{res['score']}")
        else:
            has_failure = True
            log(f"账号{res['account_index']} ({u_mask}): 立创题库答题失败❌ 原因:{res['failure_reason']}")
            
    if fail_exit and has_failure:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
