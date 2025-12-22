import requests
import json
import time
import uuid
import execjs
import os

# ================= 配置区域 =================
# 全局固定公钥 (用于加密 jsec-x-df)
GLOBAL_PUBLIC_KEY = "043b2759c70dab4718520cad55ac41eea6f8922c1309afb788f7578b3e585b167811023effefc2b9193cd93ae9c9a2a864e5fffbf7517c679f40cbf4c4630aa28c"

# 静态 Cookies (来自你的请求，保持不变的部分)
STATIC_COOKIES = {
    'device_id': 'c7d0a5f4b554477fae0e1ba29f84fb63',
    'HWWAFSESID': 'bcd7d8b4f625fb57ac',
    'HWWAFSESTIME': '1766299533105',
    'Qs_lvt_290854': '1766237893%2C1766299553',
    'Qs_pv_290854': '2499244294467079700%2C852781256760664000',
    '__sameSiteCheck__': '1',
    '_c_WBKFRo': '03ctatXDH7wXL1GIRpFWI9AUfuGhSVMzyOf5q8oX',
    '_nb_ioWEgULi': '',
    # 注意：QS_lvt, Hm_lvt 等统计类 cookie 通常不影响登录逻辑，这里直接沿用
    'Hm_lvt_bdc175618582350273cc82e8dd494d69': '1754417092,1756655417,1756820063,1756824557',
}

# 基础 Headers
BASE_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'cache-control': 'no-cache, no-store, must-revalidate',
    'content-type': 'application/json',
    'origin': 'https://passport.jlc.com',
    'referer': 'https://passport.jlc.com/window/login?appId=JLC_PORTAL_PC&redirectUrl=https%3A%2F%2Fwww.jlc.com%2F',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
    'sec-ch-ua': '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
}

# ================= 核心逻辑 =================

def load_js_context():
    """加载并编译 JS 环境，补充浏览器环境缺失的变量"""
    js_path = 'sm2.js'
    if not os.path.exists(js_path):
        raise FileNotFoundError(f"请确保 {js_path} 文件在当前目录下")
        
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    # 注入环境垫片，防止 JS 报错
    preamble = """
    var window = this;
    var navigator = { appName: 'Netscape', appVersion: '5.0', userAgent: 'Mozilla/5.0' };
    var document = { 
        createElement: function() { return { getContext: function() {} } },
        head: { appendChild: function() {} },
        getElementsByTagName: function() { return [{ appendChild: function() {} }] }
    };
    """
    return execjs.compile(preamble + js_content)

def get_dynamic_secret():
    """
    步骤 1: 调用 /secret/update 接口获取 keyId (即 secretkey)
    同时获取最新的 JSESSIONID
    """
    url = "https://passport.jlc.com/api/cas-auth/secret/update"
    
    # 该接口只需要基础 cookie 即可
    try:
        response = requests.post(url, json={}, headers=BASE_HEADERS, cookies=STATIC_COOKIES)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') != 200:
            raise Exception(f"获取密钥失败: {data}")
            
        # 获取 keyId (Header 中的 secretkey)
        key_id = data['data']['keyId']
        
        # 获取新返回的 Cookie (主要是 JSESSIONID)
        new_cookies = response.cookies.get_dict()
        
        return key_id, new_cookies
        
    except Exception as e:
        print(f"[-] 请求握手接口失败: {e}")
        exit(1)

def generate_client_uuid():
    """生成符合格式的 UUID"""
    # 格式: uuid-timestamp
    ts = int(time.time() * 1000)
    uid = str(uuid.uuid4())
    return f"{uid}-{ts}"

def calc_jsec_x_df(js_ctx, client_uuid):
    """
    步骤 2: 使用 SM2 加密 client_uuid 生成 jsec-x-df
    对应 JS: sm2Encrypt(data, publickey, cipherMode)
    """
    # cipherMode 1 为 C1C3C2 模式
    try:
        encrypted = js_ctx.call('sm2Encrypt', client_uuid, GLOBAL_PUBLIC_KEY, 1)
        return encrypted
    except Exception as e:
        print(f"[-] JS 加密失败: {e}")
        exit(1)

def main():
    print("[*] 正在初始化环境...")
    js_ctx = load_js_context()
    
    print("[*] 正在与服务器握手获取 SecretKey...")
    secret_key, session_cookies = get_dynamic_secret()
    
    print("[*] 正在计算 jsec-x-df 签名...")
    client_uuid = generate_client_uuid()
    jsec_val = calc_jsec_x_df(js_ctx, client_uuid)
    
    # 合并 Cookies
    final_cookies = STATIC_COOKIES.copy()
    final_cookies.update(session_cookies) # 更新 JSESSIONID 等动态 cookie
    
    # 构造 Headers
    final_headers = BASE_HEADERS.copy()
    final_headers['secretkey'] = secret_key
    final_headers['jsec-x-df'] = jsec_val
    final_headers['x-jlc-clientuuid'] = client_uuid
    
    # Base64 编码的 client info (固定值即可，含义是 PC-WEB)
    final_headers['x-jlc-clientinfo'] = 'eyJjbGllbnRUeXBlIjoiUEMtV0VCIn0='

    # ================= 输出结果 =================
    print("\n" + "="*20 + " 生成结果 " + "="*20)
    
    # 格式化输出 Cookies
    print("        cookies = {")
    for k, v in final_cookies.items():
        print(f"            '{k}': '{v}',")
    print("        }")
    
    print("")
    
    # 格式化输出 Headers
    print("        headers = {")
    for k, v in final_headers.items():
        print(f"            '{k}': '{v}',")
    print("        }")

if __name__ == "__main__":
    main()
