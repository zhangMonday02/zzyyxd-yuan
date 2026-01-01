import sys
import os
import time
import json
import subprocess
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 尝试导入加密方法，假设 Utils.py 在同目录
try:
    from Utils import pwdEncrypt
except ImportError:
    print("错误: 无法导入 pwdEncrypt。请确保 Utils.py 在同目录下。")
    sys.exit(1)

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"[{timestamp}] {msg}")

def execute_js_request(driver, url, payload):
    """
    通过浏览器控制台(fetch)发送POST请求
    """
    js_script = """
    var url = arguments[0];
    var payload = arguments[1];
    var callback = arguments[2];

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json;charset=UTF-8',
            'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => callback(data))
    .catch(error => callback({success: false, message: "JS_FETCH_ERROR: " + error.toString()}));
    """
    try:
        # 使用 execute_async_script 等待 fetch 回调
        result = driver.execute_async_script(js_script, url, payload)
        return result
    except Exception as e:
        log(f"浏览器控制台请求执行失败: {e}")
        return None

def get_captcha_ticket():
    """
    调用 AliV3min.py 获取 captchaTicket
    """
    log("正在调用 AliV3min.py 获取验证码...")
    
    # 获取当前脚本所在的绝对路径目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # 使用 communicate() 替代 readline()，防止死锁卡顿
        # 传递 env=os.environ 确保子进程能找到 node 环境
        process = subprocess.Popen(
            [sys.executable, 'AliV3min.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # 将错误也输出到标准输出方便抓取
            text=True,
            encoding='utf-8',
            errors='ignore',
            cwd=current_dir,  # 强制工作目录
            env=os.environ    # 继承环境变量
        )
        
        # 等待进程结束并获取所有输出，设置超时时间为 180秒
        stdout_data, _ = process.communicate(timeout=180)
        
        ticket = None
        # 分析输出内容
        lines = stdout_data.split('\n')
        for line in lines:
            line = line.strip()
            # 1. 尝试解析 JSON 寻找 ticket
            if '"captchaTicket":' in line:
                try:
                    # 尝试提取 json 部分
                    start_idx = line.find('{')
                    end_idx = line.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        json_str = line[start_idx:end_idx+1]
                        data = json.loads(json_str)
                        if isinstance(data, dict):
                            # 路径可能在 data.captchaTicket 或 data.data.captchaTicket
                            if 'captchaTicket' in data:
                                ticket = data['captchaTicket']
                            elif 'data' in data and isinstance(data['data'], dict):
                                ticket = data['data'].get('captchaTicket')
                except:
                    pass
            
            # 2. 兼容 AliV3min 直接打印纯 Ticket 的情况 (32位字符)
            if not ticket and len(line) == 32 and all(c in '0123456789abcdef' for c in line):
                 ticket = line

        if ticket:
            log(f"SUCCESS: Obtained CaptchaTicket:\n{ticket}")
            return ticket
        else:
            log("AliV3min.py 未能返回有效的 captchaTicket")
            # 只有失败时才打印部分日志供调试
            print("--- AliV3min Log (Last 500 chars) ---")
            print(stdout_data[-500:])
            print("-------------------------------------")
            return None

    except subprocess.TimeoutExpired:
        process.kill()
        log("AliV3min.py 运行超时 (3分钟)，已强制结束")
        return None
    except Exception as e:
        log(f"调用 AliV3min.py 发生异常: {e}")
        return None

def process_account(account_idx, username, password, fail_exit_enabled):
    """
    单个账号的处理流程
    """
    log(f"=== 开始处理第 {account_idx} 个账号 ===")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # 新版无头模式
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 安装插件
    crx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'JLCTK.crx')
    if os.path.exists(crx_path):
        chrome_options.add_extension(crx_path)
    else:
        log(f"错误: 找不到插件文件 {crx_path}")
        return False, "插件丢失"

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_script_timeout(30)
    
    try:
        # ================= Step 1: 初始化 Session =================
        init_success = False
        for i in range(3):
            try:
                log(f"打开护照页面 (尝试 {i+1}/3)...")
                driver.get("https://passport.jlc.com")
                
                payload = {"appId":"JLC_PORTAL_PC","clientType":"PC-WEB"}
                resp = execute_js_request(driver, "https://passport.jlc.com/api/cas/login/get-init-session", payload)
                
                if resp and resp.get("success") is True and resp.get("code") == 200:
                    log("Session 初始化成功")
                    init_success = True
                    break
                else:
                    log(f"Session 初始化失败")
                    driver.refresh()
                    time.sleep(2)
            except Exception as e:
                log(f"Session 初始化异常: {e}")
                driver.quit()
                driver = webdriver.Chrome(options=chrome_options)
                driver.set_script_timeout(30)

        if not init_success:
            log("错误: 超过3次无法初始化 Session，退出程序。")
            driver.quit()
            sys.exit(1)

        # ================= Step 2: 获取 CaptchaTicket =================
        captcha_ticket = None
        for i in range(3):
            captcha_ticket = get_captcha_ticket()
            if captcha_ticket:
                break
            log(f"获取 CaptchaTicket 失败，重试 {i+1}/3...")
            time.sleep(2)
        
        if not captcha_ticket:
            log("错误: 超过3次无法获取 CaptchaTicket，退出程序。")
            driver.quit()
            sys.exit(1)

        # ================= Step 3: 登录 =================
        login_retry_max = 3
        login_success = False
        
        for login_attempt in range(login_retry_max):
            log(f"发送登录请求 (尝试 {login_attempt+1}/{login_retry_max})...")
            
            try:
                enc_user = pwdEncrypt(username)
                enc_pwd = pwdEncrypt(password)
            except Exception as e:
                log(f"加密失败: {e}")
                return False, "加密失败"

            login_payload = {
                'username': enc_user,
                'password': enc_pwd,
                'isAutoLogin': False,
                'captchaTicket': captcha_ticket
            }
            
            resp = execute_js_request(driver, "https://passport.jlc.com/api/cas/login/with-password", login_payload)
            
            if resp:
                if resp.get("success") is True and resp.get("code") == 2017:
                    log("登录接口返回成功")
                    login_success = True
                    break
                elif resp.get("code") == 10208:
                    log("登录失败: 账号或密码不正确")
                    return False, "账号或密码不正确" 
                else:
                    log(f"登录接口返回其他代码: {resp.get('code')}")
            else:
                log("登录请求无响应")
            
            time.sleep(2)

        if not login_success:
            return False, "登录接口多次失败"

        # ================= Step 4: 验证登录 (客编) =================
        verify_success = False
        for verify_attempt in range(3):
            try:
                log("正在打开 member.jlc.com 验证登录...")
                driver.get("https://member.jlc.com/")
                
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(5) 
                
                page_source = driver.page_source
                if "客编" in page_source:
                    log("验证成功: 页面包含'客编'")
                    verify_success = True
                    break
                else:
                    log("验证失败: 页面未找到'客编'")
            except Exception as e:
                log(f"验证登录过程异常: {e}")
            
            log(f"验证重试 {verify_attempt+1}/3...")
            driver.refresh()
        
        if not verify_success:
            return False, "无法验证登录状态(找不到客编)"

        # ================= Step 5: 考试流程 =================
        exam_url = "https://member.jlc.com/integrated/exam-center/intermediary?examinationRelationUrl=https%3A%2F%2Fexam.kaoshixing.com%2Fexam%2Fbefore_answer_notice%2F1647581&examinationRelationId=1647581"
        
        final_score = 0
        
        for exam_retry in range(3):
            log(f"=== 开始答题流程 (尝试 {exam_retry+1}/3) ===")
            try:
                driver.get(exam_url)
                
                btn_found = False
                for refresh_i in range(3):
                    try:
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.ID, "startExamBtn"))
                        )
                        btn = driver.find_element(By.ID, "startExamBtn")
                        log("找到开始答题按钮，点击...")
                        driver.execute_script("arguments[0].click();", btn)
                        btn_found = True
                        break
                    except Exception:
                        log(f"未找到开始按钮，尝试刷新...")
                        if refresh_i < 2:
                            driver.refresh()
                            time.sleep(3)
                
                if not btn_found:
                    log("多次刷新仍未找到开始按钮，跳过本次重试")
                    continue 

                log("点击成功，等待组卷及插件运行(限时3分钟)...")
                
                exam_start_time = time.time()
                score_found = False
                
                while time.time() - exam_start_time < 180: 
                    try:
                        if len(driver.find_elements(By.CSS_SELECTOR, "span.score")) > 0:
                            score_elem = driver.find_element(By.CSS_SELECTOR, "span.score")
                            score_text = score_elem.text.strip()
                            if score_text.isdigit():
                                final_score = int(score_text)
                                log(f"检测到分数: {final_score}")
                                score_found = True
                                break
                    except:
                        pass
                    time.sleep(1)
                
                if score_found:
                    if final_score >= 60:
                        return True, f"分数:{final_score}"
                    else:
                        log(f"分数 {final_score} 低于 60，需要重试")
                else:
                    log("答题超时 (3分钟未检测到分数)")
            
            except Exception as e:
                log(f"答题流程发生异常: {e}")
            
        return False, f"最高得分{final_score}/脚本超时或失败"

    except Exception as e:
        log(f"账号流程发生未捕获异常: {e}")
        return False, f"异常: {str(e)}"
    finally:
        driver.quit()

