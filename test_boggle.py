import tkinter as tk
from boggle_game import BoggleApp

def run_automated_test():
    root = tk.Tk()
    root.withdraw() # Cacher la fenêtre
    
    app = BoggleApp(root)
    
    # Imposer la grille
    grid_data = [
        ['E', 'R', 'Z', 'N'],
        ['N', 'S', 'T', 'A'],
        ['I', 'I', 'E', 'S'],
        ['I', 'B', 'R', 'C']
    ]
    app.current_grid = grid_data
    for r in range(4):
        for c in range(4):
            canvas, tid = app.cell_canvases[r][c]
            canvas.itemconfig(tid, text=grid_data[r][c])
            
    # Arrêter le timer réel pour le test
    if app.timer_id:
        root.after_cancel(app.timer_id)
        app.timer_id = None

    words_to_test = [
        "BIT", "BEATS", "RIE", "NIES", "TIRE", "BITS", "ETRE", "RIES", 
        "NIER", "TIRS", "BITE", "ETRES", "RIS", "CET", "TIRES", "BITES", 
        "ATRE", "RITE", "INERTE", "TER", "BITER", "ATRES", "RITES", 
        "INERTES", "SERIN", "RESTE", "REITRE", "BISE", "SIR", "SERINS", 
        "RESTER", "REITRES", "BISES", "SIRE", "CRETIN", "BER", "SEC", 
        "RENIE", "SITE", "CRETINS", "BERS", "CES", "RENIES", "SITES", 
        "CRETINE", "BEA", "TES", "RENIER", "BITA", "CRETINES", "BEAS", 
        "SET", "NIET", "BITAS", "BEAT", "RESTA", "NIE", "TIR"
    ]
    
    for w in words_to_test:
        app.entry_var.set(w)
        app.validate_word()
        
    # Mots invalides
    invalid_words = ["GENERIQUE", "FERME", "CRASSE"]
    for w in invalid_words:
        app.entry_var.set(w)
        app.validate_word()
        
    # Calculer les résultats
    app.calculate_final_results()
    
    # Vérification du score
    # Score attendu : 112
    score_text = app.score_label.cget("text")
    score = int(score_text.split(":")[-1].strip())
    
    if score == 112:
        print("TEST_SUCCESS")
    else:
        print(f"TEST_FAILURE: Score obtained {score} instead of 112")
    
    root.destroy()

if __name__ == "__main__":
    run_automated_test()
