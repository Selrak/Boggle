import random
import multiprocessing
import time

# ==========================================
# 1. DÉFINITION DES DÉS DU BOGGLE FRANÇAIS
# ==========================================
DES_BOGGLE_FR = [
    "ETUKNO", "EVGTIN", "DECAMP", "IELRUW",
    "EHIFSE", "RECALS", "ENTDOS", "OFXRIA",
    "NAVEDZ", "EIOATA", "GLENYU", "BMAQJO",
    "TLIBRA", "SPULTE", "AIMSOR", "ENHRIS"
]

# ==========================================
# 2. STRUCTURE DU TRIE POUR LE DICTIONNAIRE
# ==========================================
class TrieNode:
    __slots__ = ['children', 'is_word'] 
    def __init__(self):
        self.children = {}
        self.is_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_word = True

# ==========================================
# 3. ALGORITHME DE RÉSOLUTION (DFS)
# ==========================================
def dfs(grid, i, j, node, current_word, visited, found_words):
    if node.is_word and len(current_word) >= 3:
        found_words.add(current_word)

    directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]

    for dx, dy in directions:
        nx, ny = i + dx, j + dy
        if 0 <= nx < 4 and 0 <= ny < 4 and not visited[nx][ny]:
            char = grid[nx][ny]
            if char in node.children:
                visited[nx][ny] = True
                dfs(grid, nx, ny, node.children[char], current_word + char, visited, found_words)
                visited[nx][ny] = False 

def solve_grid(grid, trie_root):
    found_words = set()
    for i in range(4):
        for j in range(4):
            char = grid[i][j]
            if char in trie_root.children:
                visited = [[False]*4 for _ in range(4)]
                visited[i][j] = True
                dfs(grid, i, j, trie_root.children[char], char, visited, found_words)
    return len(found_words)

# ==========================================
# 4. GÉNÉRATION ET GESTION PARALLÈLE (CORRIGÉE)
# ==========================================
def generate_random_grid():
    des_melanges = random.sample(DES_BOGGLE_FR, 16)
    lettres = [random.choice(de) for de in des_melanges]
    return [lettres[i:i+4] for i in range(0, 16, 4)]

global_trie_root = None 

def init_worker():
    """Chaque processus enfant charge son propre dictionnaire au démarrage."""
    global global_trie_root
    trie = Trie()
    try:
        # On utilise directement le fichier nettoyé !
        with open("mots_boggle.txt", "r", encoding="utf-8") as f:
            for line in f:
                trie.insert(line.strip())
        global_trie_root = trie.root
    except FileNotFoundError:
        pass # L'erreur sera gérée plus élégamment si le fichier manque

def worker_task(_):
    grid = generate_random_grid()
    return solve_grid(grid, global_trie_root)

# ==========================================
# 5. FONCTION PRINCIPALE (STATISTIQUES)
# ==========================================
def main():
    import os
    if not os.path.exists("mots_boggle.txt"):
        print("Erreur : Le fichier 'mots_boggle.txt' est introuvable.")
        return

    nb_grilles_a_simuler = 500000
    nb_cpus = multiprocessing.cpu_count()
    
    print(f"Lancement de l'étude sur {nb_grilles_a_simuler} grilles aléatoires.")
    print(f"Parallélisation sur {nb_cpus} processus. Ça va chauffer !...")

    start_time = time.time()

    # Plus d'arguments compliqués passés au pool, init_worker se débrouille
    with multiprocessing.Pool(processes=nb_cpus, initializer=init_worker) as pool:
        results = pool.map(worker_task, range(nb_grilles_a_simuler))

    end_time = time.time()

    temps_exec = end_time - start_time
    moyenne = sum(results) / len(results)
    grille_max = max(results)
    grille_min = min(results)
    variance = sum((x - moyenne) ** 2 for x in results) / len(results)
    ecart_type = variance ** 0.5

    print("\n--- RÉSULTATS STATISTIQUES (Monte-Carlo) ---")
    print(f"Temps de calcul    : {temps_exec:.2f} secondes")
    print(f"Vitesse            : {nb_grilles_a_simuler/temps_exec:.0f} grilles/sec")
    print(f"Moyenne de mots    : {moyenne:.2f} mots par grille")
    print(f"Écart-type         : {ecart_type:.2f}")
    print(f"Minimum trouvé     : {grille_min} mots")
    print(f"Maximum trouvé     : {grille_max} mots")

if __name__ == '__main__':
    main()