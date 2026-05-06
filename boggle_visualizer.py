import tkinter as tk
from tkinter import ttk
import json
import os
import webbrowser
from datetime import datetime
import numpy as np

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except ImportError:
    plt = None

try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    go = None

import boggle_history

def calculate_top_tier_rate(found_lens, poss_lens):
    if not poss_lens: return 0
    max_l = max(int(k) for k in poss_lens.keys())
    tier_keys = [str(i) for i in range(max(3, max_l - 2), max_l + 1)]
    total_poss = sum(poss_lens.get(k, 0) for k in tier_keys)
    if total_poss == 0: return 0
    total_found = sum(found_lens.get(k, 0) for k in tier_keys)
    return (total_found / total_poss) * 100

class StatsWindow:
    def __init__(self, parent, game_id):
        self.window = tk.Toplevel(parent)
        self.window.title("Statistiques et Progression")
        self.window.geometry("900x700")
        self.window.configure(bg="white")
        
        self.history = boggle_history.get_history()
        self.current_id = game_id
        
        if not self.history:
            tk.Label(self.window, text="Pas assez de données pour afficher les stats.", bg="white").pack(pady=20)
            return

        self.setup_header()
        self.setup_tabs()
        self.setup_footer()

    def setup_header(self):
        rank_data = boggle_history.get_rankings(self.current_id)
        if not rank_data: return
        
        header_frame = tk.Frame(self.window, bg="#f8f9fa", pady=15, padx=20)
        header_frame.pack(fill="x")
        
        main_text = f"Partie terminée ! Classement : {rank_data['overall_rank']} / {rank_data['total_games']}"
        tk.Label(header_frame, text=main_text, font=("Arial", 14, "bold"), bg="#f8f9fa").pack()
        
        sub_text = f"Pour les grilles de type '{rank_data['richness']}', vous êtes classé {rank_data['richness_rank']}."
        tk.Label(header_frame, text=sub_text, font=("Arial", 11), bg="#f8f9fa", fg="#555").pack()

    def setup_tabs(self):
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        if plt is None:
            err_tab = tk.Frame(self.notebook, bg="white")
            self.notebook.add(err_tab, text="Erreur")
            tk.Label(err_tab, text="Matplotlib est requis pour les graphiques.", bg="white").pack(pady=50)
            return

        self.add_overall_progress_tab()
        self.add_long_words_tab()
        self.add_binned_progress_tab()
        self.add_distribution_tab()

    def _prepare_data(self):
        x = range(1, len(self.history) + 1)
        score_pct = [(g['score'] / g['max_score'] * 100) if g['max_score'] > 0 else 0 for g in self.history]
        words_pct = [(g['words_count'] / g['max_words_count'] * 100) if g['max_words_count'] > 0 else 0 for g in self.history]
        
        top_tier_rates = []
        for g in self.history:
            found = json.loads(g['found_lengths_json'])
            poss = json.loads(g['possible_lengths_json'])
            top_tier_rates.append(calculate_top_tier_rate(found, poss))
            
        return x, score_pct, words_pct, top_tier_rates

    def add_overall_progress_tab(self):
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="Progression Générale")
        
        x, score_pct, words_pct, _ = self._prepare_data()
        
        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(x, score_pct, label="% Score", marker='o', markersize=4, color='#1f77b4', alpha=0.7)
        ax.plot(x, words_pct, label="% Mots", marker='s', markersize=4, color='#ff7f0e', alpha=0.7)
        
        # Moving averages
        if len(score_pct) >= 5:
            ma_score = np.convolve(score_pct, np.ones(5)/5, mode='valid')
            ax.plot(range(5, len(score_pct)+1), ma_score, color='#1f77b4', lw=2, linestyle='--')
            
        ax.set_title("Progression du Score et des Mots (%)")
        ax.set_xlabel("Numéro de partie")
        ax.set_ylabel("Pourcentage (%)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def add_long_words_tab(self):
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="Mots Longs")
        
        x, _, _, top_tier_rates = self._prepare_data()
        
        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(x, top_tier_rates, label="Taux de capture 'Top-Tier'", marker='d', color='#2ca02c')
        
        if len(top_tier_rates) >= 5:
            ma_tier = np.convolve(top_tier_rates, np.ones(5)/5, mode='valid')
            ax.plot(range(5, len(top_tier_rates)+1), ma_tier, color='#2ca02c', lw=2, linestyle='--')

        ax.set_title("Capacité à trouver les mots les plus longs de la grille")
        ax.set_ylabel("% des mots de longueur [Max-2, Max] trouvés")
        ax.set_xlabel("Numéro de partie")
        ax.grid(True, alpha=0.3)
        
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def add_binned_progress_tab(self):
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="Par Richesse")
        
        fig = Figure(figsize=(8, 5), dpi=100)
        ax1 = fig.add_subplot(121)
        ax2 = fig.add_subplot(122)
        
        bins = {"Poor": [], "Average": [], "Rich": []}
        for g in self.history:
            r = boggle_history.get_richness_bin(g['max_score'])
            pct = (g['score'] / g['max_score'] * 100) if g['max_score'] > 0 else 0
            bins[r].append(pct)
            
        colors = {"Poor": "#9edae5", "Average": "#1f77b4", "Rich": "#d62728"}
        
        # Binned Progress (Time vs Score per bin)
        for name, data in bins.items():
            if data:
                ax1.plot(range(1, len(data)+1), data, label=name, color=colors[name])
        
        ax1.set_title("Progression par type")
        ax1.set_ylabel("% Score")
        ax1.legend()
        
        # Boxplot comparison
        valid_data = [data for data in bins.values() if data]
        valid_labels = [name for name, data in bins.items() if data]
        if valid_data:
            ax2.boxplot(valid_data, labels=valid_labels)
            ax2.set_title("Distribution par type")
            ax2.set_ylabel("% Score")

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def add_distribution_tab(self):
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="Distributions")
        
        all_scores = [g['score'] for g in self.history]
        last_n = all_scores[-20:]
        current_score = next(g['score'] for g in self.history if g['id'] == self.current_id)
        
        fig = Figure(figsize=(8, 5), dpi=100)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
        
        ax1.hist(all_scores, bins=15, color='#ccc', alpha=0.7, label='Tous les scores')
        ax1.axvline(current_score, color='red', linestyle='--', label='Partie actuelle')
        ax1.set_title("Distribution de tous les scores")
        ax1.legend()
        
        ax2.hist(last_n, bins=10, color='#6baed6', alpha=0.7, label='Dernières 20 parties')
        ax2.axvline(current_score, color='red', linestyle='--', label='Partie actuelle')
        ax2.set_title("Distribution des 20 dernières parties")
        ax2.legend()
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def setup_footer(self):
        footer = tk.Frame(self.window, bg="white", pady=10)
        footer.pack(fill="x")
        
        if go is not None:
            btn = tk.Button(footer, text="Ouvrir Graphique 3D Interactif (Plotly)", command=self.open_plotly, 
                            bg="#e7f3ff", fg="#007bff", relief="flat", padx=10)
            btn.pack()
        else:
            tk.Label(footer, text="Installez 'plotly' pour le graphique 3D interactif.", bg="white", fg="#999").pack()

    def open_plotly(self):
        if not self.history: return
        
        indices = list(range(1, len(self.history) + 1))
        scores_pct = [(g['score'] / g['max_score'] * 100) if g['max_score'] > 0 else 0 for g in self.history]
        max_scores = [g['max_score'] for g in self.history]
        richness = [boggle_history.get_richness_bin(g['max_score']) for g in self.history]
        
        fig = px.scatter_3d(
            x=indices, y=scores_pct, z=max_scores,
            color=richness,
            labels={'x': 'Partie #', 'y': 'Score (%)', 'z': 'Max Score (Richesse)'},
            title="Progression Boggle 3D : Temps vs Performance vs Richesse de grille"
        )
        
        fig.update_traces(marker=dict(size=5, opacity=0.8))
        
        file_path = "boggle_3d_stats.html"
        fig.write_html(file_path)
        webbrowser.open("file://" + os.path.realpath(file_path))

def show_stats(parent, game_id):
    StatsWindow(parent, game_id)
