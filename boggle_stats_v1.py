import random
import multiprocessing
import time
import argparse
import os
from collections import defaultdict

# --- IMPORTATIONS SCIENTIFIQUES ---
try:
    import numpy as np
    import scipy.stats as st
except ImportError:
    print("Erreur : NumPy et SciPy sont requis pour les analyses statistiques.")
    print("Installez-les avec : pip install numpy scipy")
    exit(1)

# ==========================================
# DÉFINITION ET STRUCTURES (Boggle)
# ==========================================
DES_BOGGLE_FR = [
    "ETUKNO", "EVGTIN", "DECAMP", "IELRUW",
    "EHIFSE", "RECALS", "ENTDOS", "OFXRIA",
    "NAVEDZ", "EIOATA", "GLENYU", "BMAQJO",
    "TLIBRA", "SPULTE", "AIMSOR", "ENHRIS"
]

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

def calcul_score(mot):
    l = len(mot)
    if l <= 4: return 1
    if l == 5: return 2
    if l == 6: return 3
    if l == 7: return 5
    return 11

# ==========================================
# RÉSOLUTION ET WORKER
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

def solve_grid(grid, trie_root, do_score, do_meta):
    found_words = set()
    for i in range(4):
        for j in range(4):
            char = grid[i][j]
            if char in trie_root.children:
                visited = [[False]*4 for _ in range(4)]
                visited[i][j] = True
                dfs(grid, i, j, trie_root.children[char], char, visited, found_words)
    
    nb_mots = len(found_words)
    score = sum(calcul_score(m) for m in found_words) if do_score else 0
    
    # Pour la méta-analyse, on renvoie un dictionnaire des fréquences de longueurs
    longueurs = {}
    if do_meta:
        for m in found_words:
            l = len(m)
            longueurs[l] = longueurs.get(l, 0) + 1
            
    # On renvoie aussi la grille sous forme de chaîne pour l'affichage
    grid_str = "".join("".join(row) for row in grid)
    
    return nb_mots, score, grid_str, longueurs

global_trie_root = None 

def init_worker():
    global global_trie_root
    trie = Trie()
    try:
        with open("mots_boggle.txt", "r", encoding="utf-8") as f:
            for line in f:
                trie.insert(line.strip())
        global_trie_root = trie.root
    except FileNotFoundError:
        pass

def worker_task(args):
    do_score, do_meta = args
    des_melanges = random.sample(DES_BOGGLE_FR, 16)
    lettres = [random.choice(de) for de in des_melanges]
    grid = [lettres[i:i+4] for i in range(0, 16, 4)]
    return solve_grid(grid, global_trie_root, do_score, do_meta)

# ==========================================
# ANALYSE STATISTIQUE (SCIPY)
# ==========================================
def fit_distribution(data, titre):
    print(f"\n--- Recherche de la meilleure distribution pour : {titre} ---")
    
    # Distributions à tester (Gaussienne, Log-Normale, Gamma, Poisson-like via Weibull)
    distributions = [
        ("Normale (Gaussienne)", st.norm),
        ("Log-Normale", st.lognorm),
        ("Gamma", st.gamma),
        ("Weibull", st.weibull_min)
    ]
    
    # On crée un histogramme empirique pour comparer (calcul de l'erreur)
    y, x = np.histogram(data, bins='auto', density=True)
    x = (x + np.roll(x, -1))[:-1] / 2.0 # Milieux des bins
    
    meilleur_nom = ""
    meilleure_erreur = float('inf')
    meilleurs_params = ()
    
    for nom, dist in distributions:
        # Fit les données à la distribution
        params = dist.fit(data)
        
        # Calcule la courbe PDF (Probability Density Function) fittée
        pdf_fitted = dist.pdf(x, *params)
        
        # Somme des erreurs au carré (SSE) entre l'empirique et le théorique
        sse = np.sum(np.power(y - pdf_fitted, 2.0))
        
        print(f"  > {nom:20s} : SSE (Erreur) = {sse:.6e}")
        
        if sse < meilleure_erreur:
            meilleure_erreur = sse
            meilleur_nom = nom
            meilleurs_params = params
            
    print(f">> MEILLEUR FIT : {meilleur_nom}")
    return meilleur_nom, meilleurs_params

