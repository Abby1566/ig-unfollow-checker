from flask import Flask, render_template, request, jsonify
from instagrapi import Client
import os
import requests

app = Flask(__name__)

# --- 配置區 ---
# 1. 這裡填入你剛剛在 Termius 畫面上看到的 ngrok 網址
# 注意：結尾不要有斜線 /
HOME_PROXY = "https://simmering-motion-borrowing.ngrok-free.dev"

# 2. Instagram 帳號密碼（建議用環境變數，或是先直接填入測試）
IG_USERNAME = os.environ.get("IG_USERNAME", "你的帳號")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "你的密碼")

def check_current_ip():
    """測試代理是否生效，並回傳目前輸出的 IP"""
    test_url = "https://ifconfig.me/ip"
    proxies = {
        "http": HOME_PROXY,
        "https": HOME_PROXY
    }
    try:
        # 測試透過 ngrok 隧道去抓 IP
        response = requests.get(test_url, proxies=proxies, timeout=10)
        return response.text.strip()
    except Exception as e:
        return f"代理連線失敗: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan():
    cl = Client()
    
    # --- 關鍵步驟：設定住宅代理 ---
    print(f"正在測試代理網址: {HOME_PROXY}")
    out_ip = check_current_ip()
    print(f"目前代理輸出 IP 為: {out_ip}")
    
    try:
        # 將流量導入你家裡的樹莓派
        cl.set_proxy(HOME_PROXY)
        
        # 執行登入
        print("嘗試登入 Instagram...")
        cl.login(IG_USERNAME, IG_PASSWORD)
        
        # 登入成功後的邏輯 (範例：抓取自己的資訊)
        user_info = cl.user_info(cl.user_id)
        return jsonify({
            "status": "success", 
            "message": f"成功以 IP {out_ip} 登入！",
            "user": user_info.full_name
        })
        
    except Exception as e:
        print(f"登入失敗: {e}")
        return jsonify({
            "status": "error", 
            "message": f"登入失敗，目前 IP: {out_ip}。錯誤原因: {str(e)}"
        })

if __name__ == '__main__':
    # Render 部署需要監聽 0.0.0.0
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
