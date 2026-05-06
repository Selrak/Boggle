import os
import sys
import pickle
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- CONFIGURATION DES CHEMINS (Basé sur gem_updater.py) ---
GDRIVE_TOOL_DIR = r"C:\Tool\gdrive"
CREDS_PATH = os.path.join(GDRIVE_TOOL_DIR, "credentials.json")
TOKEN_PATH = os.path.join(GDRIVE_TOOL_DIR, "token.pickle")
DICT_PATH = r"C:\Users\cthin\Fun\Boggle\mots_boggle.txt"
DOC_ID = "1be4BUjhWirQV1v0OJxMiEKFnKwzNrx7fvFGltCnwgtc"

SCOPES = ["https://www.googleapis.com/auth/documents"]

# --- LOGIQUE BOGGLE (Trie & DFS) ---
class TrieNode:
    __slots__ = ['children', 'is_word'] 
    def __init__(self):
        self.children = {}; self.is_word = False

class Trie:
    def __init__(self): self.root = TrieNode()
    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children: node.children[char] = TrieNode()
            node = node.children[char]
        node.is_word = True

def solve_boggle(grid_str, dictionary_path):
    trie = Trie()
    with open(dictionary_path, "r", encoding="utf-8") as f:
        for line in f:
            trie.insert(line.strip().upper())

    grid = [list(grid_str[i:i+4]) for i in range(0, 16, 4)]
    found_words = set()

    def dfs(i, j, node, current_word, visited):
        if node.is_word and len(current_word) >= 3:
            found_words.add(current_word)
        for dx, dy in [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]:
            nx, ny = i + dx, j + dy
            if 0 <= nx < 4 and 0 <= ny < 4 and not visited[nx][ny]:
                char = grid[nx][ny]
                if char in node.children:
                    visited[nx][ny] = True
                    dfs(nx, ny, node.children[char], current_word + char, visited)
                    visited[nx][ny] = False

    for i in range(4):
        for j in range(4):
            char = grid[i][j]
            if char in trie.root.children:
                vis = [[False]*4 for _ in range(4)]
                vis[i][j] = True
                dfs(i, j, trie.root.children[char], char, vis)
    
    return sorted(list(found_words))

# --- GOOGLE DOCS SERVICE ---
def get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token: creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token: pickle.dump(creds, token)
    return build('docs', 'v1', credentials=creds)

def main():
    if len(sys.argv) < 2: return
    grid_input = sys.argv[1].upper()
    
    print(f"Calcul des solutions pour {grid_input}...")
    words = solve_boggle(grid_input, DICT_PATH)
    
    # Mise en forme
    formatted_text = "\n".join(words)

    # Envoi vers Google Docs
    service = get_service()
    doc = service.documents().get(documentId=DOC_ID).execute()
    
    # Calcul de l'index de fin pour tout effacer
    content = doc.get('body').get('content')
    end_index = content[-1]['endIndex'] - 1
    
    requests = [
        {'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': max(1, end_index)}}},
        {'insertText': {'location': {'index': 1}, 'text': formatted_text}}
    ]
    
    service.documents().batchUpdate(documentId=DOC_ID, body={'requests': requests}).execute()
    print(f"Succès : {len(words)} mots écrits dans le Doc.")

if __name__ == "__main__":
    main()