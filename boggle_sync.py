import json
import os
import requests
import boggle_history
import threading

CONFIG_FILE = "sync_config.json"

def get_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return None

def pull_from_gist(debug=False):
    config = get_config()
    if not config or not config.get("pat") or not config.get("gist_id"):
        if debug: print("[DEBUG] Gist Sync: Missing configuration (PAT or Gist ID). Skipping.")
        return

    gist_id = config["gist_id"]
    pat = config["pat"]
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {"Authorization": f"token {pat}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            gist_data = response.json()
            files = gist_data.get("files", {})
            sync_file = files.get("boggle_history.json")
            
            if sync_file:
                content = sync_file.get("content")
                if content:
                    cloud_data = json.loads(content)
                    cloud_games = cloud_data.get("games", [])
                    
                    if debug: print(f"[DEBUG] Gist Sync: Fetched {len(cloud_games)} games from cloud.")
                    
                    # Merge into local DB
                    count = 0
                    for game in cloud_games:
                        # save_game uses INSERT OR IGNORE based on guid UNIQUE constraint
                        boggle_history.save_game(game)
                        count += 1
                    
                    if debug: print(f"[DEBUG] Gist Sync: Sync complete ({count} records processed).")
        else:
            if debug: print(f"[DEBUG] Gist Sync: Pull failed with status {response.status_code}")
    except Exception as e:
        if debug: print(f"[DEBUG] Gist Sync: Pull error: {e}")

def push_to_gist(debug=False):
    config = get_config()
    if not config or not config.get("pat") or not config.get("gist_id"):
        return

    gist_id = config["gist_id"]
    pat = config["pat"]
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {"Authorization": f"token {pat}"}

    try:
        # Fetch all local games
        local_games = boggle_history.get_history(only_finished=False)
        
        # Prepare Gist content
        payload = {
            "files": {
                "boggle_history.json": {
                    "content": json.dumps({"games": local_games}, indent=2)
                }
            }
        }
        
        response = requests.patch(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            if debug: print(f"[DEBUG] Gist Sync: Local history pushed to cloud successfully.")
        else:
            if debug: print(f"[DEBUG] Gist Sync: Push failed with status {response.status_code}")
    except Exception as e:
        if debug: print(f"[DEBUG] Gist Sync: Push error: {e}")

def sync_pull_async(debug=False):
    threading.Thread(target=pull_from_gist, args=(debug,), daemon=True).start()

def sync_push_async(debug=False):
    threading.Thread(target=push_to_gist, args=(debug,), daemon=True).start()
