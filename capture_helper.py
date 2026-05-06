import ctypes
import os
import sys
from PIL import Image
import win32gui
import win32ui
import win32con

def capture_window(window_title, description):
    # Trouver le handle
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        def callback(h, hwnds):
            if window_title in win32gui.GetWindowText(h):
                hwnds.append(h)
            return True
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        if hwnds: hwnd = hwnds[0]
        else: return False

    # Obtenir dimensions
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    w, h = right - left, bot - top

    # Contexte graphique
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    # Appel direct via ctypes
    user32 = ctypes.windll.user32
    result = user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2) # PW_RENDERFULLCONTENT

    # Conversion en Image PIL
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

    # Sauvegarde incrémentale
    if not os.path.exists("screenshots"): os.makedirs("screenshots")
    existing = [f for f in os.listdir("screenshots") if f.endswith(".png")]
    idx = len(existing) + 1
    filepath = os.path.join("screenshots", f"{idx:03d}_{description.replace(' ', '_')}.png")
    
    if result == 1:
        im.save(filepath)
        print(f"Capture enregistrée : {filepath}")
        return filepath
    
    # Nettoyage
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        capture_window("Boggle", sys.argv[1])
    else:
        print("Usage: python capture_helper.py 'description'")
