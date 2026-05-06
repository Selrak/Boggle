param (
    [Parameter(Mandatory=$true)]
    [string]$Grid
)

# Chemin vers le dossier contenant vos scripts
$ScriptDir = "C:\Users\cthin\Fun\Boggle"
$PythonScript = Join-Path $ScriptDir "boggle_solver_gdoc.py"

if ($Grid.Length -ne 16) {
    Write-Host "Erreur : La grille doit contenir exactement 16 lettres." -ForegroundColor Red
    exit
}

Write-Host "Recherche des solutions pour la grille : $Grid..." -ForegroundColor Cyan

# Appel du script Python
python $PythonScript $Grid

Write-Host "Traitement terminé." -ForegroundColor Green