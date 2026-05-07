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
    
    filename = "boggle_history_debug.json" if debug else "boggle_history.json"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            gist_data = response.json()
            files = gist_data.get("files", {})
            sync_file = files.get(filename)
            
            if sync_file:
                content = sync_file.get("content")
                if content:
                    cloud_data = json.loads(content)
                    cloud_games = cloud_data.get("games", [])
                    
                    if debug: print(f"[DEBUG] Gist Sync: Fetched {len(cloud_games)} games from cloud ({filename}).")
                    
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
    """Additive sync: Fetches cloud data, merges with local data, and pushes the union."""
    config = get_config()
    if not config or not config.get("pat") or not config.get("gist_id"):
        return

    gist_id = config["gist_id"]
    pat = config["pat"]
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {"Authorization": f"token {pat}"}
    filename = "boggle_history_debug.json" if debug else "boggle_history.json"

    try:
        # 1. Fetch current cloud state to avoid overwriting games played on other machines
        cloud_games = []
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            gist_data = response.json()
            sync_file = gist_data.get("files", {}).get(filename)
            if sync_file and sync_file.get("content"):
                try:
                    cloud_games = json.loads(sync_file["content"]).get("games", [])
                except:
                    if debug: print("[DEBUG] Gist Sync: Cloud file corrupted, starting fresh.")
        elif response.status_code != 404:
            # If it's not a "not found" error, something is wrong. Abort to be safe.
            if debug: print(f"[DEBUG] Gist Sync: Aborting push due to fetch error ({response.status_code})")
            return

        # 2. Fetch all local games
        local_games = boggle_history.get_history(only_finished=False)
        
        # 3. Perform Union Merge based on GUID
        # We build a dictionary keyed by GUID to ensure uniqueness
        master_registry = {g["guid"]: g for g in cloud_games if "guid" in g}
        
        # Add/Overwrite with local games (local is the source of truth for its own data)
        for g in local_games:
            if "guid" in g:
                master_registry[g["guid"]] = g
                
        merged_list = sorted(master_registry.values(), key=lambda x: x.get("timestamp", ""))

        # 4. Prepare and Push Gist content
        payload = {
            "files": {
                filename: {
                    "content": json.dumps({"games": merged_list}, indent=2)
                }
            }
        }
        
        response = requests.patch(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            if debug: print(f"[DEBUG] Gist Sync: Non-destructive sync successful ({filename}). Total games: {len(merged_list)}")
        else:
            if debug: print(f"[DEBUG] Gist Sync: Push failed with status {response.status_code}")
    except Exception as e:
        if debug: print(f"[DEBUG] Gist Sync: Push error: {e}")

def sync_pull_async(debug=False):
    threading.Thread(target=pull_from_gist, args=(debug,), daemon=True).start()

def sync_push_async(debug=False):
    threading.Thread(target=push_to_gist, args=(debug,), daemon=True).start()
