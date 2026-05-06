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
    def __init__(self, parent, game_id, is_embedded=False):
        if is_embedded:
            self.window = parent
        else:
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
        
        header_frame = tk.Frame(self.window, bg="#fcfcfc", pady=10, padx=20, highlightthickness=1, highlightbackground="#eee")
        header_frame.pack(fill="x", padx=10, pady=5)
        
        main_text = f"Partie terminée ! Classement : {rank_data['overall_rank']} / {rank_data['total_games']}"
        tk.Label(header_frame, text=main_text, font=("Segoe UI", 12, "bold"), bg="#fcfcfc", fg="#333").pack()
        
        sub_text = f"Grille {rank_data['richness']} : vous êtes classé {rank_data['richness_rank']} dans cette catégorie."
        tk.Label(header_frame, text=sub_text, font=("Segoe UI", 10), bg="#fcfcfc", fg="#666").pack()

    def setup_tabs(self):
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=5)
        
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
        self.notebook.add(tab, text="Général")
        
        x, score_pct, words_pct, _ = self._prepare_data()
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(x, score_pct, label="% Score", marker='o', markersize=3, color='#0078d7', alpha=0.6)
        ax.plot(x, words_pct, label="% Mots", marker='s', markersize=3, color='#2e7d32', alpha=0.6)
        
        if len(score_pct) >= 5:
            ma_score = np.convolve(score_pct, np.ones(5)/5, mode='valid')
            ax.plot(range(5, len(score_pct)+1), ma_score, color='#0078d7', lw=2, linestyle='--')
            
        ax.set_title("Progression (%)", fontname="Segoe UI")
        ax.set_xlabel("Partie #", fontname="Segoe UI")
        ax.set_ylabel("Pourcentage (%)", fontname="Segoe UI")
        ax.legend()
        ax.grid(True, alpha=0.2)
        
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def add_long_words_tab(self):
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="Mots Longs")
        
        x, _, _, top_tier_rates = self._prepare_data()
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(x, top_tier_rates, label="Taux 'Top-Tier'", marker='d', markersize=4, color='#7b1fa2')
        
        if len(top_tier_rates) >= 5:
            ma_tier = np.convolve(top_tier_rates, np.ones(5)/5, mode='valid')
            ax.plot(range(5, len(top_tier_rates)+1), ma_tier, color='#7b1fa2', lw=2, linestyle='--')

        ax.set_title("Efficacité sur les mots longs", fontname="Segoe UI")
        ax.set_ylabel("% Mots [Max-2, Max] trouvés", fontname="Segoe UI")
        ax.set_xlabel("Partie #", fontname="Segoe UI")
        ax.grid(True, alpha=0.2)
        
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def add_binned_progress_tab(self):
        tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(tab, text="Richesse")
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax1 = fig.add_subplot(121)
        ax2 = fig.add_subplot(122)
        
        bins = {"Aride": [], "Fertile": [], "Luxuriante": []}
        for g in self.history:
            r = boggle_history.get_richness_bin(g['max_score'])
            pct = (g['score'] / g['max_score'] * 100) if g['max_score'] > 0 else 0
            bins[r].append(pct)
            
        colors = {"Aride": "#e57373", "Fertile": "#64b5f6", "Luxuriante": "#81c784"}
        
        for name, data in bins.items():
            if data:
                ax1.plot(range(1, len(data)+1), data, label=name, color=colors[name], marker='o', markersize=2, alpha=0.7)
        
        ax1.set_title("Progression par type", fontname="Segoe UI")
        ax1.set_ylabel("% Score", fontname="Segoe UI")
        ax1.legend()
        ax1.grid(True, alpha=0.2)
        
        valid_data = [data for data in bins.values() if data]
        valid_labels = [name for name, data in bins.items() if data]
        if valid_data:
            ax2.boxplot(valid_data, labels=valid_labels)
            ax2.set_title("Niveau moyen par type", fontname="Segoe UI")
            ax2.set_ylabel("% Score", fontname="Segoe UI")
            ax2.grid(True, alpha=0.2)

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
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
        
        ax1.hist(all_scores, bins=15, color='#eee', edgecolor='#ccc', label='Historique')
        ax1.axvline(current_score, color='#d32f2f', linestyle='--', lw=2, label='Actuelle')
        ax1.set_title("Tous les scores", fontname="Segoe UI")
        ax1.legend()
        
        ax2.hist(last_n, bins=10, color='#e3f2fd', edgecolor='#90caf9', label='20 dernières')
        ax2.axvline(current_score, color='#d32f2f', linestyle='--', lw=2, label='Actuelle')
        ax2.set_title("Scores récents", fontname="Segoe UI")
        ax2.legend()
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def setup_footer(self):
        footer = tk.Frame(self.window, bg="white", pady=5)
        footer.pack(fill="x")
        
        btn = tk.Button(footer, text="Ouvrir Graphique 3D Interactif (Plotly)", command=self.open_plotly, 
                        bg="#f5f5f5", fg="#0078d7", relief="flat", padx=20, pady=5, font=("Segoe UI", 9))
        btn.pack()

    def open_plotly(self):
        if not self.history: return
        
        indices = list(range(1, len(self.history) + 1))
        scores_pct = [(g['score'] / g['max_score'] * 100) if g['max_score'] > 0 else 0 for g in self.history]
        max_scores = [g['max_score'] for g in self.history]
        richness = [boggle_history.get_richness_bin(g['max_score']) for g in self.history]
        
        fig = px.scatter_3d(
            x=indices, y=scores_pct, z=max_scores,
            color=richness,
            color_discrete_map={"Aride": "#e57373", "Fertile": "#64b5f6", "Luxuriante": "#81c784"},
            labels={'x': 'Partie #', 'y': 'Score (%)', 'z': 'Max Possible'},
            title="Analyse 3D Boggle : Temps vs Performance vs Richesse"
        )
        
        fig.update_traces(marker=dict(size=4, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
        
        file_path = "boggle_3d_stats.html"
        fig.write_html(file_path)
        webbrowser.open("file://" + os.path.realpath(file_path))

def show_stats(parent, game_id, is_embedded=False):
    return StatsWindow(parent, game_id, is_embedded)
