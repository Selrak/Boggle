$WshShell = New-Object -ComObject WScript.Shell
$StartMenuPath = [System.Environment]::GetFolderPath('StartMenu')
$ProgramsPath = Join-Path $StartMenuPath "Programs"
$Shortcut = $WshShell.CreateShortcut("$ProgramsPath\Boggle.lnk")

# Get path to pythonw.exe
$PythonW = (Get-Command pythonw.exe).Source
$ScriptPath = "C:\Users\cthin\Fun\Boggle\boggle_game.py"
$WorkDir = "C:\Users\cthin\Fun\Boggle"

$Shortcut.TargetPath = $PythonW
$Shortcut.Arguments = "`"$ScriptPath`""
$Shortcut.WorkingDirectory = $WorkDir
$Shortcut.Description = "Jouer au Boggle"
# Optionally use a generic icon if available, or just default pythonw icon
$Shortcut.IconLocation = "shell32.dll, 25"
$Shortcut.Save()

Write-Host "Le raccourci Boggle a été créé dans votre menu Démarrer." -ForegroundColor Green
Write-Host "Vous pouvez maintenant le trouver en cherchant 'Boggle' dans le menu Démarrer." -ForegroundColor Cyan
