import tkinter as tk
from boggle_game import BoggleApp
import capture_helper
import time

def test_missed_words():
    root = tk.Tk()
    app = BoggleApp(root)
    
    # On attend 1 seconde que l'UI soit prête
    root.update()
    time.sleep(1)
    
    # On trouve juste un mot au hasard (bidon) pour le test
    app.found_words = ["TEST"]
    
    # On simule la fin du jeu (Ctrl+T)
    app.terminate_game()
    
    # On laisse le temps au calcul (2-3 sec max) et au rendu
    root.update()
    time.sleep(3) 
    
    capture_helper.capture_window("Boggle", "Validation_Mots_Manquants_Bleus")
    root.destroy()

if __name__ == "__main__":
    test_missed_words()
