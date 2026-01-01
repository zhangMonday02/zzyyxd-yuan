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
from selenium.common.exceptions import NoAlertPresentException, UnexpectedAlertPresentException

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


def create_chrome_driver():
    """
    创建Chrome浏览器实例 - 无插件，纯净模式+防检测
    """
    chrome_options = Options()
    
    # --- 防检测核心配置 ---
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # --- 常规配置 ---
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # --- CDP 命令防检测 ---
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })
    
    return driver


def call_aliv3min_with_timeout(timeout_seconds=180, max_retries=3):
    """调用 AliV3min.py 获取 captchaTicket"""
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
                                log(f"✅ 成功获取 captchaTicket")
                                process.terminate()
                                return captcha_ticket

                        if "captchaTicket" in line:
                            try:
                                match = re.search(r'"captchaTicket"\s*:\s*"([^"]+)"', line)
                                if match:
                                    captcha_ticket = match.group(1)
                                    log(f"✅ 成功获取 captchaTicket")
                                    process.terminate()
                                    return captcha_ticket
                            except:
                                pass
                    
                    if process.poll() is not None:
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
            }).then(response => {
                if (!response.ok) { return JSON.stringify({error: "HTTP Error " + response.status}); }
                return response.json().then(data => JSON.stringify(data));
            }).then(data => callback(data)).catch(error => callback(JSON.stringify({error: error.toString()})));
            """
            result = driver.execute_async_script(js_code, url, body_str)
        else:
            js_code = """
            var url = arguments[0];
            var callback = arguments[1];
            fetch(url, {
                method: 'GET',
                headers: {'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*', credentials: 'include'}
            }).then(response => response.json().then(data => JSON.stringify(data))).then(data => callback(data)).catch(error => callback(JSON.stringify({error: error.toString()})));
            """
            result = driver.execute_async_script(js_code, url)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None
    except Exception as e:
        log(f"❌ 浏览器请求执行脚本失败: {e}")
        return None


def perform_init_session(driver, max_retries=3):
    """执行 Session 初始化"""
    for i in range(max_retries):
        log(f"📡 初始化会话 (Attempt {i+1})...")
        response = send_request_via_browser(driver, "https://passport.jlc.com/api/cas/login/get-init-session", 'POST', {"appId": "JLC_PORTAL_PC", "clientType": "PC-WEB"})
        if response and response.get('success') == True and response.get('code') == 200:
            log("✅ 初始化会话成功")
            return True
        else:
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
    
    body = {'username': encrypted_username, 'password': encrypted_password, 'isAutoLogin': False, 'captchaTicket': captcha_ticket}
    log(f"📡 发送登录请求...")
    response = send_request_via_browser(driver, url, 'POST', body)
    if not response: return 'other_error', None
    
    if response.get('success') == True and response.get('code') == 2017: return 'success', response
    if response.get('code') == 10208: return 'password_error', response
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


def switch_to_exam_iframe(driver):
    """尝试切换到答题系统的iframe"""
    try:
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "client_context_frame")))
        driver.switch_to.frame(iframe)
        return True
    except:
        try:
            driver.switch_to.default_content()
            iframe = driver.find_element(By.NAME, "context_iframe")
            driver.switch_to.frame(iframe)
            return True
        except:
            pass
    return False


def extract_real_exam_url(driver):
    """
    在 member.jlc.com 页面内等待iframe加载并出现开始按钮，
    然后提取真实URL。
    """
    log("🔗 正在打开嘉立创中转页...")
    member_exam_url = "https://member.jlc.com/integrated/exam-center/intermediary?examinationRelationUrl=https%3A%2F%2Fexam.kaoshixing.com%2Fexam%2Fbefore_answer_notice%2F1647581&examinationRelationId=1647581"
    driver.get(member_exam_url)
    
    log("⏳ 等待页面及 Iframe 加载 (20s)...")
    
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        
        if switch_to_exam_iframe(driver):
            # 等待按钮出现，说明已经是 kaoshixing 的页面了
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="startExamBtn"] | //span[contains(text(), "开始答题")]'))
            )
            # 提取当前 iframe 的真实 URL
            real_url = driver.execute_script("return window.location.href;")
            driver.switch_to.default_content()
            
            if real_url and "kaoshixing.com" in real_url:
                log(f"✅ 提取真实链接成功")
                return real_url
    except Exception:
        try:
            driver.switch_to.default_content()
        except: pass

    return None


def click_start_exam_button(driver):
    """点击开始答题 (在顶层窗口)"""
    log(f"🔍 检查开始答题按钮...")
    xpaths = ['//*[@id="startExamBtn"]', '//button[contains(@class, "btn-primary")]//span[contains(text(), "开始答题")]', '//span[contains(text(), "开始答题")]']
    
    for xpath in xpaths:
        try:
            elem = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
            if elem.is_displayed():
                try:
                    elem.click()
                except:
                    driver.execute_script("arguments[0].click();", elem)
                log("✅ 点击开始答题按钮")
                return True
        except:
            continue
    log("❌ 未找到开始答题按钮")
    return False


def handle_possible_alerts(driver):
    try:
        alert = driver.switch_to.alert
        log(f"⚠ 检测到弹窗: {alert.text}，正在接受...")
        alert.accept()
        return True
    except NoAlertPresentException:
        return False
    except Exception:
        return False


def inject_dati_js(driver):
    """读取并注入 dati.js"""
    log("💉 正在注入 dati.js 答题脚本...")
    try:
        if not os.path.exists('dati.js'):
            log("❌ 错误: 当前目录下找不到 dati.js 文件")
            return False
            
        with open('dati.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
            
        # 注入 JS
        driver.execute_script(js_content)
        log("✅ 答题脚本注入成功，开始自动答题...")
        return True
    except Exception as e:
        log(f"❌ 注入脚本失败: {e}")
        return False


def wait_for_exam_completion_with_js(driver, timeout_seconds=180):
    """
    等待 JS 执行完成并跳转到结果页
    """
    log(f"⏳ 等待答题脚本运行及跳转 (最长 {timeout_seconds}s)...")
    start_time = time.time()
    last_log_time = start_time
    js_injected = False
    
    while time.time() - start_time < timeout_seconds:
        handle_possible_alerts(driver)
        
        try:
            current_url = driver.current_url
            
            # 定期日志
            if time.time() - last_log_time > 15:
                log(f"ℹ 当前页面: {current_url.split('?')[0]}")
                last_log_time = time.time()
            
            # 1. 成功跳转至结果页
            if '/result/' in current_url:
                log(f"✅ 成功跳转至结果页")
                return True
            
            # 2. 如果在答题页，且还没注入 JS，则注入
            if 'exam_start' in current_url and not js_injected:
                # 稍微等待页面加载
                time.sleep(2)
                if inject_dati_js(driver):
                    js_injected = True
                else:
                    # 注入失败，可能需要重试或者直接退出
                    pass
            
        except UnexpectedAlertPresentException:
            handle_possible_alerts(driver)
        except Exception:
            time.sleep(1)
            
        time.sleep(2)
    
    log("⏰ 等待超时，未检测到结果页 URL")
    return False


def get_exam_score(driver):
    """获取分数"""
    log("🔍 获取分数...")
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        try:
            score_elem = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "score")))
            score = int(re.search(r'\d+', score_elem.text.strip()).group())
            log(f"📊 提取到分数: {score}")
            return score
        except: pass
        
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '分')]")
            for el in elements:
                txt = el.text
                if re.match(r'^\d+$', txt) or re.match(r'^\d+\s*分$', txt):
                     score = int(re.search(r'\d+', txt).group())
                     log(f"📊 提取到分数: {score}")
                     return score
        except: pass
    except Exception as e:
        log(f"❌ 获取分数失败: {e}")
    return None


def process_single_account(username, password, account_index, total_accounts):
    """处理单个账号"""
    result = {'account_index': account_index, 'status': '未知', 'success': False, 'score': 0, 'highest_score': 0, 'failure_reason': None}
    
    # --- 步骤 1: 提取真实考试链接 (最多重试3次) ---
    real_exam_url = None
    driver = None
    
    try:
        log(f"🌐 启动浏览器 (账号 {account_index})...")
        driver = create_chrome_driver() # 修正：这里不再传递参数
        
        # 登录流程
        driver.get("https://passport.jlc.com")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        if not perform_init_session(driver): raise Exception("初始化 Session 失败")
        captcha_ticket = call_aliv3min_with_timeout()
        if not captcha_ticket: raise Exception("获取 CaptchaTicket 失败")
        status, login_res = login_with_password(driver, username, password, captcha_ticket)
        if status == 'password_error':
            result['status'] = '密码错误'; result['failure_reason'] = '账号或密码不正确'; driver.quit(); return result
        if status != 'success': raise Exception("登录失败")
        if not verify_login_on_member_page(driver): raise Exception("登录验证失败")
        
        # 提取链接
        for extract_attempt in range(3):
            real_exam_url = extract_real_exam_url(driver)
            if real_exam_url:
                break
            log(f"⚠ 提取链接失败，重试 ({extract_attempt+1}/3)...")
            time.sleep(2)
            
        if not real_exam_url:
            log("❌ 3次尝试均无法提取考试链接，跳过该账号")
            result['failure_reason'] = "无法提取考试链接"
            driver.quit()
            return result
            
    except Exception as e:
        log(f"❌ 准备阶段异常: {e}")
        if driver: driver.quit()
        return result

    # --- 步骤 2: 答题流程 (复用已提取的链接，最多重试3次) ---
    for exam_retry in range(3):
        try:
            log(f"📝 开始答题流程 ({exam_retry+1}/3)...")
            
            # 直接跳转到真实考试页面
            driver.get(real_exam_url)
            
            # 点击开始按钮
            if not click_start_exam_button(driver):
                log("❌ 找不到开始按钮，刷新重试")
                continue
                
            # 注入 JS 并等待结果
            if not wait_for_exam_completion_with_js(driver):
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
                    result['success'] = True; result['status'] = '答题成功'; driver.quit(); return result
                else:
                    log(f"😢 分数未达标: {score}")
                    result['failure_reason'] = f"最高得分{result['highest_score']}"
            else:
                log("⚠ 未能获取到分数")
                
        except Exception as e:
            log(f"❌ 答题过程异常: {e}")
            
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
    if len(usernames) != len(passwords): log("❌ 账号密码数量不匹配"); sys.exit(1)
    
    all_results = []
    for i, (u, p) in enumerate(zip(usernames, passwords), 1):
        log(f"\n{'='*40}\n正在处理账号 {i}\n{'='*40}")
        res = process_single_account(u, p, i, len(usernames))
        all_results.append(res)
        if i < len(usernames): time.sleep(5)
        
    log("\n" + "="*40); log("📊 最终结果总结"); log("="*40)
    has_failure = False
    for res in all_results:
        if res['success']: log(f"账号{res['account_index']}: 立创题库答题成功✅ 分数:{res['score']}")
        else: has_failure = True; log(f"账号{res['account_index']}: 立创题库答题失败❌ 原因:{res['failure_reason']}")
    if fail_exit and has_failure: sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
