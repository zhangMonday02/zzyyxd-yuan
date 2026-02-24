import os
import sys
import time
import json
import tempfile
import subprocess
import re
import shutil
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 导入 SM2 加密依赖
try:
    from Utils import pwdEncrypt
    print("✅ 成功加载 SM2 加密依赖")
except ImportError:
    print("❌ 错误: 未找到 Utils.py，请确保同目录下存在该文件")
    sys.exit(1)

# 尝试导入 serverchan3
try:
    from serverchan_sdk import sc_send
    HAS_SERVERCHAN3 = True
except ImportError:
    HAS_SERVERCHAN3 = False

# ======================== 全局变量 ========================
in_summary = False
summary_logs = []


def log(msg, show_time=True):
    """带时间戳的日志输出"""
    if show_time:
        full_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    else:
        full_msg = msg
    print(full_msg, flush=True)
    if in_summary:
        summary_logs.append(msg)


# ======================== 浏览器 ========================
def create_chrome_driver(user_data_dir=None):
    """创建 Chrome 浏览器实例（启用性能日志以抓取 secretkey）"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    if user_data_dir:
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"},
    )
    return driver


# ======================== 登录相关========================
def call_aliv3min_with_timeout(timeout_seconds=180, max_retries=18):
    """调用 AliV3min.py 获取 captchaTicket"""
    for attempt in range(max_retries):
        log(f"📞 正在调用登录脚本获取 captchaTicket (尝试 {attempt + 1}/{max_retries})...")
        process = None
        try:
            if not os.path.exists("AliV3min.py"):
                log("❌ 错误: 找不到登录依赖 AliV3min.py")
                sys.exit(1)

            process = subprocess.Popen(
                [sys.executable, "AliV3min.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )

            start_time = time.time()
            while True:
                if time.time() - start_time > timeout_seconds:
                    log(f"⏰ 登录脚本超过 {timeout_seconds} 秒未完成，强制终止...")
                    try:
                        process.kill()
                        process.wait(timeout=5)
                    except Exception:
                        pass
                    break

                try:
                    line = process.stdout.readline()
                    if line:
                        if "SUCCESS: Obtained CaptchaTicket:" in line:
                            next_line = process.stdout.readline()
                            if next_line:
                                captcha_ticket = next_line.strip()
                                log("✅ 成功获取 captchaTicket")
                                try:
                                    process.terminate()
                                    process.wait(timeout=5)
                                except Exception:
                                    pass
                                return captcha_ticket

                        if "captchaTicket" in line:
                            match = re.search(r'"captchaTicket"\s*:\s*"([^"]+)"', line)
                            if match:
                                log("✅ 成功获取 captchaTicket")
                                try:
                                    process.terminate()
                                    process.wait(timeout=5)
                                except Exception:
                                    pass
                                return match.group(1)

                    if process.poll() is not None:
                        break
                except Exception:
                    time.sleep(0.1)

            if process and process.poll() is None:
                try:
                    process.kill()
                    process.wait(timeout=5)
                except Exception:
                    pass

            if attempt < max_retries - 1:
                log(f"⚠ 未获取到 CaptchaTicket，等待5秒后第 {attempt + 2} 次重试...")
                time.sleep(5)

        except Exception as e:
            log(f"❌ 调用登录脚本异常: {e}")
            if process and process.poll() is None:
                try:
                    process.kill()
                    process.wait(timeout=5)
                except Exception:
                    pass
            if attempt < max_retries - 1:
                log(f"⚠ 等待5秒后第 {attempt + 2} 次重试...")
                time.sleep(5)

    log("❌ 登录脚本存在异常，无法获取 CaptchaTicket")
    return None


def send_login_request(driver, url, method="POST", body=None):
    """通过浏览器发送登录相关请求"""
    try:
        if body:
            body_str = json.dumps(body, ensure_ascii=False)
            js_code = """
            var url=arguments[0],bodyData=arguments[1],cb=arguments[2];
            fetch(url,{method:'POST',headers:{'Content-Type':'application/json',
            'Accept':'application/json, text/plain, */*','AppId':'JLC_PORTAL_PC',
            'ClientType':'PC-WEB'},body:bodyData,credentials:'include'})
            .then(r=>r.json().then(d=>cb(JSON.stringify(d))))
            .catch(e=>cb(JSON.stringify({error:e.toString()})));
            """
            result = driver.execute_async_script(js_code, url, body_str)
        else:
            js_code = """
            var url=arguments[0],cb=arguments[1];
            fetch(url,{method:'GET',headers:{'Content-Type':'application/json',
            'Accept':'application/json, text/plain, */*'},credentials:'include'})
            .then(r=>r.json().then(d=>cb(JSON.stringify(d))))
            .catch(e=>cb(JSON.stringify({error:e.toString()})));
            """
            result = driver.execute_async_script(js_code, url)
        return json.loads(result) if result else None
    except Exception as e:
        log(f"❌ 登录请求执行失败: {e}")
        return None


def perform_init_session(driver, max_retries=3):
    """初始化 Session"""
    for i in range(max_retries):
        log(f"📡 初始化会话 (尝试 {i + 1}/{max_retries})...")
        resp = send_login_request(
            driver,
            "https://passport.jlc.com/api/cas/login/get-init-session",
            "POST",
            {"appId": "JLC_PORTAL_PC", "clientType": "PC-WEB"},
        )
        if resp and resp.get("success") and resp.get("code") == 200:
            log("✅ 初始化会话成功")
            return True
        log(f"⚠ 初始化会话失败，接口返回: {resp}")
        if i < max_retries - 1:
            time.sleep(2)
    return False


def login_with_password(driver, username, password, captcha_ticket):
    """使用密码登录"""
    try:
        enc_user = pwdEncrypt(username)
        enc_pass = pwdEncrypt(password)
    except Exception as e:
        log(f"❌ SM2 加密失败: {e}")
        return "other_error", None

    body = {
        "username": enc_user,
        "password": enc_pass,
        "isAutoLogin": False,
        "captchaTicket": captcha_ticket,
    }
    log("📡 发送登录请求...")
    resp = send_login_request(
        driver, "https://passport.jlc.com/api/cas/login/with-password", "POST", body
    )
    if not resp:
        return "other_error", None

    if resp.get("success") and resp.get("code") == 2017:
        return "success", resp
    if resp.get("code") == 10208:
        log(f"❌ 账号或密码不正确，接口返回: {resp}")
        return "password_error", resp

    log(f"⚠ 登录返回未知状态，接口返回: {resp}")
    return "other_error", resp


def verify_login_on_member_page(driver, max_retries=3):
    """在 member.jlc.com 验证登录状态"""
    for attempt in range(max_retries):
        log(f"🔍 验证登录状态 ({attempt + 1}/{max_retries})...")
        try:
            try:
                driver.get("https://member.jlc.com/")
            except TimeoutException:
                log("⚠ 验证页面加载超时，停止加载并尝试检查...")
                driver.execute_script("window.stop();")

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)
            page_source = driver.page_source
            if "客编" in page_source or "customerCode" in page_source:
                log("✅ 验证登录成功")
                return True
        except Exception as e:
            log(f"⚠ 验证登录失败: {e}")
        if attempt < max_retries - 1:
            time.sleep(2)
    return False


def perform_login_flow(driver, username, password, max_retries=3):
    """完整登录流程"""
    session_fail_count = 0
    for login_attempt in range(max_retries):
        log(f"🔐 开始登录流程 (尝试 {login_attempt + 1}/{max_retries})...")
        try:
            try:
                driver.get("https://passport.jlc.com")
            except TimeoutException:
                log("⚠ 登录页面加载超时，尝试停止加载继续...")
                driver.execute_script("window.stop();")

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            if not perform_init_session(driver):
                session_fail_count += 1
                if session_fail_count >= 3:
                    log("❌ 浏览器环境存在异常")
                raise Exception("初始化 Session 失败")

            session_fail_count = 0

            captcha_ticket = call_aliv3min_with_timeout()
            if not captcha_ticket:
                raise Exception("获取 CaptchaTicket 失败")

            status, resp = login_with_password(driver, username, password, captcha_ticket)
            if status == "password_error":
                return "password_error"
            if status != "success":
                raise Exception(f"登录失败，状态: {status}")

            if not verify_login_on_member_page(driver):
                raise Exception("登录验证失败")

            log("✅ 登录流程完成")
            return "success"

        except Exception as e:
            log(f"❌ 登录流程异常: {e}")
            if login_attempt < max_retries - 1:
                log("⏳ 等待3秒后重试登录流程...")
                time.sleep(3)
            else:
                log("❌ 登录流程已达最大重试次数")
                return "login_failed"
    return "login_failed"


# ======================== BBS 功能函数 ========================
def extract_secretkey(driver, max_retries=5):
    """从浏览器性能日志中提取 secretkey"""
    for attempt in range(max_retries):
        try:
            logs = driver.get_log("performance")
            for entry in logs:
                try:
                    message = json.loads(entry["message"])
                    msg_method = message.get("message", {}).get("method", "")

                    headers = {}
                    if msg_method == "Network.requestWillBeSent":
                        req = message["message"]["params"]["request"]
                        url = req.get("url", "")
                        if "jlc-bbs.com" in url:
                            headers = req.get("headers", {})
                    elif msg_method == "Network.responseReceived":
                        resp = message["message"]["params"]["response"]
                        url = resp.get("url", "")
                        if "jlc-bbs.com" in url:
                            headers = resp.get("requestHeaders", {})

                    if headers:
                        sk = (
                            headers.get("secretkey")
                            or headers.get("SecretKey")
                            or headers.get("secretKey")
                            or headers.get("SECRETKEY")
                        )
                        if sk:
                            log(f"✅ 成功提取 secretkey: {sk[:20]}...")
                            return sk
                except Exception:
                    continue
        except Exception as e:
            log(f"⚠ 提取 secretkey 异常: {e}")

        if attempt < max_retries - 1:
            log(f"⚠ 未提取到 secretkey，等待3秒后重试 ({attempt + 1}/{max_retries})...")
            time.sleep(3)
            try:
                driver.refresh()
                time.sleep(5)
            except Exception:
                pass
    return None


def send_bbs_request(driver, url, method="POST", body=None, secretkey="", max_retries=3):
    """通过浏览器发送 BBS API 请求（自动携带 cookie）"""
    for attempt in range(max_retries):
        try:
            if method.upper() == "POST":
                if body is not None:
                    body_str = json.dumps(body, ensure_ascii=False)
                    js_code = """
                    var url=arguments[0],bodyData=arguments[1],sk=arguments[2],cb=arguments[3];
                    fetch(url,{method:'POST',headers:{'Content-Type':'application/json','secretkey':sk},
                    body:bodyData,credentials:'include'})
                    .then(function(r){return r.text();})
                    .then(function(d){cb(d);})
                    .catch(function(e){cb(JSON.stringify({error:e.toString()}));});
                    """
                    result = driver.execute_async_script(js_code, url, body_str, secretkey)
                else:
                    js_code = """
                    var url=arguments[0],sk=arguments[1],cb=arguments[2];
                    fetch(url,{method:'POST',headers:{'Content-Type':'application/json','secretkey':sk},
                    credentials:'include'})
                    .then(function(r){return r.text();})
                    .then(function(d){cb(d);})
                    .catch(function(e){cb(JSON.stringify({error:e.toString()}));});
                    """
                    result = driver.execute_async_script(js_code, url, secretkey)
            else:  # GET
                js_code = """
                var url=arguments[0],sk=arguments[1],cb=arguments[2];
                fetch(url,{method:'GET',headers:{'secretkey':sk},credentials:'include'})
                .then(function(r){return r.text();})
                .then(function(d){cb(d);})
                .catch(function(e){cb(JSON.stringify({error:e.toString()}));});
                """
                result = driver.execute_async_script(js_code, url, secretkey)

            if result:
                try:
                    parsed = json.loads(result)
                    return parsed
                except json.JSONDecodeError:
                    log(f"⚠ 接口返回非JSON，原文: {result[:500]}")
            else:
                log("⚠ 接口返回空内容")

        except Exception as e:
            log(f"⚠ 请求执行失败 (尝试 {attempt + 1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            time.sleep(2)

    return None


def get_sign_info(driver, secretkey, label="", max_retries=3):
    """获取签到信息（含当前积分）"""
    for attempt in range(max_retries):
        resp = send_bbs_request(
            driver,
            "https://www.jlc-bbs.com/api/bbs/signInRecordWeb/getSignInfo",
            "POST", None, secretkey, max_retries=1,
        )
        if resp:
            if resp.get("success") and resp.get("code") == 200:
                data = resp.get("data", {})
                total_score = data.get("totalScore", 0)
                sign_days = data.get("signInDays", 0)
                continue_days = data.get("signInContinueDays", 0)
                if label:
                    log(f"📊 {label}积分: {total_score} (累计签到{sign_days}天, 连续{continue_days}天)")
                return {"success": True, "totalScore": total_score, "data": data}
            else:
                log(f"⚠ 获取积分信息失败，接口返回: {resp}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"success": False, "error": resp.get("message", "未知错误"), "raw": resp}
        else:
            if attempt < max_retries - 1:
                log(f"⚠ 获取积分信息请求失败，重试中 ({attempt + 1}/{max_retries})...")
                time.sleep(2)

    return {"success": False, "error": "请求失败"}


def do_sign_in(driver, secretkey, max_retries=3):
    """执行签到"""
    for attempt in range(max_retries):
        resp = send_bbs_request(
            driver,
            "https://www.jlc-bbs.com/api/bbs/signInRecordWeb/signIn",
            "POST",
            {"signInContent": "", "signInExpression": ""},
            secretkey, max_retries=1,
        )
        if resp:
            if resp.get("success") and resp.get("code") == 200:
                task_score = resp.get("data", {}).get("taskScore", 0)
                return {"status": "success", "taskScore": task_score}
            elif resp.get("message") and "已经签到" in resp.get("message", ""):
                return {"status": "already_signed", "message": resp.get("message")}
            else:
                log(f"⚠ 签到失败，接口返回: {resp}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"status": "failed", "error": resp.get("message", "未知原因"), "raw": resp}
        else:
            if attempt < max_retries - 1:
                log(f"⚠ 签到请求失败，重试中 ({attempt + 1}/{max_retries})...")
                time.sleep(2)

    return {"status": "failed", "error": "请求失败"}


def get_remaining_lottery_times(driver, max_retries=3):
    """从前端页面提取剩余抽奖次数"""
    for attempt in range(max_retries):
        try:
            page_source = driver.page_source
            match = re.search(r"今日可抽奖次数：\s*</span>\s*(\d+)\s*次", page_source)
            if match:
                times = int(match.group(1))
                log(f"🎰 剩余抽奖次数: {times}")
                return {"success": True, "times": times}
            match2 = re.search(r"今日可抽奖次数[：:]\s*(\d+)\s*次", page_source)
            if match2:
                times = int(match2.group(1))
                log(f"🎰 剩余抽奖次数: {times}")
                return {"success": True, "times": times}
            text = driver.find_element(By.TAG_NAME, "body").text
            match3 = re.search(r"今日可抽奖次数[：:]\s*(\d+)\s*次", text)
            if match3:
                times = int(match3.group(1))
                log(f"🎰 剩余抽奖次数: {times}")
                return {"success": True, "times": times}
        except Exception as e:
            log(f"⚠ 获取抽奖次数异常: {e}")

        if attempt < max_retries - 1:
            log(f"⚠ 未能获取抽奖次数，等待3秒后重试 ({attempt + 1}/{max_retries})...")
            time.sleep(3)
            try:
                driver.refresh()
                time.sleep(5)
            except Exception:
                pass

    log("⚠ 无法从页面获取剩余抽奖次数")
    return {"success": False, "error": "无法从页面提取抽奖次数"}


def do_lottery(driver, secretkey):
    """执行单次抽奖"""
    resp = send_bbs_request(
        driver,
        "https://www.jlc-bbs.com/api/bbs/luckyDrawActivityRecord/executeLuckDraw",
        "POST",
        {"luckyDrawActivityAccessId": "ab69ff00332949328ba578c086d42141"},
        secretkey, max_retries=2,
    )
    if resp:
        if resp.get("success") and resp.get("code") == 200:
            name = resp.get("data", {}).get("name", "未知奖品")
            return {"status": "success", "name": name, "data": resp.get("data", {})}
        elif resp.get("message") and "次数" in resp.get("message", ""):
            return {"status": "no_times", "message": resp.get("message")}
        elif resp.get("message") and "积分" in resp.get("message", ""):
            return {"status": "no_points", "message": resp.get("message")}
        else:
            log(f"⚠ 抽奖返回异常，接口返回: {resp}")
            return {"status": "failed", "error": resp.get("message", "未知错误"), "raw": resp}
    return {"status": "failed", "error": "请求失败"}


def get_koi_cards(driver, secretkey, max_retries=3):
    """获取锦鲤卡数量"""
    for attempt in range(max_retries):
        timestamp = int(time.time() * 1000)
        url = f"https://www.jlc-bbs.com/api/bbs/prizeOrder/getPrizeCard?_t={timestamp}"
        resp = send_bbs_request(driver, url, "GET", None, secretkey, max_retries=1)
        if resp:
            if resp.get("success") and resp.get("code") == 200:
                count = resp.get("data", 0)
                return {"success": True, "count": count}
            else:
                log(f"⚠ 获取锦鲤卡失败，接口返回: {resp}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"success": False, "error": resp.get("message", "未知错误"), "raw": resp}
        else:
            if attempt < max_retries - 1:
                log(f"⚠ 获取锦鲤卡请求失败，重试中 ({attempt + 1}/{max_retries})...")
                time.sleep(2)

    return {"success": False, "error": "请求失败"}


# ======================== BBS 业务流程（登录后的所有操作） ========================
def execute_bbs_flow(driver, account_index, result):
    """
    执行 BBS 签到、抽奖、锦鲤卡检查的完整业务流程。
    此函数在登录验证成功后调用，使用同一个 driver 实例。
    """
    # ============ 签到阶段 ============
    log("📄 打开签到页面...")
    try:
        driver.get("https://www.jlc-bbs.com/platform/sign")
    except TimeoutException:
        log("⚠ 签到页面加载超时，停止加载继续...")
        driver.execute_script("window.stop();")

    log("⏳ 等待10秒让页面完全加载...")
    time.sleep(10)

    # 提取 secretkey
    secretkey = extract_secretkey(driver)
    if not secretkey:
        log("❌ 无法提取 secretkey，此账号流程异常")
        result["has_error"] = True
        result["error_msg"] = "secretkey 提取失败"
        return

    # 1. 获取签到前积分
    log("📡 获取签到前积分...")
    info_before = get_sign_info(driver, secretkey, label="签到前")
    if info_before.get("success"):
        result["sign_before_points"] = info_before["totalScore"]
    else:
        log(f"⚠ 获取签到前积分失败: {info_before.get('error', '未知')}")

    # 2. 执行签到
    log("📡 执行签到...")
    sign_result = do_sign_in(driver, secretkey)
    result["sign_status"] = sign_result["status"]

    if sign_result["status"] == "success":
        result["sign_points_gained"] = sign_result["taskScore"]
        log(f"✅ 签到成功，获得 {sign_result['taskScore']} 积分")
    elif sign_result["status"] == "already_signed":
        log(f"ℹ {sign_result.get('message', '今天已经签到过了')}")
    else:
        result["sign_error_msg"] = sign_result.get("error", "未知原因")
        result["has_error"] = True
        log(f"❌ 签到失败: {result['sign_error_msg']}")

    # 3. 获取签到后积分
    log("📡 获取签到后积分...")
    info_after = get_sign_info(driver, secretkey, label="签到后")
    if info_after.get("success"):
        result["sign_after_points"] = info_after["totalScore"]
    else:
        log(f"⚠ 获取签到后积分失败: {info_after.get('error', '未知')}")

    # ============ 抽奖阶段 ============
    log("📄 打开抽奖页面...")
    try:
        driver.get(
            "https://www.jlc-bbs.com/platform/points-paradise"
            "?type=index&id=ab69ff00332949328ba578c086d42141"
        )
    except TimeoutException:
        log("⚠ 抽奖页面加载超时，停止加载继续...")
        driver.execute_script("window.stop();")

    log("⏳ 等待10秒让页面完全加载...")
    time.sleep(10)

    # 刷新 secretkey（性能日志可能被清理，如提取不到就复用之前的）
    new_sk = extract_secretkey(driver)
    if new_sk:
        secretkey = new_sk

    # 检查当前积分
    log("📡 检查当前积分...")
    points_info = get_sign_info(driver, secretkey, label="当前")
    current_points = 0
    if points_info.get("success"):
        current_points = points_info["totalScore"]
        result["lottery_before_points"] = current_points
    else:
        log(f"⚠ 获取当前积分失败: {points_info.get('error', '未知')}")
        if result["sign_after_points"] is not None:
            current_points = result["sign_after_points"]
            result["lottery_before_points"] = current_points
            log(f"ℹ 使用签到后积分作为参考: {current_points}")

    # 检查剩余抽奖次数
    times_info = get_remaining_lottery_times(driver)
    remaining_times = 0
    if times_info.get("success"):
        remaining_times = times_info["times"]
    else:
        log(f"⚠ 获取抽奖次数失败: {times_info.get('error', '未知')}")

    # 判断是否抽奖
    if remaining_times == 0:
        result["lottery_status"] = "skipped"
        result["lottery_skip_reason"] = "抽奖次数为0"
        log("ℹ 抽奖次数为0，跳过抽奖")
    elif current_points < 10:
        result["lottery_status"] = "skipped"
        result["lottery_skip_reason"] = f"积分不足10（当前{current_points}）"
        log(f"ℹ 积分不足10（当前{current_points}），跳过抽奖")
    else:
        # 执行抽奖循环
        log("🎰 开始抽奖...")
        result["lottery_status"] = "success"
        lottery_count = 0

        while True:
            lottery_result = do_lottery(driver, secretkey)

            if lottery_result["status"] == "success":
                lottery_count += 1
                prize_name = lottery_result["name"]
                result["lottery_prizes"].append(prize_name)
                log(f"🎉 抽奖{lottery_count}: {prize_name}")
                time.sleep(1)
            elif lottery_result["status"] == "no_times":
                log(f"ℹ {lottery_result.get('message', '抽奖次数已用完')}")
                break
            elif lottery_result["status"] == "no_points":
                log(f"ℹ {lottery_result.get('message', '积分不足')}")
                break
            else:
                result["lottery_error_msg"] = lottery_result.get("error", "未知原因")
                result["has_error"] = True
                log(f"❌ 抽奖失败: {result['lottery_error_msg']}")
                break

        if lottery_count > 0:
            log(f"🎰 共完成 {lottery_count} 次抽奖")

    # 获取抽奖后积分
    log("📡 获取最终积分...")
    final_info = get_sign_info(driver, secretkey, label="最终")
    if final_info.get("success"):
        result["final_points"] = final_info["totalScore"]
        result["lottery_after_points"] = final_info["totalScore"]
    else:
        result["final_points_error"] = final_info.get("error", "未知")
        log(f"⚠ 获取最终积分失败: {result['final_points_error']}")
        if result["sign_after_points"] is not None and not result["lottery_prizes"]:
            result["final_points"] = result["sign_after_points"]

    # ============ 锦鲤卡 ============
    log("📡 检查锦鲤卡数量...")
    koi_result = get_koi_cards(driver, secretkey)
    if koi_result.get("success"):
        result["koi_cards"] = koi_result["count"]
        log(f"🐟 锦鲤卡数量: {result['koi_cards']}")
    else:
        result["koi_cards_error"] = koi_result.get("error", "未知")
        log(f"⚠ 获取锦鲤卡数量失败: {result['koi_cards_error']}")


# ======================== 单账号处理（带密码表和断点记忆） ========================
def process_single_account(username, password, account_index, total_accounts):
    """处理单个账号 - 支持多密码重试和断点记忆"""
    backup_passwords = [
        "Aa123123",
        "Zz123123",
        "Qq123123",
        "Ss123123",
        "Xx123123",
        "Yuanxd20031024",
        "jjl1775774A",
        "qeowowe5472",
        "Wyf349817236",
        "Bb123123"
    ]

    # 构建密码候选列表（去重并保持顺序，优先尝试传入的密码）
    all_passwords = [password]
    for bp in backup_passwords:
        if bp != password:
            all_passwords.append(bp)

    result = {
        "account_index": account_index,
        "password_error": False,
        "all_passwords_failed": False,
        "login_error": False,
        "has_error": False,
        "error_msg": None,
        # 签到
        "sign_before_points": None,
        "sign_after_points": None,
        "sign_status": None,
        "sign_points_gained": None,
        "sign_error_msg": None,
        # 抽奖
        "lottery_before_points": None,
        "lottery_after_points": None,
        "lottery_status": None,
        "lottery_skip_reason": None,
        "lottery_prizes": [],
        "lottery_error_msg": None,
        # 最终
        "final_points": None,
        "final_points_error": None,
        # 锦鲤卡
        "koi_cards": None,
        "koi_cards_error": None,
    }

    current_pwd_idx = 0
    max_session_retries = 3  # 全流程重试最大次数（针对非密码错误的异常）

    # 外层循环：处理非密码错误导致的全流程重试
    for session_attempt in range(max_session_retries):

        # 内层循环：遍历密码列表
        while current_pwd_idx < len(all_passwords):
            current_password = all_passwords[current_pwd_idx]

            if current_pwd_idx == 0:
                log(f"🌐 启动浏览器 (账号 {account_index} - 使用传入密码)...")
            else:
                log(f"🌐 启动浏览器 (账号 {account_index} - 尝试备用密码 {current_pwd_idx}/{len(all_passwords) - 1})...")

            user_data_dir = tempfile.mkdtemp()
            driver = None

            try:
                driver = create_chrome_driver(user_data_dir)

                # --- 阶段 1: 登录流程 ---
                login_status = perform_login_flow(driver, username, current_password, max_retries=3)

                if login_status == "password_error":
                    log(f"❌ 密码错误: {current_password}，尝试下一个备用密码...")
                    current_pwd_idx += 1
                    driver.quit()
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                    continue  # 立即进入下一次内层循环尝试新密码

                if login_status != "success":
                    # 登录失败但不是明确的密码错误（如网络问题、验证码问题等）
                    # 跳出内层循环，进入外层重试，记忆密码进度
                    log(f"⚠ 登录流程异常 (非密码错误)，准备重新开始全流程...")
                    driver.quit()
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                    break

                # --- 阶段 2: BBS 业务流程 ---
                log(f"✅ 账号 {account_index} 登录成功，开始执行BBS业务流程...")
                execute_bbs_flow(driver, account_index, result)

                log(f"✅ 账号 {account_index} 处理完成")
                driver.quit()
                shutil.rmtree(user_data_dir, ignore_errors=True)
                return result

            except Exception as e:
                log(f"❌ 账号 {account_index} 处理过程中发生异常: {e}")
                result["has_error"] = True
                result["error_msg"] = str(e)
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                if os.path.exists(user_data_dir):
                    try:
                        shutil.rmtree(user_data_dir, ignore_errors=True)
                    except Exception:
                        pass
                # 发生未捕获异常，视为非密码错误，跳出内层循环进行全流程重试
                break

        # 检查是否因为所有密码都试完了才退出内层循环
        if current_pwd_idx >= len(all_passwords):
            log("❌ 所有候选密码均提示错误，放弃该账号")
            result["all_passwords_failed"] = True
            result["password_error"] = True
            result["has_error"] = True
            result["error_msg"] = "所有候选密码均验证失败"
            return result

        # 如果还在外层循环中，说明是触发了全流程重试
        if session_attempt < max_session_retries - 1:
            log(f"⏳ 等待5秒后进行第 {session_attempt + 2} 次全流程重试 (从密码 {current_pwd_idx + 1} 继续)...")
            time.sleep(5)

    # 外层循环结束，说明多次重试均失败（非密码错误）
    result["login_error"] = True
    result["has_error"] = True
    result["error_msg"] = "多次尝试登录均失败(非密码错误)"
    return result


# ======================== 推送相关========================
def push_summary(push_text):
    """推送总结日志到各平台"""
    if not push_text:
        return

    title = "嘉立创BBS签到&抽奖总结"
    full_text = f"{title}\n{push_text}"

    # Telegram
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            resp = requests.get(url, params={"chat_id": tg_chat, "text": full_text}, timeout=15)
            if resp.status_code == 200 and resp.json().get("ok"):
                log("Telegram-日志已推送")
            else:
                log(f"Telegram-推送失败，返回原文: {resp.text}")
        except Exception as e:
            log(f"Telegram-推送异常: {e}")

    # 企业微信
    wechat_key = os.getenv("WECHAT_WEBHOOK_KEY")
    if wechat_key:
        try:
            wechat_url = wechat_key if wechat_key.startswith("https://") else f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={wechat_key}"
            resp = requests.post(wechat_url, json={"msgtype": "text", "text": {"content": full_text}}, timeout=15)
            if resp.status_code == 200:
                log("企业微信-日志已推送")
            else:
                log(f"企业微信-推送失败，返回原文: {resp.text}")
        except Exception as e:
            log(f"企业微信-推送异常: {e}")

    # 钉钉
    dingtalk = os.getenv("DINGTALK_WEBHOOK")
    if dingtalk:
        try:
            dd_url = dingtalk if dingtalk.startswith("https://") else f"https://oapi.dingtalk.com/robot/send?access_token={dingtalk}"
            resp = requests.post(dd_url, json={"msgtype": "text", "text": {"content": full_text}}, timeout=15)
            if resp.status_code == 200:
                log("钉钉-日志已推送")
            else:
                log(f"钉钉-推送失败，返回原文: {resp.text}")
        except Exception as e:
            log(f"钉钉-推送异常: {e}")

    # PushPlus
    pp_token = os.getenv("PUSHPLUS_TOKEN")
    if pp_token:
        try:
            resp = requests.post("http://www.pushplus.plus/send", json={"token": pp_token, "title": title, "content": push_text}, timeout=15)
            if resp.status_code == 200:
                log("PushPlus-日志已推送")
            else:
                log(f"PushPlus-推送失败，返回原文: {resp.text}")
        except Exception as e:
            log(f"PushPlus-推送异常: {e}")

    # Server酱
    sc_key = os.getenv("SERVERCHAN_SCKEY")
    if sc_key:
        try:
            resp = requests.post(f"https://sctapi.ftqq.com/{sc_key}.send", data={"title": title, "desp": push_text}, timeout=15)
            if resp.status_code == 200:
                log("Server酱-日志已推送")
            else:
                log(f"Server酱-推送失败，返回原文: {resp.text}")
        except Exception as e:
            log(f"Server酱-推送异常: {e}")

    # Server酱3
    sc3_key = os.getenv("SERVERCHAN3_SCKEY")
    if sc3_key and HAS_SERVERCHAN3:
        try:
            resp = sc_send(sc3_key, title, push_text, {"tags": "嘉立创|BBS签到"})
            if resp.get("code") == 0:
                log("Server酱3-日志已推送")
            else:
                log(f"Server酱3-推送失败，返回原文: {resp}")
        except Exception as e:
            log(f"Server酱3-推送异常: {e}")

    # 酷推
    cp_skey = os.getenv("COOLPUSH_SKEY")
    if cp_skey:
        try:
            resp = requests.get(f"https://push.xuthus.cc/send/{cp_skey}", params={"c": full_text}, timeout=15)
            if resp.status_code == 200:
                log("酷推-日志已推送")
            else:
                log(f"酷推-推送失败，返回原文: {resp.text}")
        except Exception as e:
            log(f"酷推-推送异常: {e}")

    # 自定义 API
    custom = os.getenv("CUSTOM_WEBHOOK")
    if custom:
        try:
            resp = requests.post(custom, json={"title": title, "content": push_text}, timeout=15)
            if resp.status_code == 200:
                log("自定义API-日志已推送")
            else:
                log(f"自定义API-推送失败，返回原文: {resp.text}")
        except Exception as e:
            log(f"自定义API-推送异常: {e}")


def has_any_push_config():
    """检查是否配置了任何推送渠道"""
    keys = [
        "TELEGRAM_BOT_TOKEN", "WECHAT_WEBHOOK_KEY", "DINGTALK_WEBHOOK",
        "PUSHPLUS_TOKEN", "SERVERCHAN_SCKEY", "SERVERCHAN3_SCKEY",
        "COOLPUSH_SKEY", "CUSTOM_WEBHOOK",
    ]
    return any(os.getenv(k) for k in keys)


# ======================== 主函数 ========================
def main():
    global in_summary

    if len(sys.argv) < 3:
        print("用法: python bbs_sign.py 账号1,账号2... 密码1,密码2... [失败退出标志]")
        print("示例: python bbs_sign.py user1,user2 pwd1,pwd2")
        print("示例: python bbs_sign.py user1,user2 pwd1,pwd2 true")
        sys.exit(1)

    usernames = [u.strip() for u in sys.argv[1].split(",") if u.strip()]
    passwords = [p.strip() for p in sys.argv[2].split(",") if p.strip()]

    fail_exit = False
    if len(sys.argv) >= 4:
        fail_exit = sys.argv[3].lower() == "true"

    if len(usernames) != len(passwords):
        log("❌ 错误: 账号和密码数量不匹配!")
        sys.exit(1)

    total = len(usernames)
    log(f"检测到 {total} 个账号需要处理，失败退出功能已{'开启' if fail_exit else '关闭'}", show_time=False)

    all_results = []

    for i, (username, password) in enumerate(zip(usernames, passwords), 1):
        log(f"\n{'='*50}", show_time=False)
        log(f"开始处理账号 {i}/{total}", show_time=False)
        log(f"{'='*50}", show_time=False)

        result = process_single_account(username, password, i, total)
        all_results.append(result)

        if i < total:
            log("⏳ 等待5秒后处理下一个账号...")
            time.sleep(5)

    # ======================== 总结输出 ========================
    in_summary = True

    log("", show_time=False)
    log("=" * 60, show_time=False)
    log("📊 嘉立创BBS签到 & 抽奖 结果总结", show_time=False)
    log("=" * 60, show_time=False)

    push_reasons = []
    any_error = False

    for res in all_results:
        idx = res["account_index"]
        log("--------------------------------------------------", show_time=False)
        log(f"账号{idx}:", show_time=False)

        # === 密码错误 ===
        if res.get("password_error"):
            if res.get("all_passwords_failed"):
                log("├── 状态: ❌ 所有候选密码均验证失败，已跳过", show_time=False)
            else:
                log("├── 状态: ❌ 账号或密码错误，已跳过", show_time=False)
            any_error = True
            push_reasons.append(f"账号{idx}密码错误")
            log("--------------------------------------------------", show_time=False)
            continue

        # === 登录失败 ===
        if res.get("login_error"):
            log(f"├── 状态: ❌ 登录失败 ({res.get('error_msg', '未知')})", show_time=False)
            any_error = True
            push_reasons.append(f"账号{idx}登录异常")
            log("--------------------------------------------------", show_time=False)
            continue

        # === 签到积分变化 ===
        sign_status = res.get("sign_status")
        before_p = res.get("sign_before_points")
        after_p = res.get("sign_after_points")

        if sign_status == "success":
            if before_p is not None and after_p is not None:
                diff = after_p - before_p
                sign_str = f"{before_p} → {after_p} (+{diff})"
            elif res.get("sign_points_gained") is not None:
                sign_str = f"签到成功 (+{res['sign_points_gained']})"
            else:
                sign_str = "签到成功"
        elif sign_status == "already_signed":
            sign_str = "已签到过"
        elif sign_status == "failed":
            sign_str = f"签到失败，原因: {res.get('sign_error_msg', '未知')}"
            any_error = True
            push_reasons.append(f"账号{idx}签到失败")
        elif res.get("has_error") and res.get("error_msg"):
            sign_str = f"运行异常: {res.get('error_msg')}"
            any_error = True
            push_reasons.append(f"账号{idx}运行失败")
        else:
            sign_str = "未执行"
            if res.get("has_error"):
                any_error = True
                push_reasons.append(f"账号{idx}运行失败")

        log(f"├── 签到积分变化: {sign_str}", show_time=False)

        # === 抽奖积分变化 ===
        lottery_status = res.get("lottery_status")
        lot_before = res.get("lottery_before_points")
        lot_after = res.get("lottery_after_points")

        if lottery_status == "success":
            if lot_before is not None and lot_after is not None:
                diff = lot_after - lot_before
                lottery_str = f"{lot_before} → {lot_after} ({diff})"
            else:
                lottery_str = "抽奖完成"
        elif lottery_status == "skipped":
            lottery_str = f"未抽奖，原因: {res.get('lottery_skip_reason', '未知')}"
        elif lottery_status == "failed":
            lottery_str = f"抽奖失败，原因: {res.get('lottery_error_msg', '未知')}"
            err_msg = res.get("lottery_error_msg", "")
            if "积分" not in err_msg and "次数" not in err_msg:
                any_error = True
                push_reasons.append(f"账号{idx}抽奖异常")
        else:
            lottery_str = "未执行"

        log(f"├── 抽奖积分变化: {lottery_str}", show_time=False)

        # === 最终积分 ===
        final_p = res.get("final_points")
        if final_p is not None:
            log(f"├── 最终积分: {final_p}", show_time=False)
        else:
            err = res.get("final_points_error", "未知")
            log(f"├── 最终积分: 获取失败，原因: {err}", show_time=False)

        # === 锦鲤卡 ===
        koi = res.get("koi_cards")
        if koi is not None:
            log(f"├── 锦鲤卡数量: {koi}", show_time=False)
        else:
            err = res.get("koi_cards_error", "未知")
            log(f"├── 锦鲤卡数量: 获取失败，原因: {err}", show_time=False)

        # === 抽奖奖品 ===
        for pi, prize in enumerate(res.get("lottery_prizes", []), 1):
            log(f"├── 抽奖{pi}奖品: {prize}", show_time=False)
            if "积分" not in prize:
                push_reasons.append(f"账号{idx}中奖{prize}")

        log("--------------------------------------------------", show_time=False)

    # === 补充捕获遗漏的异常账号 ===
    for res in all_results:
        idx = res["account_index"]
        if res.get("has_error") and not res.get("password_error") and not res.get("login_error"):
            reason_str = f"账号{idx}运行失败"
            if reason_str not in push_reasons and f"账号{idx}签到失败" not in push_reasons and f"账号{idx}抽奖异常" not in push_reasons:
                any_error = True
                push_reasons.append(reason_str)

    # === 推送决策 ===
    push_reasons = list(dict.fromkeys(push_reasons))
    should_push = len(push_reasons) > 0

    if should_push:
        reason_text = "/".join(push_reasons)
        log(f"本次运行推送，推送原因: {reason_text}", show_time=False)

        push_text = "\n".join(summary_logs)
        if has_any_push_config():
            push_summary(push_text)
        else:
            log("ℹ 未配置任何推送链接，跳过实际推送", show_time=False)
    else:
        log("本次运行不推送，无推送条件命中", show_time=False)

    in_summary = False

    # === 退出码 ===
    has_any_account_error = any(r.get("has_error") for r in all_results)

    if fail_exit and has_any_account_error:
        log("❌ 由于失败退出功能已开启且有账号异常，返回退出码 1")
        sys.exit(1)
    else:
        if fail_exit:
            log("✅ 所有账号执行完成，无异常，程序正常退出")
        else:
            log("✅ 程序正常退出")
        sys.exit(0)


if __name__ == "__main__":
    main()
