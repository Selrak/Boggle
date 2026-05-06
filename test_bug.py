import tkinter as tk
from boggle_game import BoggleApp

root = tk.Tk()
app = BoggleApp(root)
app.game_in_progress = True
app.found_words = ["TEST"]
app.calculate_final_results()
print("After calculate_final_results:", repr(app.words_display.get("1.0", tk.END)))
