import requests
import machine
import time
import config

def check():
    url = f"https://raw.githubusercontent.com/{config.GITHUB_USER}/{config.GITHUB_REPO}/{config.GITHUB_BRANCH}/main.py"
    headers = {"Authorization": f"token {config.GITHUB_TOKEN}", "User-Agent": "ESP32-S3"}

    try:
        res = requests.get(f"{url}?t={time.time()}", headers=headers)
        
        if res.status_code == 200:
            remote_code = res.text
            
            # Đọc code cũ trong mạch
            local_code = ""
            try:
                with open("main.py", "r") as f:
                    local_code = f.read()
            except OSError:
                pass 
            
            # So sánh nội dung
            if remote_code != local_code and len(remote_code) > 10:
                print("-> [OTA] CO VERSION MOI! Dang ghi de...")
                with open("main.py", "w") as f:
                    f.write(remote_code)
                    
                print("-> [OTA] Update Completed! Rebooting...")
                time.sleep(1)
                machine.reset() 
            else:
                print("-> [OTA] The current version is the latest version.")
        else:
            print(f"-> [OTA] GitHub Error (HTTP {res.status_code})")
        res.close()
    except Exception as e:
        print("-> [OTA] Loi mang:", e)