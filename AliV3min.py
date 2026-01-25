import json
import sys
import requests

proxy = None

class AliV3:
    def __init__(self):
        self.captchaTicket = None
        self.CertifyId = None
        self.author = '古月&zhangMonday'
        
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
            print('verifyParam not found')
            return

        # 使用 API 返回的数据
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
        # This is the final result we want
        print(response.text)
        
        try:
            self.captchaTicket = response.json()['data']['captchaTicket']
            print("\nSUCCESS: Obtained CaptchaTicket:")
            print(self.captchaTicket)
        except Exception as e:
            print("Failed to get captchaTicket:", e)

    def test(self):
        pass

    def main(self):
        # 使用 API 获取验证码
        if self.getCap():
            self.Sumbit_All()
        else:
            print("验证码获取失败，无法继续。")


if __name__ == '__main__':
    ali = AliV3()
    ali.main()