def main():
    if len(sys.argv) < 3:
        print("用法: python jlc.py 账号1,账号2... 密码1,密码2... [失败退出标志]")
        print("示例: python jlc.py user1,user2 pwd1,pwd2")
        print("示例: python jlc.py user1,user2 pwd1,pwd2 true")
        sys.exit(0)

    users_str = sys.argv[1]
    pwds_str = sys.argv[2]
    
    fail_exit_flag = False
    if len(sys.argv) >= 4:
        if sys.argv[3].lower() == 'true':
            fail_exit_flag = True
    
    users = users_str.split(',')
    pwds = pwds_str.split(',')
    
    if len(users) != len(pwds):
        print("错误: 账号和密码数量不匹配")
        sys.exit(1)
    
    results = []
    
    print(f"失败退出标志: {'开启' if fail_exit_flag else '关闭'}")
    
    for i in range(len(users)):
        user = users[i].strip()
        pwd = pwds[i].strip()
        if not user: continue
        
        # 传递 i+1 作为序号，不传递真实账号
        success, msg = process_account(i+1, user, pwd, fail_exit_flag)
        results.append({
            "index": i+1,
            "success": success,
            "msg": msg
        })
        
        if i < len(users) - 1:
            time.sleep(2)

    print("\n" + "="*30)
    print("所有账号运行结束，结果汇总:")
    
    all_success = True
    pass_count = 0
    
    for res in results:
        status = "立创题库答题成功✅" if res['success'] else "立创题库答题失败❌"
        # 结果汇总也只显示序号
        print(f"账号{res['index']}")
        if res['success']:
            print(f"{status} {res['msg']}")
            pass_count += 1
        else:
            print(f"{status} 原因:{res['msg']}")
            all_success = False
        print("-" * 20)

    pass_rate = (pass_count / len(results)) * 100 if results else 0
    print(f"总计: {len(results)}, 通过: {pass_count}, 通过率: {pass_rate:.2f}%")
    
    if fail_exit_flag:
        if not all_success:
            print("触发失败退出标志，返回退出码 1")
            sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
