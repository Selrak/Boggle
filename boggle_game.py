import sys
import os
import json
import time
import random
import unicodedata
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QLineEdit, 
                             QPushButton, QTextEdit, QFrame, QSizePolicy, 
                             QMessageBox, QBoxLayout)
from PySide6.QtCore import Qt, QTimer, QSize, QEvent
from PySide6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush

import boggle_history
import boggle_sync
import boggle_visualizer
import subprocess

def remove_accents(input_str):
    nksfd = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nksfd if not unicodedata.combining(c)])

class PauseOverlay(QWidget):
    """Overlay de pause qui masque le plateau."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setStyleSheet("background-color: white;")
        
        self.pause_label = QLabel("PAUSE")
        self.pause_label.setFont(QFont("Arial", 36, QFont.Bold))
        self.pause_label.setAlignment(Qt.AlignCenter)
        self.pause_label.setStyleSheet("color: red;")
        
        self.info_label = QLabel("Appuyez sur ESPACE pour reprendre")
        self.info_label.setFont(QFont("Arial", 14))
        self.info_label.setAlignment(Qt.AlignCenter)
        
        self.layout.addStretch()
        self.layout.addWidget(self.pause_label)
        self.layout.addWidget(self.info_label)
        self.layout.addStretch()
        
        self.hide()

class BoggleGrid(QWidget):
    """Widget de grille personnalisé utilisant paintEvent pour maximiser les performances et la flexibilité."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.letters = [["" for _ in range(4)] for _ in range(4)]
        self.angles = [[0 for _ in range(4)] for _ in range(4)]
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_grid(self, grid_data, angles=None):
        self.letters = grid_data
        self.angles = angles if angles else [[0 for _ in range(4)] for _ in range(4)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Déterminer la taille d'une cellule pour que la grille soit toujours carrée
        side = min(self.width(), self.height())
        margin = 10
        grid_size = side - 2 * margin
        cell_size = grid_size / 4
        
        offset_x = (self.width() - grid_size) / 2
        offset_y = (self.height() - grid_size) / 2
        
        font = QFont("Arial")
        font.setBold(True)
        # Taille de police proportionnelle à la cellule
        font.setPointSizeF(cell_size * 0.45)
        painter.setFont(font)

        for r in range(4):
            for c in range(4):
                x = offset_x + c * cell_size + 5
                y = offset_y + r * cell_size + 5
                rect_size = cell_size - 10
                
                # Dessiner le dé (rectangle arrondi)
                rect_path = QColor("white")
                painter.setPen(QPen(QColor("black"), 3))
                painter.setBrush(QBrush(QColor("white")))
                painter.drawRoundedRect(x, y, rect_size, rect_size, 15, 15)
                
                # Dessiner la lettre avec rotation
                letter = self.letters[r][c]
                if letter:
                    painter.save()
                    # Translation au centre de la cellule pour la rotation
                    painter.translate(x + rect_size / 2, y + rect_size / 2)
                    painter.rotate(self.angles[r][c])
                    
                    # Dessiner le texte au centre
                    # Utiliser boundingRect pour un centrage parfait si nécessaire, 
                    # ou simplement drawText avec l'alignement
                    painter.setPen(QColor("black"))
                    painter.drawText(-rect_size/2, -rect_size/2, rect_size, rect_size, 
                                     Qt.AlignCenter, letter)
                    painter.restore()

class CustomLineEdit(QLineEdit):
    """QLineEdit qui laisse passer la barre espace pour la pause."""
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            # On ignore l'événement pour qu'il remonte à BoggleAppQt.keyPressEvent
            event.ignore()
        else:
            super().keyPressEvent(event)

class ResponsiveContainer(QWidget):
    """Conteneur qui bascule entre HBox et VBox selon le ratio d'aspect."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)
        
        # Zone Grille
        self.grid_widget = BoggleGrid()
        
        # Zone Latérale
        self.side_widget = QWidget()
        self.side_layout = QVBoxLayout(self.side_widget)
        self.side_layout.setContentsMargins(0, 0, 0, 0)
        
        # Saisie et Timer
        self.input_layout = QHBoxLayout()
        self.entry = CustomLineEdit()
        self.entry.setFont(QFont("Arial", 20))
        self.entry.setFixedHeight(50)
        self.timer_label = QLabel("3:00")
        self.timer_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.timer_label.setMinimumWidth(80) # Garantir la visibilité
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.input_layout.addWidget(self.entry)
        self.input_layout.addWidget(self.timer_label)
        self.side_layout.addLayout(self.input_layout)
        
        # Liste de mots
        self.side_layout.addWidget(QLabel("<b>Mots trouvés</b>"))
        self.words_display = QTextEdit()
        self.words_display.setReadOnly(True)
        self.words_display.setFont(QFont("Arial", 13))
        self.side_layout.addWidget(self.words_display)
        
        # Stats et Boutons
        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.extra_score_label = QLabel("")
        self.extra_score_label.setFont(QFont("Arial", 11))
        self.extra_score_label.setStyleSheet("color: green;")
        
        stats_score_layout = QHBoxLayout()
        stats_score_layout.addWidget(self.stats_label)
        stats_score_layout.addWidget(self.extra_score_label)
        stats_score_layout.addStretch()
        self.side_layout.addLayout(stats_score_layout)
        
        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setFont(QFont("Arial", 10))
        self.stats_display.setMaximumHeight(150)
        self.side_layout.addWidget(self.stats_display)
        
        self.reset_btn = QPushButton("Nouveau Jeu (Ctrl+R)")
        self.side_layout.addWidget(self.reset_btn)

        self.main_layout.addWidget(self.grid_widget)
        self.main_layout.addWidget(self.side_widget)

        self.grid_widget.setMinimumSize(300, 300)
        self.side_widget.setMinimumSize(250, 150)

    def resizeEvent(self, event):
        width = self.width()
        height = self.height()
        
        # Basculer l'orientation
        if width > height * 1.1:
            self.main_layout.setDirection(QBoxLayout.LeftToRight)
            self.side_widget.setMaximumWidth(400)
            self.side_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        else:
            self.main_layout.setDirection(QBoxLayout.TopToBottom)
            self.side_widget.setMaximumWidth(16777215)
            self.side_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            
        super().resizeEvent(event)

class BoggleAppQt(QMainWindow):
    DICE = [
        "ETILAC", "AOTOTT", "AQSFRI", "AUTEDN",
        "IMNQUV", "ABJOOB", "GHRVET", "EGKLUY",
        "ELPISO", "EHINPS", "ENEWVT", "ESINLP",
        "MIDXER", "ADENVZ", "ACDEMP", "BILAFE"
    ]
    TOTAL_GAME_TIME = 180

    def __init__(self, debug=False, force_update=False):
        super().__init__()
        self.debug_mode = debug
        self.force_update = force_update
        
        self.current_grid = []
        self.dictionary = set()
        self.prefixes = set()
        self.found_words = []
        self.extra_words = []
        self.all_valid_words = []
        self.missed_words = []
        self.missed_words_computed = False
        self.final_base_score = 0
        self.extra_score = 0
        
        self.game_in_progress = False
        self.is_paused = False
        self.time_left = self.TOTAL_GAME_TIME
        self.start_time = None
        self.total_pause_duration = 0
        self.last_pause_start = None
        self.pending_focus_out_timer = None
        self.focus_pause_grace_until = 0

        self.setWindowTitle("Boggle (Qt)")
        
        # Déterminer la couleur de fond selon le mode debug
        bg_color = "#E3F2FD" if self.debug_mode else "white"
        
        # Style global pour éviter les textes invisibles et styliser les onglets
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {bg_color}; color: black; }}
            QLineEdit {{ 
                border: 2px solid #ddd; 
                border-radius: 5px; 
                padding: 5px; 
                color: black; 
                background-color: #fcfcfc;
            }}
            QTextEdit {{ 
                border: 1px solid #eee; 
                color: black; 
                background-color: white;
            }}
            QPushButton {{
                background-color: #f8f8f8;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                min-width: 100px;
            }}
            QPushButton:hover {{ background-color: #f0f0f0; }}
            QTabWidget::pane {{ border: 1px solid #eee; }}
            QTabBar::tab {{
                background: #f5f5f5;
                color: #555;
                padding: 8px 20px;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {bg_color};
                color: black;
                font-weight: bold;
                border-bottom: 1px solid {bg_color};
            }}
        """)
        
        self.load_dictionary()
        self.setup_ui()
        self.load_geometry()
        
        # Initialisation DB
        boggle_history.set_db_name(debug=self.debug_mode)
        boggle_history.init_db()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        # Application level event filter for focus
        QApplication.instance().installEventFilter(self)
        
        self.generate_new_game()
        
        # Lancer la vérification des mises à jour après 1 seconde
        QTimer.singleShot(1000, self.check_for_updates)

        if self.debug_mode:
            print("[DEBUG] PySide6 App initialized")

    def check_for_updates(self):
        # Quick check if git is available to avoid system prompts on macOS
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except:
            if self.debug_mode: print("[DEBUG] Git not found. Skipping update check.")
            self.update_status_label.hide()
            return

        config_path = "boggle_config.json"
        now = time.time()
        should_check = self.force_update
        
        if not should_check:
            try:
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                        last_check = config.get("last_update_check", 0)
                        # Check if 24 hours (86400 seconds) have passed
                        if now - last_check > 86400:
                            should_check = True
                else:
                    should_check = True
            except:
                should_check = True

        if not should_check:
            if self.debug_mode: print("[DEBUG] Skipping update check (checked recently).")
            self.update_status_label.hide()
            return

        self.update_status_label.setText("Recherche de mises à jour...")
        self.update_status_label.show()
        QApplication.processEvents()
        
        if self.debug_mode: print("[DEBUG] Checking for updates...")
        
        # Save the time of this check
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f: config = json.load(f)
            config["last_update_check"] = now
            with open(config_path, "w") as f: json.dump(config, f)
        except: pass

        try:
            # Fetch remote without affecting local branch
            subprocess.run(["git", "fetch"], capture_output=True, check=True, timeout=5)
            
            # Compare local HEAD with origin/master
            local_hash = subprocess.check_output(["git", "rev-parse", "@"], encoding='utf-8').strip()
            remote_hash = subprocess.check_output(["git", "rev-parse", "@{u}"], encoding='utf-8').strip()
            
            if local_hash != remote_hash:
                if self.debug_mode: print(f"[DEBUG] Update found! Local: {local_hash[:7]}, Remote: {remote_hash[:7]}")
                self.update_status_label.setText("Mise à jour disponible !")
                self.show_update_dialog()
            else:
                if self.debug_mode: print("[DEBUG] Game is up to date.")
                self.update_status_label.hide()
        except Exception as e:
            if self.debug_mode: print(f"[DEBUG] Update check failed: {e}")
            self.update_status_label.hide()

    def show_update_dialog(self):
        msg = "Une nouvelle version du jeu est disponible sur GitHub.\n\nVoulez-vous mettre à jour (git pull) et redémarrer ?"
        confirm = QMessageBox.question(self, "Mise à jour disponible", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if confirm == QMessageBox.Yes:
            try:
                subprocess.run(["git", "pull"], check=True)
                QMessageBox.information(self, "Mise à jour", "Mise à jour réussie. Le jeu va redémarrer.")
                # Restart the application
                python = sys.executable
                os.execl(python, python, *sys.argv)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec de la mise à jour : {e}")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.ApplicationDeactivate:
            if self.game_in_progress and not self.is_paused:
                if self.pending_focus_out_timer:
                    self.pending_focus_out_timer.stop()
                self.pending_focus_out_timer = QTimer.singleShot(50, self._handle_focus_out_check)
        elif event.type() == QEvent.ApplicationActivate:
            if self.pending_focus_out_timer:
                self.pending_focus_out_timer.stop()
                self.pending_focus_out_timer = None
            if self.game_in_progress and self.is_paused and self.paused_due_to_focus:
                self.toggle_pause(force_state=False)
            self.responsive_container.entry.setFocus()
        return super().eventFilter(obj, event)

    def _handle_focus_out_check(self):
        self.pending_focus_out_timer = None
        if time.time() < self.focus_pause_grace_until:
            return
        if self.game_in_progress and not self.is_paused:
            self.toggle_pause(force_state=True, due_to_focus=True)

    def load_dictionary(self):
        dict_path = "mots_boggle.txt"
        if os.path.exists(dict_path):
            with open(dict_path, "r", encoding="utf-8") as f:
                for line in f:
                    word = remove_accents(line.strip().upper())
                    if len(word) >= 3: 
                        self.dictionary.add(word)
                        for i in range(1, len(word)):
                            self.prefixes.add(word[:i])

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # Onglet Plateau
        self.game_tab = QWidget()
        self.game_layout = QVBoxLayout(self.game_tab)
        
        # Conteneur empilé pour l'overlay de pause
        self.stack = QWidget()
        self.stack_layout = QVBoxLayout(self.stack)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        
        self.responsive_container = ResponsiveContainer()
        self.pause_overlay = PauseOverlay()
        
        # On ajoute les deux widgets. L'overlay sera affiché par dessus si besoin.
        # En Qt, on peut utiliser QStackedWidget ou simplement gérer la visibilité.
        self.stack_layout.addWidget(self.responsive_container)
        self.stack_layout.addWidget(self.pause_overlay)
        self.pause_overlay.hide()
        
        self.game_layout.addWidget(self.stack)
        self.tabs.addTab(self.game_tab, "Plateau")
        
        # Connexions
        self.responsive_container.reset_btn.clicked.connect(self.on_reset_request)
        self.responsive_container.entry.returnPressed.connect(self.validate_word)
        self.responsive_container.entry.textChanged.connect(self.on_text_changed)
        
        # Onglet Progression
        self.stats_tab = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_tab)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_view = boggle_visualizer.StatsWindowQt(game_id=None, debug=self.debug_mode)
        self.stats_layout.addWidget(self.stats_view)
        self.tabs.addTab(self.stats_tab, "Progression")

        # Update status label
        self.update_status_label = QLabel("")
        self.update_status_label.setFont(QFont("Arial", 9))
        self.update_status_label.setStyleSheet("color: #999;")
        self.update_status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.update_status_label)
        self.update_status_label.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.toggle_pause()
        elif event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
            if event.key() == Qt.Key_R:
                self.on_reset_request()
            elif event.key() == Qt.Key_T:
                self.terminate_game()
        super().keyPressEvent(event)

    def toggle_pause(self, force_state=None):
        if not self.game_in_progress: return
        
        new_state = not self.is_paused if force_state is None else force_state
        if new_state == self.is_paused: return

        self.is_paused = new_state
        if self.is_paused:
            self.last_pause_start = time.time()
            self.timer.stop()
            self.responsive_container.hide()
            self.pause_overlay.show()
        else:
            if self.last_pause_start:
                self.total_pause_duration += (time.time() - self.last_pause_start)
                self.last_pause_start = None
            self.pause_overlay.hide()
            self.responsive_container.show()
            self.responsive_container.entry.setFocus()
            self.timer.start(1000)

    def on_text_changed(self, text):
        upper_text = remove_accents(text).upper()
        if text != upper_text:
            cursor_pos = self.responsive_container.entry.cursorPosition()
            self.responsive_container.entry.setText(upper_text)
            self.responsive_container.entry.setCursorPosition(cursor_pos)
            
        if self.debug_mode:
            self.update_debug_colors(upper_text)

    def update_debug_colors(self, word):
        if not word:
            self.responsive_container.entry.setStyleSheet("")
            return
            
        in_grid = self.is_word_in_grid(word)
        in_dict = word in self.dictionary
        
        fg_color = "green" if in_grid else "red"
        bg_color = "#E8F5E9" if in_dict else "#FFEBEE"
        
        self.responsive_container.entry.setStyleSheet(f"QLineEdit {{ border: 2px solid #ddd; border-radius: 5px; padding: 5px; color: {fg_color}; background-color: {bg_color}; }}")

    def on_reset_request(self):
        if self.game_in_progress:
            # On met en pause pendant la question pour être fair-play
            self.toggle_pause(force_state=True)
            confirm = QMessageBox.question(
                self, "Nouveau tirage", 
                "Voulez-vous vraiment abandonner cette partie pour un nouveau tirage ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if confirm == QMessageBox.No:
                self.toggle_pause(force_state=False)
                return
            # Save the interrupted game silently
            self.end_game(interrupted=True, silent=True)
            
        self.generate_new_game()

    def generate_new_game(self):
        self.timer.stop()
        
        # S'assurer que l'interface n'est plus en mode pause
        self.pause_overlay.hide()
        self.responsive_container.show()
        
        random_dice = list(self.DICE)
        random.shuffle(random_dice)
        f_grid = []
        for d in random_dice:
            l = random.choice(d)
            f_grid.append('QU' if l == 'Q' else l)
        
        self.current_grid = [f_grid[i:i+4] for i in range(0, 16, 4)]
        angles = [[random.choice([0, 90, 180, 270]) for _ in range(4)] for _ in range(4)]
        
        self.responsive_container.grid_widget.set_grid(self.current_grid, angles)
        self.found_words = []
        self.extra_words = []
        self.missed_words = []
        self.missed_words_computed = False
        self.final_base_score = 0
        self.extra_score = 0
        
        self.responsive_container.words_display.clear()
        self.responsive_container.stats_display.clear()
        self.responsive_container.stats_label.setText("")
        self.responsive_container.extra_score_label.setText("")
        self.responsive_container.entry.clear()
        
        self.game_in_progress = True
        self.is_paused = False
        self.time_left = self.TOTAL_GAME_TIME
        self.start_time = time.time()
        self.total_pause_duration = 0
        
        self.update_timer_label()
        self.timer.start(1000)
        self.responsive_container.entry.setFocus()

    def update_timer(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.update_timer_label()
        else:
            self.end_game()

    def update_timer_label(self):
        mins, secs = divmod(self.time_left, 60)
        self.responsive_container.timer_label.setText(f"{mins}:{secs:02d}")

    def validate_word(self):
        word = self.responsive_container.entry.text().strip().upper()
        if not word or len(word) < 3:
            self.responsive_container.entry.clear()
            return
            
        added = False
        if self.game_in_progress:
            if word not in self.found_words:
                self.found_words.append(word)
                added = True
        else:
            if word not in self.found_words and word not in self.extra_words:
                self.extra_words.append(word)
                if (word in self.dictionary) and self.is_word_in_grid(word):
                    self.extra_score += self.get_word_score(word)
                    self.responsive_container.stats_label.setText(f"Score final : {self.final_base_score} (+ {self.extra_score} pts)")
                added = True
                
        if added:
            self.refresh_words_display()
            self.responsive_container.words_display.ensureCursorVisible()
            
        self.responsive_container.entry.clear()
        if self.debug_mode:
            self.update_debug_colors("")

    def refresh_words_display(self):
        def get_color_and_pts(w):
            on_grid = self.is_word_in_grid(w)
            in_dict = w in self.dictionary
            if on_grid and in_dict: return "green", self.get_word_score(w)
            if not on_grid: return "red", 0
            return "purple", 0

        all_entries = []
        # Mots trouvés pendant le jeu
        for w in self.found_words:
            if not self.game_in_progress:
                color, pts = get_color_and_pts(w)
                all_entries.append(f'<span style="color:{color}">{w} ({pts})</span>')
            else:
                all_entries.append(f'<span>{w}</span>')
                
        # Mots ajoutés après le jeu
        for w in self.extra_words:
            color, pts = get_color_and_pts(w)
            all_entries.append(f'<span style="color:{color}">{w} ({pts})</span>')
            
        # Mots manqués (seulement en fin de partie)
        if not self.game_in_progress and self.missed_words_computed:
            for w in self.missed_words:
                if w not in self.extra_words:
                    all_entries.append(f'<span style="color:gray">{w} ({self.get_word_score(w)})</span>')

        # Calculer le nombre de colonnes en fonction de la largeur du widget
        width = self.responsive_container.words_display.width()
        num_cols = max(1, width // 120)  # Environ 120px par colonne

        html = "<table width='100%' cellpadding='2'>"
        for i in range(0, len(all_entries), num_cols):
            html += "<tr>"
            for j in range(num_cols):
                if i + j < len(all_entries):
                    html += f"<td width='{int(100/num_cols)}%'>{all_entries[i+j]}</td>"
                else:
                    html += "<td></td>"
            html += "</tr>"
        html += "</table>"
                    
        self.responsive_container.words_display.setHtml(html)

    def update_stats_table(self):
        found_all = set(self.found_words) | set(self.extra_words)
        
        s_len = {}
        for w in self.all_valid_words:
            l = min(len(w), 8)
            if l not in s_len: s_len[l] = [0, 0]
            s_len[l][0] += 1
            if w in found_all: s_len[l][1] += 1
            
        total_p_score = sum(self.get_word_score(w) for w in self.all_valid_words)
        total_p_words = len(self.all_valid_words)
        
        html = f"<b>POTENTIEL GRILLE : {total_p_words} mots, {total_p_score} pts</b><br>"
        html += "<table width='100%' cellpadding='2'>"
        
        sorted_lens = sorted(s_len.keys())
        half = (len(sorted_lens) + 1) // 2
        for i in range(half):
            html += "<tr>"
            for j in [i, i+half]:
                if j < len(sorted_lens):
                    l = sorted_lens[j]
                    total, found = s_len[l]
                    pct = round((found / total * 100)) if total > 0 else 0
                    l_s = f"{l}L" if l < 8 else "8L+"
                    # Déterminer une couleur de fond légère basée sur la longueur
                    bg_color = ["#E3F2FD", "#E8F5E9", "#FFFDE7", "#FCE4EC", "#F3E5F5", "#F5F5F5"][min(j, 5)]
                    html += f"<td style='background-color:{bg_color}; border: 1px solid #ddd;'>"
                    html += f"<b>{l_s}</b> : {found}/{total} ({pct}%)</td>"
                else:
                    html += "<td></td>"
            html += "</tr>"
        html += "</table>"
        
        self.responsive_container.stats_display.setHtml(html)

    def is_word_in_grid(self, word):
        target = []
        i = 0
        while i < len(word):
            if i+1 < len(word) and word[i:i+2] == "QU": target.append("QU"); i += 2
            else: target.append(word[i]); i += 1
        for r in range(4):
            for c in range(4):
                if self.dfs(r, c, target, 0, set()): return True
        return False

    def dfs(self, r, c, target, idx, visited):
        if idx == len(target): return True
        if not (0<=r<4 and 0<=c<4) or (r,c) in visited or self.current_grid[r][c] != target[idx]: return False
        visited.add((r,c))
        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            if self.dfs(r+dr, c+dc, target, idx+1, visited): return True
        visited.remove((r,c))
        return False

    def find_all_possible_words(self):
        found = set()
        for r in range(4):
            for c in range(4):
                self._solve_dfs(r, c, "", set(), found)
        return list(found)

    def _solve_dfs(self, r, c, current_prefix, visited, found):
        if not (0 <= r < 4 and 0 <= c < 4) or (r, c) in visited: return
        letter = self.current_grid[r][c]
        new_prefix = current_prefix + letter
        if new_prefix not in self.dictionary and new_prefix not in self.prefixes: return
        if new_prefix in self.dictionary: found.add(new_prefix)
        visited.add((r, c))
        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            self._solve_dfs(r + dr, c + dc, new_prefix, visited, found)
        visited.remove((r, c))

    def get_word_score(self, word):
        l = len(word)
        if l <= 4: return 1
        if l == 5: return 2
        if l == 6: return 3
        if l == 7: return 5
        return 11

    def terminate_game(self):
        if self.game_in_progress:
            self.time_left = 0
            self.end_game(interrupted=True)

    def update_timer(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.update_timer_label()
        else:
            self.end_game(interrupted=False)

    def update_timer_label(self):
        mins, secs = divmod(self.time_left, 60)
        self.responsive_container.timer_label.setText(f"{mins}:{secs:02d}")

    def end_game(self, interrupted=True, silent=False):
        if self.debug_mode: print(f"[DEBUG] Ending game. Interrupted: {interrupted}, Silent: {silent}")
        self.timer.stop()
        self.game_in_progress = False
        self.calculate_final_results(interrupted=interrupted, silent=silent)

    def calculate_final_results(self, interrupted=False, silent=False):
        self.final_base_score = 0
        for w in self.found_words:
            if (w in self.dictionary) and self.is_word_in_grid(w):
                self.final_base_score += self.get_word_score(w)
                
        if not self.missed_words_computed:
            self.all_valid_words = self.find_all_possible_words()
            self.missed_words = sorted([w for w in self.all_valid_words if w not in self.found_words], key=lambda x: (-len(x), x))
            self.missed_words_computed = True
            
        self.responsive_container.stats_label.setText(f"Score final : {self.final_base_score}")
        self.update_stats_table()
        self.refresh_words_display()
        self.process_stats(interrupted=interrupted, silent=silent)

    def process_stats(self, interrupted=False, silent=False):
        # Calculate playing time
        actual_playing_time = 0
        if self.start_time:
            now = time.time()
            total_duration = now - self.start_time
            effective_pause = self.total_pause_duration
            if self.is_paused and self.last_pause_start:
                effective_pause += (now - self.last_pause_start)
            actual_playing_time = int(total_duration - effective_pause)
            if not interrupted: actual_playing_time = self.TOTAL_GAME_TIME
            else: actual_playing_time = min(actual_playing_time, self.TOTAL_GAME_TIME)

        if self.debug_mode:
            print(f"[DEBUG] Saving game. Score: {self.final_base_score}, Time: {actual_playing_time}s, Finished: {not interrupted}")

        total_possible_score = sum(self.get_word_score(w) for w in self.all_valid_words)
        found_valid = [w for w in self.found_words if (w in self.dictionary) and self.is_word_in_grid(w)]
        
        found_lens = {}
        for w in found_valid:
            l = str(len(w))
            found_lens[l] = found_lens.get(l, 0) + 1
            
        poss_lens = {}
        for w in self.all_valid_words:
            l = str(len(w))
            poss_lens[l] = poss_lens.get(l, 0) + 1
            
        longest_found = max([len(w) for w in found_valid]) if found_valid else 0
        longest_poss = max([len(w) for w in self.all_valid_words]) if self.all_valid_words else 0
        
        data = {
            'score': self.final_base_score,
            'max_score': total_possible_score,
            'words_count': len(found_valid),
            'max_words_count': len(self.all_valid_words),
            'longest_word_found_len': longest_found,
            'longest_word_possible_len': longest_poss,
            'found_lengths': found_lens,
            'possible_lengths': poss_lens,
            'grid_string': "".join("".join(row) for row in self.current_grid),
            'found_words': found_valid,
            'has_paused': self.has_paused_this_game,
            'playing_time': actual_playing_time,
            'is_finished': 1 if not interrupted else 0
        }
        
        game_id = boggle_history.save_game(data)
        boggle_sync.sync_push_async(debug=self.debug_mode)
        
        if silent: return
        
        # Update Stats Tab
        # Remove old widget if any
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        self.stats_view = boggle_visualizer.StatsWindowQt(game_id=game_id, debug=self.debug_mode)
        self.stats_layout.addWidget(self.stats_view)


    def load_geometry(self):
        config_path = "boggle_config_qt.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    pos = config.get("pos", [100, 100])
                    size = config.get("size", [800, 600])
                    self.move(pos[0], pos[1])
                    self.resize(size[0], size[1])
            except:
                self.resize(800, 600)
        else:
            self.resize(800, 600)

    def save_geometry(self):
        config_path = "boggle_config_qt.json"
        try:
            config = {
                "pos": [self.pos().x(), self.pos().y()],
                "size": [self.width(), self.height()]
            }
            with open(config_path, "w") as f:
                json.dump(config, f)
        except:
            pass

    def closeEvent(self, event):
        self.save_geometry()
        
        if self.game_in_progress:
            was_already_paused = self.is_paused
            
            # Force pause to hide board before showing dialog
            if not was_already_paused:
                self.toggle_pause(force_state=True)
            
            confirm = QMessageBox.question(
                self, "Quitter", 
                "Une partie est en cours. Voulez-vous vraiment quitter ?\n(La progression sera sauvegardée comme inachevée)",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if confirm == QMessageBox.Yes:
                self.end_game(interrupted=True, silent=True)
                event.accept()
            else:
                if not was_already_paused:
                    self.toggle_pause(force_state=False)
                # Ensure focus is back to the entry
                QTimer.singleShot(100, self.responsive_container.entry.setFocus)
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    is_debug = "--debug" in sys.argv
    force_update = "--force-update" in sys.argv
    
    app = QApplication(sys.argv)
    
    # Application d'une police par défaut (Arial)
    font = QFont("Arial", 11)
    app.setFont(font)
    
    window = BoggleAppQt(debug=is_debug, force_update=force_update)
    window.show()
    sys.exit(app.exec())