# ==========================================
# FONCTION PRINCIPALE
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Simulateur Statistique Boggle")
    parser.add_argument('-n', '--nombre', type=int, default=50000, help="Nombre de grilles à simuler")
    parser.add_argument('--score', action='store_true', help="Calculer et analyser les scores")
    parser.add_argument('--meta-longueur', action='store_true', help="Étude méta-stochastique sur la longueur des mots")
    args = parser.parse_args()

    if not os.path.exists("mots_boggle.txt"):
        print("Erreur : 'mots_boggle.txt' est introuvable.")
        return

    print(f"Lancement de l'étude sur {args.nombre} grilles aléatoires.")
    nb_cpus = multiprocessing.cpu_count()
    
    start_time = time.time()
    last_print = start_time

    mots_list = []
    scores_list = []
    meta_lambdas = [] # Pour stocker la longueur moyenne par grille
    
    max_mots = -1
    grilles_max_mots = []
    max_score = -1
    grilles_max_score = []

    # Utilisation de imap_unordered pour avoir un flux continu et faire un heartbeat
    with multiprocessing.Pool(processes=nb_cpus, initializer=init_worker) as pool:
        # On prépare les arguments pour chaque worker
        tasks = ((args.score, args.meta_longueur) for _ in range(args.nombre))
        
        completed = 0
        chunk_size = max(1, args.nombre // (nb_cpus * 10)) # Optimisation des transferts IPC
        
        for res in pool.imap_unordered(worker_task, tasks, chunksize=chunk_size):
            nb_mots, score, grid_str, longueurs = res
            
            mots_list.append(nb_mots)
            if args.score:
                scores_list.append(score)
                
            # Traitement des records
            if nb_mots > max_mots:
                max_mots = nb_mots
                grilles_max_mots = [grid_str]
            elif nb_mots == max_mots:
                grilles_max_mots.append(grid_str)
                
            if args.score:
                if score > max_score:
                    max_score = score
                    grilles_max_score = [grid_str]
                elif score == max_score:
                    grilles_max_score.append(grid_str)

            # Traitement méta-longueur : distribution géométrique/poissonnienne des longueurs
            if args.meta_longueur and nb_mots > 0:
                # La longueur minimale est 3. On calcule la moyenne des longueurs > 3
                # Cela correspond au paramètre lambda d'une loi de Poisson décalée
                total_lettres = sum((l - 3) * count for l, count in longueurs.items())
                moyenne_l_sup_3 = total_lettres / nb_mots
                meta_lambdas.append(moyenne_l_sup_3)

            # Heartbeat toutes les 10 secondes
            completed += 1
            now = time.time()
            if now - last_print >= 10.0:
                vitesse = completed / (now - start_time)
                pct = (completed / args.nombre) * 100
                print(f"[\u2665] {completed}/{args.nombre} grilles ({pct:.1f}%) - Vitesse : {vitesse:.0f} grilles/sec")
                last_print = now

    end_time = time.time()
    temps_exec = end_time - start_time

    # --- RÉSULTATS STANDARDS ---
    print("\n" + "="*50)
    print(" RÉSULTATS STATISTIQUES GLOBAUX")
    print("="*50)
    print(f"Temps total : {temps_exec:.2f} s | Vitesse : {args.nombre/temps_exec:.0f} g/s")
    
    mots_arr = np.array(mots_list)
    print(f"\n[NOMBRE DE MOTS]")
    print(f"Moyenne    : {np.mean(mots_arr):.2f}")
    print(f"Écart-type : {np.std(mots_arr):.2f}")
    print(f"Minimum    : {np.min(mots_arr)}")
    print(f"Maximum    : {max_mots}")
    
    # Affichage des meilleures grilles
    print(f"\nGrille(s) ayant le plus de mots ({max_mots} mots) :")
    for g in grilles_max_mots[:5]: # On limite à 5 pour ne pas spammer
        print(f"  {g[:4]}-{g[4:8]}-{g[8:12]}-{g[12:]}")
    if len(grilles_max_mots) > 5: print("  ...")

    # Fit Mots
    fit_distribution(mots_arr, "Nombre de Mots par Grille")

    # --- RÉSULTATS SCORE ---
    if args.score:
        scores_arr = np.array(scores_list)
        print("\n" + "="*50)
        print(" RÉSULTATS DES SCORES")
        print("="*50)
        print(f"Moyenne    : {np.mean(scores_arr):.2f}")
        print(f"Écart-type : {np.std(scores_arr):.2f}")
        print(f"Maximum    : {max_score}")
        
        print(f"\nGrille(s) ayant le meilleur score ({max_score} pts) :")
        for g in grilles_max_score[:5]:
            print(f"  {g[:4]}-{g[4:8]}-{g[8:12]}-{g[12:]}")
            
        fit_distribution(scores_arr, "Score par Grille")

    # --- RÉSULTATS MÉTA-STOCHASTIQUES ---
    if args.meta_longueur and len(meta_lambdas) > 0:
        print("\n" + "="*50)
        print(" ÉTUDE MÉTA-STOCHASTIQUE DES LONGUEURS")
        print("="*50)
        print("Méthode : Pour chaque grille, la distribution des longueurs des mots")
        print("est modélisée par une loi de Poisson décalée de 3 (puisque min = 3 lettres).")
        print("Le paramètre λ (lambda) de cette loi a été calculé pour chaque grille.")
        
        lambdas_arr = np.array(meta_lambdas)
        print(f"\n[PARAMÈTRE λ (Allongement moyen au-delà de 3 lettres)]")
        print(f"Moyenne des λ : {np.mean(lambdas_arr):.4f}")
        print(f"Écart-type    : {np.std(lambdas_arr):.4f}")
        
        # Fit pour voir comment les Lambdas sont distribués
        fit_distribution(lambdas_arr, "Méta-distribution du paramètre λ des grilles")

if __name__ == '__main__':
    main()