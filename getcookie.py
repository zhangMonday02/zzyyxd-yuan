import json
import time
import uuid
import sys
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

# ================= 配置区域 =================
MAIN_URL = "https://www.jlc.com"
PASSPORT_URL = "https://passport.jlc.com/window/login?appId=JLC_PORTAL_PC&redirectUrl=https%3A%2F%2Fwww.jlc.com%2F"

def log(msg):
    """日志输出到 stderr，不干扰 stdout"""
    sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()

def init_driver():
    """初始化浏览器"""
    log("正在启动 Chrome 浏览器 (无头模式)...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=zh-CN")
    
    # 模拟真实 UA
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 防检测
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """
    })
    return driver

def get_waf_cookies_strict(driver):
    """
    严格按照要求获取 WAF Cookie:
    1. 访问 jlc.com
    2. 检查 HWWAFSESID 和 HWWAFSESTIME
    3. 有则删除并刷新，无则刷新重试
    """
    log(f"1. 访问主页获取 WAF: {MAIN_URL}")
    driver.get(MAIN_URL)
    time.sleep(3)

    waf_keys = ['HWWAFSESID', 'HWWAFSESTIME']
    
    def get_cookies_dict():
        return {c['name']: c['value'] for c in driver.get_cookies()}

    cookies = get_cookies_dict()
    has_waf = all(k in cookies for k in waf_keys)

    if has_waf:
        log("   [状态] 检测到旧的 WAF Cookie")
        log("   [操作] 手动删除并刷新页面...")
        driver.delete_cookie('HWWAFSESID')
        driver.delete_cookie('HWWAFSESTIME')
        time.sleep(1)
        driver.refresh()
        log("   [等待] 等待 Set-Cookie 生效 (3s)...")
        time.sleep(3)
    else:
        log("   [状态] 未检测到 WAF Cookie")
        log("   [操作] 尝试刷新页面 (Max 3次)...")
        for i in range(3):
            driver.refresh()
            time.sleep(3)
            cookies = get_cookies_dict()
            if all(k in cookies for k in waf_keys):
                log(f"   [成功] 第 {i+1} 次刷新获取到了 Cookie")
                break
            else:
                log(f"   [重试] 第 {i+1} 次刷新未获取到...")

    final_cookies = get_cookies_dict()
    # 提取 WAF
    waf_result = {k: final_cookies.get(k) for k in waf_keys if final_cookies.get(k)}
    
    if len(waf_result) == 2:
        log(f"   [结果] WAF Cookie 获取成功: {waf_result}")
    else:
        log("   [警告] WAF Cookie 获取不完整，可能会导致 500 错误")
    
    return final_cookies

def fetch_dynamic_public_key(driver):
    """
    在浏览器内执行 fetch 获取公钥
    """
    log("3. 动态获取 SM2 公钥 (API: /config/get-public-key)...")
    
    # 注入异步脚本获取公钥
    fetch_script = """
    var callback = arguments[arguments.length - 1];
    fetch('https://passport.jlc.com/api/cas/config/get-public-key')
        .then(response => response.json())
        .then(data => {
            if (data.code === 200) {
                callback(data.data);
            } else {
                callback(null);
            }
        })
        .catch(error => callback(null));
    """
    
    try:
        public_key = driver.execute_async_script(fetch_script)
        if public_key:
            log(f"   [成功] 获取到公钥: {public_key[:15]}...")
            return public_key
        else:
            log("   [失败] 接口返回错误")
            return None
    except Exception as e:
        log(f"   [异常] 获取公钥脚本执行失败: {e}")
        return None

def generate_client_info(driver):
    """
    根据当前浏览器环境动态生成 x-jlc-clientinfo Base64
    """
    log("4. 动态生成 x-jlc-clientinfo...")
    js_script = """
    var info = {
        "clientType": "PC-WEB",
        "osName": "Windows", 
        "osVersion": "10",
        "browserName": "Chrome",
        "browserVersion": navigator.appVersion.match(/Chrome\/([\d.]+)/)[1],
        "browserEngine": "Blink",
        "screenWidth": window.screen.width,
        "screenHeight": window.screen.height,
        "dpr": window.devicePixelRatio,
        "colorDepth": window.screen.colorDepth,
        "netType": "4g",
        "language": navigator.language,
        "timeZone": Intl.DateTimeFormat().resolvedOptions().timeZone
    };
    return btoa(JSON.stringify(info));
    """
    try:
        info = driver.execute_script(js_script)
        return info
    except:
        # Fallback if script fails
        return "eyJjbGllbnRUeXBlIjoiUEMtV0VCIn0="

def get_passport_data(driver):
    """
    获取 SecretKey 并计算签名
    """
    log(f"2. 跳转 Passport 页面: {PASSPORT_URL}")
    driver.get(PASSPORT_URL)
    
    # 增加等待，确保握手完成
    time.sleep(5)
    
    # 1. 动态获取公钥
    public_key = fetch_dynamic_public_key(driver)
    if not public_key:
        # 如果动态获取失败，使用备用（虽然你要求动态，但为了程序健壮性）
        log("   [警告] 使用默认公钥")
        public_key = "043b2759c70dab4718520cad55ac41eea6f8922c1309afb788f7578b3e585b167811023effefc2b9193cd93ae9c9a2a864e5fffbf7517c679f40cbf4c4630aa28c"

    # 2. 获取 SecretKey
    secret_key = ""
    try:
        key_pair_str = driver.execute_script("return localStorage.getItem('keyPair');")
        if key_pair_str:
            key_pair = json.loads(key_pair_str)
            secret_key = key_pair.get('keyId', '')
            log(f"   [成功] 获取 SecretKey: {secret_key}")
        else:
            log("   [失败] LocalStorage 中无 keyPair")
    except Exception as e:
        log(f"   [异常] 获取 SecretKey: {e}")

    # 3. 计算签名
    timestamp = int(time.time() * 1000)
    client_uuid = f"{uuid.uuid4()}-{timestamp}"
    log(f"   [生成] ClientUUID: {client_uuid}")

    jsec_val = ""
    try:
        # 确保 SM2Utils 加载
        driver.execute_script("if(typeof window.SM2Utils === 'undefined') { window.SM2Utils = {}; }")
        
        # 调用页面函数
        js_code = f"return window.SM2Utils.encs('{public_key}', '{client_uuid}', 1);"
        jsec_val = driver.execute_script(js_code)
        
        if jsec_val:
            log("   [成功] 生成 jsec-x-df 签名")
        else:
            log("   [失败] 签名生成为空")
    except Exception as e:
        log(f"   [异常] 签名计算: {e}")

    return secret_key, client_uuid, jsec_val

def main():
    driver = init_driver()
    try:
        # 1. WAF Cookies
        cookies_map = get_waf_cookies_strict(driver)
        
        # 2. Passport Params
        secret_key, client_uuid, jsec_val = get_passport_data(driver)
        
        if not secret_key or not jsec_val:
            log("无法获取必要参数，退出")
            return

        # 3. 整理 Cookies (合并 WAF 和 Passport 的 Session)
        # 重新获取一次当前页面的 Cookie，确保 JSESSIONID 是最新的
        current_cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        cookies_map.update(current_cookies)
        
        # 补充一些前端生成的统计 Cookie (模拟)
        ts = int(time.time())
        if 'Qs_lvt_290854' not in cookies_map:
            cookies_map['Qs_lvt_290854'] = f"{ts-5000}%2C{ts}"
        if 'Qs_pv_290854' not in cookies_map:
            cookies_map['Qs_pv_290854'] = f"{random.randint(1000000000000000000, 9999999999999999999)}"
        if '__sameSiteCheck__' not in cookies_map:
            cookies_map['__sameSiteCheck__'] = '1'
        if '_c_WBKFRo' not in cookies_map:
            cookies_map['_c_WBKFRo'] = '03ctatXDH7wXL1GIRpFWI9AUfuGhSVMzyOf5q8oX' # 固定指纹
        
        # 4. 整理 Headers
        user_agent = driver.execute_script("return navigator.userAgent;")
        client_info = generate_client_info(driver)
        
        headers_map = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'cache-control': 'no-cache, no-store, must-revalidate',
            'content-type': 'application/json',
            'expires': '0',
            'jsec-x-df': jsec_val,
            'origin': 'https://passport.jlc.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': PASSPORT_URL,
            'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'secretkey': secret_key,
            'support-cookie-samesite': 'true',
            'user-agent': user_agent,
            'x-jlc-clientinfo': client_info,
            'x-jlc-clientuuid': client_uuid,
        }

        # 5. 输出
        
        # Cookies 输出
        print("cookies = {")
        # 确保关键 Cookie 存在
        cookie_keys = ['device_id', 'HWWAFSESID', 'HWWAFSESTIME', 'Qs_lvt_290854', 'Qs_pv_290854', '__sameSiteCheck__', '_c_WBKFRo', '_nb_ioWEgULi', 'JSESSIONID', 'lsId']
        for k in cookie_keys:
            val = cookies_map.get(k, '')
            # 补全 device_id
            if k == 'device_id' and not val: val = uuid.uuid4().hex
            print(f"    '{k}': '{val}',")
        print("}")
        print("")

        # Headers 输出
        print("headers = {")
        # 按照你要求的顺序排序
        header_keys_order = [
            'accept', 'accept-language', 'cache-control', 'content-type', 'expires', 
            'jsec-x-df', 'origin', 'pragma', 'priority', 'referer', 'sec-ch-ua', 
            'sec-ch-ua-mobile', 'sec-ch-ua-platform', 'sec-fetch-dest', 'sec-fetch-mode', 
            'sec-fetch-site', 'secretkey', 'support-cookie-samesite', 'user-agent', 
            'x-jlc-clientinfo', 'x-jlc-clientuuid'
        ]
        
        for k in header_keys_order:
            val = headers_map.get(k, '')
            print(f"    '{k}': '{val}',")
        print("}")

    except Exception as e:
        log(f"Critical Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
