import tkinter as tk
from boggle_game import BoggleApp
import capture_helper
import time

def test_columns():
    root = tk.Tk()
    app = BoggleApp(root)
    
    # Remplir la liste avec suffisamment de mots pour forcer plusieurs colonnes
    test_words = [
        "CHAT", "CHIEN", "MAISON", "VOITURE", "ARBRE", "SOLEIL", "LUNE", "ETOILE", 
        "POMME", "POIRE", "BANANE", "FRAISE", "ORANGE", "CERISE", "RAISIN", "PRUNE",
        "TABLE", "CHAISE", "LIT", "CANAPE", "PORTE", "FENETRE", "MUR", "PLAFOND",
        "ROUGE", "VERT", "BLEU", "JAUNE", "NOIR", "BLANC", "GRIS", "ROSE",
        "PAPIER", "CRAYON", "STYLO", "GOMME", "REGLE", "CAHIER", "LIVRE", "SAC"
    ]
    
    app.game_in_progress = True
    app.found_words = test_words
    
    # Forcer le rafraîchissement de l'affichage
    app.refresh_words_display()
    
    # Mettre à jour l'interface graphique pour que le rendu soit effectif
    root.update()
    time.sleep(1) # Laisser un peu de temps au rendu
    
    # Prendre la capture d'écran
    capture_helper.capture_window("Boggle", "Validation_MultiColonnes")
    
    root.destroy()

if __name__ == "__main__":
    test_columns()
