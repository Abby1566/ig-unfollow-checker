import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, BadPassword

app = Flask(__name__)

# --- 核心設定 (請確保 IP 是你目前 curl -4 ifconfig.me 看到的數字) ---
HOME_PROXY = "https://simmering-motion-borrowing.ngrok-free.dev"
DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def check_instagram(username, password, verification_code=None):
    cl = Client()
    # 縮短延遲範圍，避免超過 Render 的 30 秒大限
    cl.delay_range = [1, 2] 
    # 設定連線超時，避免無限卡死
    cl.request_timeout = 15 
    
    try:
        # 掛載新竹住宅代理
        #cl.set_proxy(HOME_PROXY)
        
        if verification_code:
            print(f"[*] 使用驗證碼登入: @{username}")
            cl.login(username, password, verification_code=verification_code)
        else:
            print(f"[*] 嘗試登入: @{username}")
            cl.login(username, password)
        
        # 抓取資料
        user_id = cl.user_id_from_username(username)
        followers = [u.username for u in cl.user_followers(user_id).values()]
        following = [u.username for u in cl.user_following(user_id).values()]
        
        return {"status": "success", "followers": followers, "following": following}

    except TwoFactorRequired:
        return {"status": "2fa_required"}
    except Exception as e:
        error_msg = str(e).lower()
        if "proxy" in error_msg or "tunnel" in error_msg:
            return {"status": "error", "message": "代理連線失敗，請檢查樹莓派與路由器。"}
        if "bad_password" in error_msg:
            return {"status": "error", "message": "密碼錯誤，請重新檢查。"}
        return {"status": "error", "message": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def api_check():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    code = data.get('verification_code')

    if not username or not password:
        return jsonify({"success": False, "message": "請輸入帳密"})

    result = check_instagram(username, password, code)

    if result["status"] == "2fa_required":
        return jsonify({"success": False, "need_2fa": True})
    
    if result["status"] == "error":
        return jsonify({"success": False, "message": result["message"]})

    # 回傳結果
    return jsonify({
        "success": True,
        "stats": {
            "followers_count": len(result["followers"]),
            "following_count": len(result["following"])
        },
        "message": "掃描完成！"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
