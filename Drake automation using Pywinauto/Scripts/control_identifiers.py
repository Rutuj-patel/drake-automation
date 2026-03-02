import win32gui
from pywinauto.application import Application

found = []
def _cb(hwnd, _):
    if not win32gui.IsWindowVisible(hwnd):
        return
    title = win32gui.GetWindowText(hwnd)
    if "Data Entry" in title:
        found.append((hwnd, title))

win32gui.EnumWindows(_cb, None)

if not found:
    print("No Data Entry window found. Open the 1099-DIV form in Drake first.")
else:
    for hwnd, title in found:
        print(f"\nHWND={hwnd}  '{title}'")
        app = Application(backend="uia").connect(handle=hwnd)
        win = app.window(handle=hwnd)
        win.print_control_identifiers()