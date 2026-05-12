import os
import json
import webbrowser
from datetime import datetime
import numpy as np

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except ImportError:
    plt = None

import boggle_history
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

def calculate_top_tier_rate(found_lens, poss_lens):
    if not poss_lens: return 0
    max_poss_len = max(int(k) for k in poss_lens.keys())
    target_lens = [str(max_poss_len), str(max_poss_len - 1), str(max_poss_len - 2)]
    
    total_target_poss = sum(poss_lens.get(l, 0) for l in target_lens)
    if total_target_poss == 0: return 0
    
    total_target_found = sum(found_lens.get(l, 0) for l in target_lens)
    return (total_target_found / total_target_poss) * 100

class StatsWindowQt(QWidget):
    def __init__(self, game_id=None, debug=False, parent=None):
        super().__init__(parent)
        self.current_id = game_id
        
        # Ensure we are reading from the correct database
        boggle_history.set_db_name(debug=debug)
        
        # Ne charger que l'historique valide (fini et > 3min) pour l'affichage
        self.history = boggle_history.get_history(only_finished=True)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        if not self.history:
            lbl = QLabel("Pas assez de données pour afficher les stats.")
            lbl.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(lbl)
            return

        self.setup_header()
        self.setup_tabs()
        self.setup_footer()

    def setup_header(self):
        if self.current_id is None: return
        rank_data = boggle_history.get_rankings(self.current_id)
        if not rank_data: return
        
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #fcfcfc; border: 1px solid #eee; border-radius: 5px;")
        h_layout = QVBoxLayout(header_widget)
        
        main_text = f"Partie terminée ! Classement : {rank_data['overall_rank']} / {rank_data['total_games']}"
        l1 = QLabel(main_text)
        l1.setFont(QFont("Arial", 12, QFont.Bold))
        l1.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(l1)
        
        sub_text = f"Grille {rank_data['richness']} : vous êtes classé {rank_data['richness_rank']} dans cette catégorie."
        l2 = QLabel(sub_text)
        l2.setFont(QFont("Arial", 10))
        l2.setAlignment(Qt.AlignCenter)
        l2.setStyleSheet("color: #666;")
        h_layout.addWidget(l2)
        
        self.layout.addWidget(header_widget)

    def setup_tabs(self):
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        if plt is None:
            err_tab = QWidget()
            err_layout = QVBoxLayout(err_tab)
            lbl = QLabel("Matplotlib est requis pour les graphiques.")
            lbl.setAlignment(Qt.AlignCenter)
            err_layout.addWidget(lbl)
            self.tabs.addTab(err_tab, "Erreur")
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
            
        return list(x), score_pct, words_pct, top_tier_rates

    def add_overall_progress_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        x, score_pct, words_pct, _ = self._prepare_data()
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(x, score_pct, label="% Score", marker='o', markersize=3, color='#0078d7', alpha=0.6)
        ax.plot(x, words_pct, label="% Mots", marker='s', markersize=3, color='#2e7d32', alpha=0.6)
        
        if len(score_pct) >= 5:
            ma_score = np.convolve(score_pct, np.ones(5)/5, mode='valid')
            ax.plot(range(5, len(score_pct)+1), ma_score, color='#0078d7', lw=2, linestyle='--')
            
        ax.set_title("Progression (%)", fontname="Arial")
        ax.set_xlabel("Partie #", fontname="Arial")
        ax.set_ylabel("Pourcentage (%)", fontname="Arial")
        ax.legend()
        ax.grid(True, alpha=0.2)
        
        canvas = FigureCanvas(fig)
        tab_layout.addWidget(canvas)
        self.tabs.addTab(tab, "Général")

    def add_long_words_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        x, _, _, top_tier_rates = self._prepare_data()
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(x, top_tier_rates, label="Taux 'Top-Tier'", marker='d', markersize=4, color='#7b1fa2')
        
        if len(top_tier_rates) >= 5:
            ma_tier = np.convolve(top_tier_rates, np.ones(5)/5, mode='valid')
            ax.plot(range(5, len(top_tier_rates)+1), ma_tier, color='#7b1fa2', lw=2, linestyle='--')

        ax.set_title("Efficacité sur les mots longs", fontname="Arial")
        ax.set_ylabel("% Mots [Max-2, Max] trouvés", fontname="Arial")
        ax.set_xlabel("Partie #", fontname="Arial")
        ax.grid(True, alpha=0.2)
        
        canvas = FigureCanvas(fig)
        tab_layout.addWidget(canvas)
        self.tabs.addTab(tab, "Mots Longs")

    def add_binned_progress_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax1 = fig.add_subplot(121)
        ax2 = fig.add_subplot(122)
        
        bins = {'Aride': [], 'Fertile': [], 'Luxuriante': []}
        for g in self.history:
            if g['max_score'] < 50: bins['Aride'].append(g)
            elif g['max_score'] < 150: bins['Fertile'].append(g)
            else: bins['Luxuriante'].append(g)
            
        colors = {'Aride': '#ff9800', 'Fertile': '#4caf50', 'Luxuriante': '#f44336'}
        
        for bin_name, games in bins.items():
            if not games: continue
            x = range(1, len(games) + 1)
            score_pct = [(g['score'] / g['max_score'] * 100) if g['max_score'] > 0 else 0 for g in games]
            
            ax1.plot(x, score_pct, label=bin_name, marker='.', markersize=4, color=colors[bin_name], alpha=0.7)
            
            if len(score_pct) >= 3:
                ma = np.convolve(score_pct, np.ones(3)/3, mode='valid')
                ax2.plot(range(3, len(score_pct)+1), ma, label=bin_name, color=colors[bin_name], lw=2)

        ax1.set_title("Brut", fontname="Arial")
        ax2.set_title("Tendance (MM3)", fontname="Arial")
        ax1.legend(fontsize=8); ax2.legend(fontsize=8)
        ax1.grid(True, alpha=0.2); ax2.grid(True, alpha=0.2)
        
        fig.tight_layout()
        canvas = FigureCanvas(fig)
        tab_layout.addWidget(canvas)
        self.tabs.addTab(tab, "Richesse")

    def add_distribution_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        all_scores = [g['score'] for g in self.history]
        last_n = all_scores[-20:]
        
        # Safe lookup for current score (might be filtered out if unfinished)
        current_score = next((g['score'] for g in self.history if g['id'] == self.current_id), None)
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
        
        ax1.hist(all_scores, bins=15, color='#eee', edgecolor='#ccc', label='Historique')
        if current_score is not None:
            ax1.axvline(current_score, color='#d32f2f', linestyle='--', lw=2, label='Actuelle')
        ax1.set_title("Tous les scores", fontname="Arial")
        ax1.legend()
        
        ax2.hist(last_n, bins=10, color='#e3f2fd', edgecolor='#90caf9', label='20 dernières')
        if current_score is not None:
            ax2.axvline(current_score, color='#d32f2f', linestyle='--', lw=2, label='Actuelle')
        ax2.set_title("Scores récents", fontname="Arial")
        ax2.legend()
        
        fig.tight_layout()
        canvas = FigureCanvas(fig)
        tab_layout.addWidget(canvas)
        self.tabs.addTab(tab, "Distribution")

    def setup_footer(self):
        btn = QPushButton("Ouvrir graphique 3D Interactif (Navigateur)")
        btn.clicked.connect(self.generate_3d_plot)
        self.layout.addWidget(btn)

    def generate_3d_plot(self):
        try:
            import plotly.graph_objects as go
            import pandas as pd
        except ImportError:
            return

        df = pd.DataFrame(self.history)
        if df.empty: return
        
        df['score_pct'] = (df['score'] / df['max_score'] * 100).fillna(0)
        df['words_pct'] = (df['words_count'] / df['max_words_count'] * 100).fillna(0)
        df['game_num'] = range(1, len(df) + 1)
        
        fig = go.Figure(data=[go.Scatter3d(
            x=df['game_num'],
            y=df['score_pct'],
            z=df['words_pct'],
            mode='lines+markers',
            marker=dict(
                size=5,
                color=df['score'],
                colorscale='Viridis',
                opacity=0.8
            ),
            line=dict(color='darkblue', width=2),
            text=[f"Score: {s}<br>Mots: {w}" for s, w in zip(df['score'], df['words_count'])],
            hoverinfo='text'
        )])

        fig.update_layout(
            title="Progression Boggle 3D",
            scene=dict(
                xaxis_title='Partie #',
                yaxis_title='% Score Possible',
                zaxis_title='% Mots Possibles'
            )
        )
        
        file_path = "boggle_3d_stats.html"
        fig.write_html(file_path)
        webbrowser.open("file://" + os.path.realpath(file_path))
