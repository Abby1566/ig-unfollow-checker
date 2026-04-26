import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, BadPassword, LoginRequired

app = Flask(__name__)

# --- 設定區 ---
HOME_PROXY = "http://1.164.104.46:5269"
DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- 核心登入邏輯 ---
def check_instagram(username, password, verification_code=None):
    cl = Client()
    # 啟動住宅代理，繞過地區限制
    cl.set_proxy(HOME_PROXY)
    # 設定行為隨機延遲，防止被 IG 偵測為機器人
    cl.delay_range = [1, 3]

    try:
        if verification_code:
            print(f"[*] 嘗試使用驗證碼登入: @{username}")
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
    except BadPassword:
        return {"status": "error", "message": "密碼錯誤，請重新檢查。"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 快照功能 ---
def handle_snapshots(username, new_followers, new_following):
    path = os.path.join(DATA_DIR, f"{username}_snapshot.json")
    unfollowers = []
    new_fans = []

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            old_data = json.load(f)
            old_f = set(old_data['followers'])
            curr_f = set(new_followers)
            unfollowers = list(old_f - curr_f)
            new_fans = list(curr_f - old_f)

    # 存入新快照
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "followers": new_followers,
            "following": new_following
        }, f, ensure_ascii=False)
    
    return unfollowers, new_fans

# --- 路由 ---
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
        return jsonify({"success": False, "message": "請輸入帳號密碼"})

    result = check_instagram(username, password, code)

    if result["status"] == "2fa_required":
        return jsonify({"success": False, "need_2fa": True, "message": "請輸入雙重驗證碼"})
    
    if result["status"] == "error":
        return jsonify({"success": False, "message": result["message"]})

    # 處理名單比對
    unfollowers, new_fans = handle_snapshots(username, result["followers"], result["following"])

    return jsonify({
        "success": True,
        "stats": {
            "followers_count": len(result["followers"]),
            "following_count": len(result["following"]),
            "unfollowers_count": len(unfollowers),
            "new_fans_count": len(new_fans)
        },
        "unfollowers": unfollowers,
        "new_fans": new_fans
    })

if __name__ == '__main__':
    # Render 會自動指定 PORT，我們監聽 0.0.0.0
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
