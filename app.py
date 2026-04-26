import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, BadPassword, ProxyError

app = Flask(__name__)

# --- 核心設定 (請確保這組 IP 跟你的截圖一致) ---
HOME_PROXY = "http://1.164.104.46:5269"
DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def check_instagram(username, password, verification_code=None):
    cl = Client()
    # 修正之前的語法錯誤：使用屬性賦值而非函數呼叫
    cl.delay_range = [1, 3] 
    # 設定超時，避免 Render 30 秒硬限制
    cl.request_timeout = 15 
    
    try:
        # 掛載你家新竹的住宅代理
        cl.set_proxy(HOME_PROXY)
        
        if verification_code:
            print(f"[*] 嘗試驗證碼登入: @{username}")
            cl.login(username, password, verification_code=verification_code)
        else:
            print(f"[*] 嘗試普通登入: @{username}")
            cl.login(username, password)
        
        # 登入成功，抓取名單
        user_id = cl.user_id_from_username(username)
        followers = [u.username for u in cl.user_followers(user_id).values()]
        following = [u.username for u in cl.user_following(user_id).values()]
        
        return {"status": "success", "followers": followers, "following": following}

    except TwoFactorRequired:
        return {"status": "2fa_required"}
    except ProxyError:
        return {"status": "error", "message": "代理連線失敗，請檢查家裡樹莓派與路由器。"}
    except Exception as e:
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

    result = check_instagram(username, password, code)

    if result["status"] == "2fa_required":
        return jsonify({"success": False, "need_2fa": True})
    
    if result["status"] == "error":
        return jsonify({"success": False, "message": result["message"]})

    # 比對邏輯 (簡單化處理)
    # 這裡可以加入你之前的 snapshot 邏輯，但為了穩定先回傳基本數據
    return jsonify({
        "success": True,
        "stats": {
            "followers_count": len(result["followers"]),
            "following_count": len(result["following"])
        },
        "message": "掃描成功！"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
