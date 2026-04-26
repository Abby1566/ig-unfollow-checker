import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from instagrapi import Client

app = Flask(__name__)

# --- 設定區 ---
# 請確保這是你剛剛測試成功的公網 IP 與 Port
HOME_PROXY = "http://1.164.104.46:5269"
DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- 工具函數 ---

def get_snapshot_path(username):
    return os.path.join(DATA_DIR, f"{username}_snapshot.json")

def save_snapshot(username, followers, following):
    """存檔快照"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "followers": followers,
        "following": following,
        "followers_count": len(followers),
        "following_count": len(following)
    }
    with open(get_snapshot_path(username), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_snapshot(username):
    """讀取上次的快照"""
    path = get_snapshot_path(username)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# --- 核心邏輯 ---

def check_instagram(username, password):
    cl = Client()
    
    # 1. 啟用你家樹莓派的住宅代理，這是抗封鎖的神盾
    print(f"[*] 啟動安全機制：連線至住宅代理 {HOME_PROXY}")
    cl.set_proxy(HOME_PROXY)
    
    # 2. 模擬真實用戶行為的延遲 (2~5秒)
    cl.delay_range = [2, 5]

    try:
        print(f"[*] 嘗試登入帳號: @{username}")
        cl.login(username, password)
        
        user_id = cl.user_id_from_username(username)
        
        print("[*] 正在抓取粉絲名單...")
        followers_dict = cl.user_followers(user_id)
        followers = [u.username for u in followers_dict.values()]
        
        print("[*] 正在抓取追蹤中名單...")
        following_dict = cl.user_following(user_id)
        following = [u.username for u in following_dict.values()]
        
        return followers, following, None
    except Exception as e:
        print(f"[!] 錯誤: {str(e)}")
        return None, None, str(e)

# --- Flask 路由 ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def api_check():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"success": False, "message": "請輸入帳號密碼"})

    # 執行掃描
    new_followers, new_following, error = check_instagram(username, password)
    
    if error:
        return jsonify({"success": False, "message": f"登入失敗: {error}"})

    # 讀取舊快照進行比對
    old_data = load_snapshot(username)
    
    unfollowers = []
    new_fans = []
    
    if old_data:
        # 比對邏輯：舊有但新名單沒有 = 退追了
        old_followers = set(old_data['followers'])
        curr_followers = set(new_followers)
        
        unfollowers = list(old_followers - curr_followers)
        new_fans = list(curr_followers - old_followers)

    # 存下本次掃描作為下次的快照
    save_snapshot(username, new_followers, new_following)

    return jsonify({
        "success": True,
        "stats": {
            "followers_count": len(new_followers),
            "following_count": len(new_following),
            "unfollowers_count": len(unfollowers),
            "new_fans_count": len(new_fans)
        },
        "unfollowers": unfollowers,
        "new_fans": new_fans,
        "message": "掃描完成！已更新快照資料。"
    })

if __name__ == '__main__':
    # 這裡 port 改成 8080，方便你內網測試
    app.run(host='0.0.0.0', port=8080, debug=True)
