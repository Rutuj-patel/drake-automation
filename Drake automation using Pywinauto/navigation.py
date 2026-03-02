import time

import win32api
import win32con
import win32gui
from pywinauto import keyboard
from pywinauto.application import Application

import config
from window_utils import force_focus


# Search-box navigation

def search_and_open(general_hwnd: int, term: str) -> None:
    """
    Type *term* into Drake's form search box (auto_id="1003") and press Enter.
    Drake will open the matching form.
    """
    force_focus(general_hwnd)
    time.sleep(0.2)

    app    = Application(backend="uia").connect(handle=general_hwnd)
    win    = app.window(handle=general_hwnd)
    search = win.child_window(auto_id="1003", control_type="Edit")
    search.wait("visible", timeout=10)
    search.click_input()
    time.sleep(0.1)

    keyboard.send_keys(f"^a{{DELETE}}{term}{{ENTER}}", pause=0.03)
    time.sleep(config.FORM_OPEN_DELAY)
    print(f"[NAV] Searched '{term}' and pressed Enter")


# Keyboard helpers

def press_page_down(hwnd: int) -> None:
    """Send a Page Down key to *hwnd* (used to advance to next form record)."""
    force_focus(hwnd)
    win32api.keybd_event(win32con.VK_NEXT, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_NEXT, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(config.PGDN_DELAY)


def press_escape(hwnd: int) -> None:
    """Send Escape to *hwnd* (saves & closes the current form in Drake)."""
    force_focus(hwnd)
    win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.5)


# Mouse helper

def click_hwnd(ctrl_hwnd: int) -> None:
    """Click the centre of *ctrl_hwnd* using raw Win32 mouse events."""
    rect = win32gui.GetWindowRect(ctrl_hwnd)
    x    = (rect[0] + rect[2]) // 2
    y    = (rect[1] + rect[3]) // 2
    win32api.SetCursorPos((x, y))
    time.sleep(0.05)
    win32api.mouse_event(0x0002, x, y, 0, 0)   # MOUSEEVENTF_LEFTDOWN
    time.sleep(0.05)
    win32api.mouse_event(0x0004, x, y, 0, 0)   # MOUSEEVENTF_LEFTUP
    time.sleep(0.25)


# Starting-screen helpers

def click_item_detail(start_hm: dict) -> bool:
    """Click the 'Item Detail' button (ctrl 1002) on a form starting screen."""
    item_detail = start_hm.get("1002")
    if not item_detail:
        print("  [NAV] Item Detail button (1002) not found!")
        return False
    click_hwnd(item_detail)
    time.sleep(1.8)
    return True


def save_starting_screen(start_hwnd: int, start_hm: dict) -> None:
    """Click the Save button (ctrl 1007) on a form starting screen."""
    save_ctrl = start_hm.get("1007")
    if save_ctrl:
        force_focus(start_hwnd)
        click_hwnd(save_ctrl)
        print("  [NAV] Starting screen saved.")
    else:
        press_escape(start_hwnd)
        print("  [NAV] Save button not found — closed via ESC.")