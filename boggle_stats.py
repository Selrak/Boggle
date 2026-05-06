import random
import multiprocessing
import time
import argparse
import os
import sys
import warnings

# --- IMPORTATIONS SCIENTIFIQUES ---
try:
    import numpy as np
    import scipy.stats as st
    import matplotlib.pyplot as plt
except ImportError:
    print("Erreur : NumPy, SciPy et Matplotlib sont requis.")
    print("Installez-les avec : pip install numpy scipy matplotlib")
    sys.exit(1)

# ==========================================
# DÉFINITION ET STRUCTURES
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

def afficher_grille(g_str):
    """Affiche une chaîne de 16 lettres sous forme de grille 4x4."""
    for i in range(0, 16, 4):
        print(f"    {g_str[i]} {g_str[i+1]} {g_str[i+2]} {g_str[i+3]}")
    print("")

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
    longueurs = {}
    if do_meta:
        for m in found_words:
            l = len(m)
            longueurs[l] = longueurs.get(l, 0) + 1
            
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
# ANALYSE ET GRAPHIQUES (MATPLOTLIB / SCIPY)
# ==========================================
def fit_distribution_and_plot(data, titre, xlabel):
    print(f"\n--- Recherche du fit pour : {titre} ---")
    
    # 1. Échantillonnage pour la vitesse (SciPy rame au-delà de quelques milliers de points)
    # On retire les zéros stricts pour éviter les RuntimeWarning (division by zero / log(0))
    data_clean = data[data > 0] 
    if len(data_clean) > 5000:
        data_fit = np.random.choice(data_clean, 5000, replace=False)
    else:
        data_fit = data_clean

    distributions = [
        ("Normale", st.norm),
        ("Log-Normale", st.lognorm),
        ("Gamma", st.gamma),
        ("Weibull", st.weibull_min)
    ]
    
    y, x_edges = np.histogram(data, bins='auto', density=True)
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2

    meilleur_nom = ""
    meilleure_erreur = float('inf')
    meilleurs_params = ()
    meilleur_dist = None

    # On ignore poliment les avertissements mathématiques de SciPy
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for nom, dist in distributions:
            params = dist.fit(data_fit)
            pdf_fitted = dist.pdf(x_centers, *params)
            sse = np.sum((y - pdf_fitted) ** 2)
            print(f"  > {nom:15s} : SSE = {sse:.6e}")
            
            if sse < meilleure_erreur:
                meilleure_erreur = sse
                meilleur_nom = nom
                meilleurs_params = params
                meilleur_dist = dist

    print(f">> MEILLEUR FIT : {meilleur_nom}")

    # 2. Construction du Graphique
    plt.figure(figsize=(9, 5))
    plt.hist(data, bins='auto', density=True, alpha=0.6, color='#1f77b4', edgecolor='black', label='Données empiriques')
    
    xmin, xmax = plt.xlim()
    x_plot = np.linspace(xmin, xmax, 200)
    y_plot = meilleur_dist.pdf(x_plot, *meilleurs_params)
    
    plt.plot(x_plot, y_plot, 'r-', lw=2.5, label=f'Fit Optimal ({meilleur_nom})')
    plt.title(f"{titre}\n(Fit : {meilleur_nom})", fontsize=14)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel("Densité de probabilité", fontsize=12)
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    # Ne pas bloquer l'exécution, on affichera tout à la fin
    plt.draw()

# ==========================================
# FONCTION PRINCIPALE
# ==========================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--nombre', type=int, default=100000)
    parser.add_argument('--score', action='store_true')
    parser.add_argument('--meta-longueur', action='store_true')
    args = parser.parse_args()

    print(f"Lancement de l'étude sur {args.nombre} grilles...")
    nb_cpus = multiprocessing.cpu_count()
    start_time = time.time()
    last_print = start_time

    mots_list = []
    scores_list = []
    meta_lambdas = []
    
    max_mots = -1
    grilles_max_mots = []
    max_score = -1
    grilles_max_score = []

    with multiprocessing.Pool(processes=nb_cpus, initializer=init_worker) as pool:
        tasks = ((args.score, args.meta_longueur) for _ in range(args.nombre))
        completed = 0
        chunk_size = max(1, args.nombre // (nb_cpus * 10))
        
        for res in pool.imap_unordered(worker_task, tasks, chunksize=chunk_size):
            nb_mots, score, grid_str, longueurs = res
            mots_list.append(nb_mots)
            
            if args.score:
                scores_list.append(score)
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
            if args.meta_longueur and nb_mots > 0:
                total_lettres = sum((l - 3) * count for l, count in longueurs.items())
                meta_lambdas.append(total_lettres / nb_mots)

            # --- Vraie barre de progression en temps réel (0.2s) ---
            completed += 1
            now = time.time()
            if now - last_print >= 0.2:
                vitesse = completed / (now - start_time)
                pct = (completed / args.nombre) * 100
                sys.stdout.write(f"\r[\u2588\u2588\u2588] {completed}/{args.nombre} ({pct:.1f}%) - Vitesse : {vitesse:.0f} g/s")
                sys.stdout.flush()
                last_print = now

    sys.stdout.write(f"\r[\u2713] Terminé ! {args.nombre}/{args.nombre} (100.0%) - Analyse en cours...\n")
    sys.stdout.flush()

    temps_exec = time.time() - start_time
    print(f"\nTemps calcul : {temps_exec:.2f} s | Vitesse : {args.nombre/temps_exec:.0f} g/s")

    # --- RÉSULTATS MOTS ---
    print("\n" + "="*40 + "\n 1. NOMBRE DE MOTS\n" + "="*40)
    mots_arr = np.array(mots_list)
    print(f"Moyenne : {np.mean(mots_arr):.2f} | Max : {max_mots}")
    print(f"Grille(s) de {max_mots} mots :")
    for g in grilles_max_mots[:3]:
        afficher_grille(g)
    fit_distribution_and_plot(mots_arr, "Distribution du Nombre de Mots", "Nombre de mots trouvés")

    # --- RÉSULTATS SCORES ---
    if args.score:
        print("\n" + "="*40 + "\n 2. SCORES\n" + "="*40)
        scores_arr = np.array(scores_list)
        print(f"Moyenne : {np.mean(scores_arr):.2f} | Max : {max_score} pts")
        print(f"Grille(s) de {max_score} points :")
        for g in grilles_max_score[:3]:
            afficher_grille(g)
        fit_distribution_and_plot(scores_arr, "Distribution des Scores", "Points (Score)")

    # --- RÉSULTATS MÉTA ---
    if args.meta_longueur and len(meta_lambdas) > 0:
        print("\n" + "="*40 + "\n 3. MÉTA-STOCHASTIQUE (λ)\n" + "="*40)
        lambdas_arr = np.array(meta_lambdas)
        print(f"Moyenne des λ : {np.mean(lambdas_arr):.4f}")
        fit_distribution_and_plot(lambdas_arr, "Distribution du paramètre λ (Allongement)", "Valeur de λ (Mots > 3 lettres)")

    # Affiche toutes les fenêtres graphiques à la toute fin
    print("\n-> Affichage des graphiques. Fermez les fenêtres pour quitter le programme.")
    plt.show()

if __name__ == '__main__':
    main()