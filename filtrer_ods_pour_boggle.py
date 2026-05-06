import os
import unicodedata

# Chemins vers tes fichiers
DOSSIER = r"C:\Users\cthin\Fun\Boggle"
FICHIER_ENTREE = os.path.join(DOSSIER, "mots_ODS_2021.txt")
FICHIER_SORTIE = os.path.join(DOSSIER, "mots_boggle.txt")

def nettoyer_mot(mot):
    # Enlever les accents au cas où
    mot = ''.join(c for c in unicodedata.normalize('NFD', mot)
                  if unicodedata.category(c) != 'Mn')
    return mot.upper().strip()

def preparer_dictionnaire():
    print(f"Lecture de {FICHIER_ENTREE}...")
    
    mots_gardes = 0
    mots_rejetes = 0
    
    try:
        with open(FICHIER_ENTREE, 'r', encoding='utf-8') as f_in, \
             open(FICHIER_SORTIE, 'w', encoding='utf-8') as f_out:
            
            for ligne in f_in:
                mot = nettoyer_mot(ligne)
                
                # Filtre : au moins 3 lettres ET uniquement des lettres de A à Z
                if len(mot) >= 3 and mot.isalpha():
                    f_out.write(mot + '\n')
                    mots_gardes += 1
                else:
                    mots_rejetes += 1
                    
        print("\n--- RÉSULTATS DU NETTOYAGE ---")
        print(f"Mots conservés (>= 3 lettres) : {mots_gardes}")
        print(f"Mots rejetés (< 3 lettres)    : {mots_rejetes}")
        print(f"Fichier généré                : {FICHIER_SORTIE}")
        print("\n=> Pense à utiliser 'mots_boggle.txt' dans ton script principal !")

    except FileNotFoundError:
        print(f"Erreur : Le fichier {FICHIER_ENTREE} est introuvable.")

if __name__ == '__main__':
    preparer_dictionnaire()