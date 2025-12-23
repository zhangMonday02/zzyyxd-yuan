import requests
import execjs
import time
import uuid
import json
import os
import base64
import random
import string

# ================= Configuration =================
GLOBAL_PUBLIC_KEY = "043b2759c70dab4718520cad55ac41eea6f8922c1309afb788f7578b3e585b167811023effefc2b9193cd93ae9c9a2a864e5fffbf7517c679f40cbf4c4630aa28c"

# Credentials to encrypt
USERNAME = "13800138000"
PASSWORD = "YourPassword123"

# ================= Setup JS Environment =================

def ensure_dependencies():
    """Ensures crypto-js exists. Downloads if missing."""
    if not os.path.exists("crypto-js.min.js"):
        print("[-] Downloading crypto-js.min.js...")
        try:
            url = "https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                with open("crypto-js.min.js", "w", encoding="utf-8") as f:
                    f.write(resp.text)
            else:
                print(f"[!] Failed to download crypto-js: {resp.status_code}")
                exit(1)
        except Exception as e:
            print(f"[!] Network error downloading crypto-js: {e}")
            exit(1)

def get_js_ctx():
    ensure_dependencies()
    
    with open("crypto-js.min.js", "r", encoding="utf-8") as f:
        crypto_js = f.read()
    
    with open("sm2 (2).js", "r", encoding="utf-8") as f:
        sm2_js = f.read()
    
    # Polyfill browser objects for SM2/CryptoJS
    shim = """
        var window = this;
        var navigator = {
            appName: 'Netscape',
            appVersion: '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        };
        var document = { createElement: function() { return { getContext: function() {} } } };
    """
    
    return execjs.compile(shim + "\n" + crypto_js + "\n" + sm2_js)

def sm2_encrypt(ctx, data):
    """Encrypts string using SM2 (C1C3C2 mode). JS handles Base64 encoding internally."""
    return ctx.call('sm2Encrypt', data, GLOBAL_PUBLIC_KEY, 1)

def generate_client_info():
    """Generates a complete client info blob to avoid server 500 errors."""
    info = {
        "clientType": "PC-WEB",
        "osName": "Windows",
        "osVersion": "10",
        "browserName": "Chrome",
        "browserVersion": "120.0.0.0",
        "browserEngine": "Blink",
        "browserEngineVersion": "120.0.0.0",
        "screenWidth": 1920,
        "screenHeight": 1080,
        "dpr": 1,
        "colorDepth": 24,
        "pixelDepth": 24,
        "gpuVendor": "Google Inc. (NVIDIA)",
        "gpuRenderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "cpuArchitecture": "amd64",
        "hardwareConcurrency": 16,
        "deviceVendor": None,
        "deviceType": None,
        "language": "zh-CN",
        "timeZone": "Asia/Shanghai",
        "timezoneOffset": -480,
        "netType": "4g"
    }
    json_str = json.dumps(info, separators=(',', ':'))
    return base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

def main():
    ctx = get_js_ctx()
    session = requests.Session()
    
    # 1. Generate Fingerprints
    # X-JLC-ClientUuid: UUID-Timestamp
    client_uuid = f"{uuid.uuid4()}-{int(time.time() * 1000)}"
    # Visitor ID: 32 char hex string
    visitor_id = ''.join(random.choices(string.hexdigits.lower(), k=32))
    # JSec-X-Df: SM2 Encrypted Visitor ID
    jsec_x_df = sm2_encrypt(ctx, visitor_id)
    # X-JLC-ClientInfo: Base64 JSON
    client_info = generate_client_info()

    # 2. Setup Headers
    headers = {
        'Host': 'passport.jlc.com',
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/plain, */*',
        'X-JLC-ClientUuid': client_uuid,
        'X-JLC-ClientInfo': client_info,
        'JSec-X-Df': jsec_x_df,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://passport.jlc.com',
        'Referer': 'https://passport.jlc.com/login',
    }

    # 3. Handshake (Get Secret Key)
    print("[-] Performing handshake (secret/update)...")
    try:
        url = 'https://passport.jlc.com/api/cas-auth/secret/update'
        # The 500 error was likely due to missing fields in ClientInfo
        resp = session.post(url, headers=headers, json={}, timeout=10)
        
        if resp.status_code != 200:
            print(f"[!] Handshake failed: {resp.status_code}")
            print(f"Response: {resp.text}")
            return

        data = resp.json()
        if data.get('code') != 200:
            print(f"[!] API Error: {data.get('message')}")
            return

        secret_key = data['data']['keyId']
        print(f"[+] Handshake success. SecretKey: {secret_key}")

    except Exception as e:
        print(f"[!] Request Exception: {e}")
        return

    # 4. Encrypt Credentials
    print("[-] Encrypting credentials...")
    enc_username = sm2_encrypt(ctx, USERNAME)
    enc_password = sm2_encrypt(ctx, PASSWORD)

    # 5. Construct Login Payload
    final_headers = headers.copy()
    final_headers['secretkey'] = secret_key
    
    payload = {
        "username": enc_username,
        "password": enc_password,
        "isAutoLogin": False,
        "appId": "JLC_PORTAL_PC"
    }

    # 6. Output
    print("\n" + "="*20 + " GENERATED LOGIN REQUEST " + "="*20)
    print(f"URL: https://passport.jlc.com/api/cas/login/with-password")
    print("\n[Cookies]")
    print(json.dumps(session.cookies.get_dict(), indent=4))
    
    print("\n[Headers]")
    print(json.dumps(final_headers, indent=4))
    
    print("\n[Body]")
    print(json.dumps(payload, indent=4))

if __name__ == '__main__':
    main()
