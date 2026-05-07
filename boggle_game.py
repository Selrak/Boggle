import tkinter as tk
from tkinter import font, messagebox, ttk
import random
import unicodedata
import os
import sys
import json

import boggle_history
import boggle_visualizer
import subprocess

def remove_accents(input_str):
    nksfd = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nksfd if not unicodedata.combining(c)])

import time

class BoggleApp:
    DICE = [
        "ETILAC", "AOTOTT", "AQSFRI", "AUTEDN",
        "IMNQUV", "ABJOOB", "GHRVET", "EGKLUY",
        "ELPISO", "EHINPS", "ENEWVT", "ESINLP",
        "MIDXER", "ADENVZ", "ACDEMP", "BILAFE"
    ]
    TOTAL_GAME_TIME = 180

    def __init__(self, root, debug=False):
        self.root = root
        self.root.title("Boggle")
        self.root.configure(bg="white")
        self.debug_mode = debug
        
        self.main_font = font.Font(family="Arial", size=13)
        self.bold_font = font.Font(family="Arial", size=13, weight="bold")
        self.entry_font = font.Font(family="Arial", size=22)
        self.timer_font = font.Font(family="Arial", size=24, weight="bold")
        self.letter_font = font.Font(family="Arial", size=36, weight="bold")
        
        self.game_in_progress = False
        self.is_paused = False
        self.paused_due_to_focus = False
        self.has_paused_this_game = False
        self.time_left = self.TOTAL_GAME_TIME
        self.start_time = None
        self.total_pause_duration = 0
        self.last_pause_start = None
        self.timer_id = None
        self.scroll_anim_id = None
        
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
        
        self.load_geometry()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.load_dictionary()
        boggle_history.init_db()
        self.setup_ui()
        self.setup_bindings()
        self.generate_new_game()
        self.update_status_label = tk.Label(self.main_frame, text="", font=("Arial", 9), bg="white", fg="#999")
        self.update_status_label.pack(side="bottom", pady=2)
        self.root.after(1000, self.check_for_updates)
        
    def check_for_updates(self):
        self.update_status_label.config(text="Recherche de mises à jour...")
        self.root.update_idletasks()
        if self.debug_mode: print("[DEBUG] Checking for updates...")
        try:
            # Fetch remote without affecting local branch
            subprocess.run(["git", "fetch"], capture_output=True, check=True, timeout=5)
            
            # Compare local HEAD with origin/master
            local_hash = subprocess.check_output(["git", "rev-parse", "@"], encoding='utf-8').strip()
            remote_hash = subprocess.check_output(["git", "rev-parse", "@{u}"], encoding='utf-8').strip()
            
            if local_hash != remote_hash:
                if self.debug_mode: print(f"[DEBUG] Update found! Local: {local_hash[:7]}, Remote: {remote_hash[:7]}")
                self.update_status_label.config(text="Mise à jour disponible !")
                self.show_update_dialog()
            else:
                if self.debug_mode: print("[DEBUG] Game is up to date.")
                self.update_status_label.pack_forget() # Hide if up to date
        except Exception as e:
            if self.debug_mode: print(f"[DEBUG] Update check failed: {e}")
            self.update_status_label.pack_forget()

    def show_update_dialog(self):
        msg = "Une nouvelle version du jeu est disponible sur GitHub.\n\nVoulez-vous mettre à jour (git pull) et redémarrer ?"
        if messagebox.askyesno("Mise à jour disponible", msg, parent=self.root):
            try:
                subprocess.run(["git", "pull"], check=True)
                messagebox.showinfo("Mise à jour", "Mise à jour réussie. Le jeu va redémarrer.")
                # Restart the application
                python = sys.executable
                os.execl(python, python, *sys.argv)
            except Exception as e:
                messagebox.showerror("Erreur", f"Échec de la mise à jour : {e}")

    def load_geometry(self):
        config_path = "boggle_config.txt"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    geom = f.read().strip()
                    if geom: self.root.geometry(geom)
            except: pass

    def on_closing(self):
        if self.game_in_progress:
            was_already_paused = self.is_paused
            
            # Ensure the game is paused before showing the dialog
            if not was_already_paused:
                self.toggle_pause(force_state=True, due_to_focus=False) # Manual pause, not auto-resume focus
            
            confirm = messagebox.askyesno(
                "Quitter", 
                "Une partie est en cours. Voulez-vous vraiment quitter ?\n(La progression sera sauvegardée comme inachevée)",
                default=messagebox.YES,
                parent=self.root
            )
            
            if confirm:
                self.end_game(interrupted=True, silent=True)
                self.root.destroy()
            else:
                # If it wasn't paused before, unpause now
                if not was_already_paused:
                    self.toggle_pause(force_state=False)
                else:
                    # Just ensure focus is restored to allow spacebar unpause
                    self.root.after(100, self.entry.focus_set)
        else:
            try:
                with open("boggle_config.txt", "w", encoding="utf-8") as f:
                    f.write(self.root.geometry())
            except: pass
            self.root.destroy()

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

    def draw_rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")
        
        # TAB 1: JEU
        self.game_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(self.game_tab, text="Plateau")
        
        self.main_frame = tk.Frame(self.game_tab, padx=20, pady=10, bg="white")
        self.main_frame.pack(expand=True, fill="both")

        # Container for everything that should be hidden during pause
        self.board_container = tk.Frame(self.main_frame, bg="white")
        self.board_container.pack(expand=True, fill="both")
        
        self.grid_frame = tk.Frame(self.board_container, bg="white")
        self.grid_frame.pack(pady=5)
        self.cell_canvases = []
        for r in range(4):
            row_canvases = []
            for c in range(4):
                canvas = tk.Canvas(self.grid_frame, width=80, height=80, bg="white", highlightthickness=0)
                canvas.grid(row=r, column=c, padx=5, pady=5)
                self.draw_rounded_rect(canvas, 2, 2, 78, 78, 15, fill="white", outline="black", width=3)
                tid = canvas.create_text(40, 40, text="", font=self.letter_font, fill="black")
                row_canvases.append((canvas, tid))
            self.cell_canvases.append(row_canvases)
            
        self.input_line = tk.Frame(self.board_container, bg="white")
        self.input_line.pack(pady=10, fill="x")
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self.input_line, textvariable=self.entry_var, font=self.entry_font, justify="center", relief="flat", highlightthickness=2, highlightbackground="#ddd", highlightcolor="#999")
        self.entry.pack(side="left", expand=True, fill="x", ipady=8)
        self.time_label = tk.Label(self.input_line, text="3:00", font=self.timer_font, bg="white", width=5, fg="black")
        self.time_label.pack(side="right", padx=10)
        
        self.words_label = tk.Label(self.board_container, text="Mots trouvés", font=self.bold_font, bg="white")
        self.words_label.pack(anchor="w")
        self.words_container = tk.Frame(self.board_container, bg="white", highlightthickness=1, highlightbackground="#eee")
        self.words_container.pack(pady=5, fill="both", expand=True)
        self.words_scroll = tk.Scrollbar(self.words_container)
        self.words_scroll.pack(side="right", fill="y")
        self.words_display = tk.Text(self.words_container, height=6, font=self.main_font, relief="flat", bg="white", yscrollcommand=self.words_scroll.set, spacing1=2, cursor="arrow", wrap="none")
        self.words_display.pack(side="left", fill="both", expand=True)
        self.words_scroll.config(command=self.words_display.yview)
        
        self.words_display.tag_config("valid", foreground="green")
        self.words_display.tag_config("not_on_grid", foreground="red")
        self.words_display.tag_config("not_in_dict", foreground="#9C27B0")
        self.words_display.tag_config("missed", foreground="blue")
        
        self.bottom_frame = tk.Frame(self.board_container, bg="white")
        self.bottom_frame.pack(fill="x", pady=5)

        # Pause Overlay (initially hidden)
        self.pause_frame = tk.Frame(self.main_frame, bg="white")
        self.pause_label = tk.Label(self.pause_frame, text="PAUSE", font=("Arial", 36, "bold"), bg="white", fg="red")
        self.pause_label.pack(expand=True, pady=50)
        tk.Label(self.pause_frame, text="Appuyez sur ESPACE pour reprendre", font=self.main_font, bg="white").pack()
        self.stats_display = tk.Text(self.bottom_frame, height=4, font=("Arial", 11), bg="white", relief="flat", highlightthickness=0)
        self.stats_display.pack(fill="x", pady=5)
        self.stats_display.tag_config("header", font=("Arial", 11, "bold"))
        self.stat_colors = {3: "#E3F2FD", 4: "#E8F5E9", 5: "#FFFDE7", 6: "#FCE4EC", 7: "#F3E5F5", 8: "#F5F5F5"}
        for l, color in self.stat_colors.items(): self.stats_display.tag_config(f"cat_{l}", background=color)

        self.score_line = tk.Frame(self.bottom_frame, bg="white")
        self.score_line.pack(fill="x")
        self.score_label = tk.Label(self.score_line, text="", font=("Arial", 14, "bold"), bg="white")
        self.score_label.pack(side="left")
        self.extra_score_label = tk.Label(self.score_line, text="", font=self.main_font, bg="white", fg="blue")
        self.extra_score_label.pack(side="left", padx=20)
        self.reset_button = tk.Button(self.bottom_frame, text="Nouveau Jeu (Ctrl+R)", command=self.on_reset_request, font=self.main_font, bg="#f8f8f8", relief="flat", padx=15, pady=5, highlightthickness=1, highlightbackground="#ccc")
        self.reset_button.pack(side="right")
        
        # TAB 2: PROGRESSION
        self.stats_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(self.stats_tab, text="Progression")
        self.stats_view = None

        self.words_display.bind("<Configure>", lambda e: self.refresh_words_display())

    def animate_scroll_to_end(self, target=1.0):
        if self.scroll_anim_id: self.root.after_cancel(self.scroll_anim_id)
        current = self.words_display.yview()[1]
        if target - current > 0.001:
            step = (target - current) * 0.2
            self.words_display.yview_moveto(current + step)
            self.scroll_anim_id = self.root.after(20, lambda: self.animate_scroll_to_end(target))

    def setup_bindings(self):
        self.root.bind("<Control-r>", lambda e: self.on_reset_request())
        self.root.bind("<Control-R>", lambda e: self.on_reset_request())
        self.root.bind("<Control-t>", lambda e: self.terminate_game())
        self.root.bind("<Control-T>", lambda e: self.terminate_game())
        self.root.bind("<space>", self.toggle_pause)
        self.entry.bind("<Return>", self.validate_word)
        self.entry.bind("<KeyPress>", self.on_key_press)
        
        # Focus events for auto-pause/resume
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.root.bind("<FocusIn>", self.on_focus_in)

    def on_focus_out(self, event):
        # Only auto-pause if the event is for the main window
        if event.widget == self.root and self.game_in_progress and not self.is_paused:
            self.toggle_pause(force_state=True, due_to_focus=True)

    def on_focus_in(self, event):
        if event.widget == self.root:
            self.entry.focus_set()
            if self.game_in_progress and self.is_paused and self.paused_due_to_focus:
                self.toggle_pause(force_state=False)

    def toggle_pause(self, event=None, force_state=None, due_to_focus=False):
        if not self.game_in_progress: return
        
        new_state = not self.is_paused if force_state is None else force_state
        if new_state == self.is_paused: return # Already in desired state

        self.is_paused = new_state
        if self.is_paused:
            if self.debug_mode: print(f"[DEBUG] Pausing game. Due to focus: {due_to_focus}")
            self.has_paused_this_game = True
            self.paused_due_to_focus = due_to_focus
            self.last_pause_start = time.time()
            if self.timer_id: self.root.after_cancel(self.timer_id); self.timer_id = None
            self.board_container.pack_forget()
            self.pause_frame.pack(expand=True, fill="both")
        else:
            if self.debug_mode: print("[DEBUG] Resuming game")
            self.paused_due_to_focus = False
            if self.last_pause_start:
                self.total_pause_duration += (time.time() - self.last_pause_start)
                self.last_pause_start = None
            self.pause_frame.pack_forget()
            self.board_container.pack(expand=True, fill="both")
            # Force focus back to entry so keyboard events work
            self.root.after(10, self.entry.focus_set)
            self.update_timer()

    def on_key_press(self, event):
        if event.state & 4: return
        if event.keysym in ("Escape", "BackSpace", "Left", "Right", "Delete", "Up", "Down", "Home", "End", "Tab", "Return"): return
        if event.char and event.char.isprintable():
            c = remove_accents(event.char).upper()
            try: self.entry.delete("sel.first", "sel.last")
            except: pass
            self.entry.insert(tk.INSERT, c)
            if self.debug_mode: self.update_debug_colors(self.entry_var.get())
            return "break"

    def refresh_words_display(self):
        self.words_display.config(state="normal")
        curr_scroll = self.words_display.yview()[0]
        self.words_display.delete("1.0", tk.END)
        col_px = 150; num_cols = max(1, self.words_display.winfo_width() // col_px)
        self.words_display.config(tabs=[col_px * i for i in range(1, num_cols + 1)])
        
        all_entries = []
        def get_tag_and_pts(w):
            on_grid = self.is_word_in_grid(w); in_dict = w in self.dictionary
            if on_grid and in_dict: return "valid", self.get_word_score(w)
            if not on_grid: return "not_on_grid", 0
            return "not_in_dict", 0

        for w in self.found_words:
            if not self.game_in_progress:
                t, p = get_tag_and_pts(w); all_entries.append((f"{w} ({p})", t))
            else: all_entries.append((w, None))
        for w in self.extra_words:
            t, p = get_tag_and_pts(w); all_entries.append((f"{w} ({p})", t))
        if not self.game_in_progress and hasattr(self, 'missed_words'):
            for w in self.missed_words:
                if w not in self.extra_words: all_entries.append((f"{w} ({self.get_word_score(w)})", "missed"))
        
        for i in range(0, len(all_entries), num_cols):
            line = all_entries[i:i+num_cols]
            for idx, (text, tag) in enumerate(line):
                self.words_display.insert(tk.END, text, tag)
                if idx < len(line) - 1: self.words_display.insert(tk.END, "\t")
            self.words_display.insert(tk.END, "\n")
        self.words_display.yview_moveto(curr_scroll)
        self.words_display.config(state="disabled")

    def validate_word(self, event=None):
        word = self.entry_var.get().strip().upper()
        if not word or len(word) < 3: self.entry_var.set(""); return "break"
        added = False
        if self.game_in_progress:
            if word not in self.found_words: self.found_words.append(word); added = True
        else:
            if word not in self.found_words and word not in self.extra_words:
                self.extra_words.append(word)
                if (word in self.dictionary) and self.is_word_in_grid(word):
                    self.extra_score += self.get_word_score(word)
                    self.extra_score_label.config(text=f"+ {self.extra_score} pts")
                    if self.missed_words_computed: self.update_stats_table()
                added = True
        if added:
            self.refresh_words_display()
            self.animate_scroll_to_end()
        self.entry_var.set("")
        if self.debug_mode: self.update_debug_colors("")
        return "break"

    def update_stats_table(self):
        self.stats_display.config(state="normal"); self.stats_display.delete("1.0", tk.END)
        # Use fixed larger tabs for Arial 11
        self.stats_display.config(tabs=[140, 280, 420, 560])
        found_all = set(self.found_words) | set(self.extra_words)
        
        s_len = {}
        for w in self.all_valid_words:
            l = min(len(w), 8)
            if l not in s_len: s_len[l] = [0, 0]
            s_len[l][0] += 1
            if w in found_all: s_len[l][1] += 1
            
        total_p_score = sum(self.get_word_score(w) for w in self.all_valid_words)
        total_p_words = len(self.all_valid_words)
        
        self.stats_display.insert(tk.END, f"POTENTIEL GRILLE : {total_p_words} mots, {total_p_score} pts\n", "header")
        
        sorted_lens = sorted(s_len.keys())
        half = (len(sorted_lens) + 1) // 2
        for i in range(half):
            for j in [i, i+half]:
                if j < len(sorted_lens):
                    l = sorted_lens[j]
                    total, found = s_len[l]
                    pct = round((found / total * 100)) if total > 0 else 0
                    l_s = f"{l}L" if l < 8 else "8L+"
                    display_text = f" {l_s} : {found}/{total} ({pct}%)"
                    self.stats_display.insert(tk.END, f"{display_text}\t", f"cat_{l}")
            self.stats_display.insert(tk.END, "\n")
        self.stats_display.config(state="disabled")

    def find_all_possible_words(self):
        found = set()
        for r in range(4):
            for c in range(4): self._solve_dfs(r, c, "", set(), found)
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

    def terminate_game(self):
        if self.game_in_progress:
            self.time_left = 0
            if self.timer_id: self.root.after_cancel(self.timer_id); self.timer_id = None
            self.time_label.config(text="0:00"); self.end_game()

    def update_timer(self):
        if self.time_left > 0:
            self.time_left -= 1; mins, secs = divmod(self.time_left, 60)
            self.time_label.config(text=f"{mins}:{secs:02d}")
            self.timer_id = self.root.after(1000, self.update_timer)
        else: self.end_game(interrupted=False)

    def end_game(self, interrupted=True, silent=False): 
        if self.debug_mode: print(f"[DEBUG] Ending game. Interrupted: {interrupted}, Silent: {silent}")
        self.game_in_progress = False; 
        self.calculate_final_results(interrupted=interrupted, silent=silent)

    def calculate_final_results(self, interrupted=False, silent=False):
        self.final_base_score = 0
        for w in self.found_words:
            if (w in self.dictionary) and self.is_word_in_grid(w): self.final_base_score += self.get_word_score(w)
        if not self.missed_words_computed:
            self.all_valid_words = self.find_all_possible_words()
            self.missed_words = sorted([w for w in self.all_valid_words if w not in self.found_words], key=lambda x: (-len(x), x))
            self.missed_words_computed = True; self.update_stats_table()
        self.refresh_words_display(); self.score_label.config(text=f"Score final : {self.final_base_score}")
        self.process_stats(interrupted=interrupted, silent=silent)

    def process_stats(self, interrupted=False, silent=False):
        # Calculate playing time
        actual_playing_time = 0
        if self.start_time:
            now = time.time()
            total_duration = now - self.start_time
            # If paused right now, don't count the current pause in playing time
            effective_pause = self.total_pause_duration
            if self.is_paused and self.last_pause_start:
                effective_pause += (now - self.last_pause_start)
            actual_playing_time = int(total_duration - effective_pause)
            # Cap it at TOTAL_GAME_TIME just in case of slight timing drift
            if not interrupted: actual_playing_time = self.TOTAL_GAME_TIME
            else: actual_playing_time = min(actual_playing_time, self.TOTAL_GAME_TIME)

        if self.debug_mode:
            print(f"[DEBUG] Saving game. Score: {self.final_base_score}, Time: {actual_playing_time}s, Finished: {not interrupted}")

        # Prepare data for history
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
        
        if silent: return

        # Update Stats Tab
        for widget in self.stats_tab.winfo_children(): widget.destroy()
        self.stats_view = boggle_visualizer.show_stats(self.stats_tab, game_id, is_embedded=True)

    def on_reset_request(self):
        if hasattr(self, 'confirm_win') and self.confirm_win.winfo_exists(): self.confirm_win.focus_force(); return
        self.show_confirmation()

    def show_confirmation(self):
        self.confirm_win = tk.Toplevel(self.root); self.confirm_win.title("Confirmation"); self.confirm_win.configure(bg="white")
        w, h = 450, 160; x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (w // 2); y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (h // 2)
        self.confirm_win.geometry(f"{w}x{h}+{x}+{y}"); self.confirm_win.transient(self.root); self.confirm_win.grab_set()
        tk.Label(self.confirm_win, text="Nouveau tirage ?", bg="white", font=self.main_font).pack(pady=20)
        btns = tk.Frame(self.confirm_win, bg="white"); btns.pack()
        tk.Button(btns, text="Oui (Ctrl+R)", command=self.confirm_reset, bg="#f0f0f0", relief="flat", font=self.main_font, width=15).pack(side="left", padx=15)
        tk.Button(btns, text="Non (Echap)", command=self.cancel_reset, bg="#f0f0f0", relief="flat", font=self.main_font, width=15).pack(side="left", padx=15)
        self.confirm_win.bind("<Control-r>", lambda e: self.confirm_reset()); self.confirm_win.bind("<Control-R>", lambda e: self.confirm_reset()); self.confirm_win.bind("<Escape>", lambda e: self.cancel_reset()); self.confirm_win.focus_force()

    def confirm_reset(self): 
        if self.game_in_progress:
            self.end_game(interrupted=True)
        self.confirm_win.destroy(); self.generate_new_game()
    def cancel_reset(self): self.confirm_win.destroy()

    def generate_new_game(self):
        if self.timer_id: self.root.after_cancel(self.timer_id)
        random_dice = list(self.DICE); random.shuffle(random_dice); f_grid = []
        for d in random_dice: l = random.choice(d); f_grid.append('QU' if l == 'Q' else l)
        self.current_grid = [f_grid[i:i+4] for i in range(0, 16, 4)]
        for r in range(4):
            for c in range(4):
                canv, tid = self.cell_canvases[r][c]
                canv.itemconfig(tid, text=self.current_grid[r][c], angle=random.choice([0, 90, 180, 270]))
        self.game_in_progress = True; self.is_paused = False; self.paused_due_to_focus = False; self.has_paused_this_game = False; 
        self.time_left = self.TOTAL_GAME_TIME; self.found_words = []; self.extra_words = []
        self.start_time = time.time(); self.total_pause_duration = 0; self.last_pause_start = None
        self.missed_words = []; self.missed_words_computed = False; self.final_base_score = 0; self.extra_score = 0
        self.entry_var.set(""); self.entry.config(state="normal"); self.entry.focus_set()
        self.stats_display.config(state="normal"); self.stats_display.delete("1.0", tk.END); self.stats_display.config(state="disabled")
        self.refresh_words_display(); self.score_label.config(text=""); self.extra_score_label.config(text=""); self.update_timer()

    def update_debug_colors(self, word):
        if not word: self.entry.config(fg="black", bg="white"); return
        in_grid = self.is_word_in_grid(word); in_dict = word in self.dictionary
        self.entry.config(fg="green" if in_grid else "red", bg="#E8F5E9" if in_dict else "#FFEBEE")

if __name__ == "__main__":
    is_debug = "--debug" in sys.argv
    if is_debug:
        print("[DEBUG] Running in debug mode")
    
    boggle_history.set_db_name(debug=is_debug)
    boggle_history.init_db()

    root = tk.Tk()
    app = BoggleApp(root, debug=is_debug)
    root.mainloop()
