import time

import win32con
import win32gui
from pywinauto.application import Application

import config



def get_data_entry_hwnd() -> int | None:
    found = []

    def _cb(hwnd, _):
        title = win32gui.GetWindowText(hwnd)
        if "DRAKE 2024 - Data Entry" in title and win32gui.IsWindowVisible(hwnd):
            found.append(hwnd)

    win32gui.EnumWindows(_cb, None)
    return found[0] if found else None


def wait_for_data_entry(timeout: int = config.FORM_TIMEOUT) -> int | None:

    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = get_data_entry_hwnd()
        if hwnd:
            return hwnd
        time.sleep(0.15)
    return None


def find_window_with_controls(
    ctrl_ids: list[str],
    timeout: int = config.SEARCH_TIMEOUT,
    label: str = "window",
) -> tuple[int | None, dict]:

    print(f"  [WIN] Waiting for {label}", end="", flush=True)
    deadline = time.time() + timeout

    while time.time() < deadline:
        tops: list[int] = []
        win32gui.EnumWindows(lambda h, _: tops.append(h), None)

        for hwnd in tops:
            if not win32gui.IsWindowVisible(hwnd):
                continue
            hm = build_hwnd_map(hwnd)
            if all(c in hm for c in ctrl_ids):
                title = win32gui.GetWindowText(hwnd)
                print(f"\n  [WIN] Found {label}: HWND={hwnd}  title='{title}'  "
                      f"controls={len(hm)}")
                return hwnd, hm

        print(".", end="", flush=True)
        time.sleep(0.15)

    print(f"\n  [WIN] TIMEOUT — {label} not found")
    return None, {}


def wait_for_popup(title: str, timeout: int = 15) -> int | None:

    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = win32gui.FindWindow(None, title)
        if hwnd and win32gui.IsWindowVisible(hwnd):
            return hwnd
        time.sleep(0.3)
    return None




def build_hwnd_map(parent_hwnd: int) -> dict:

    mapping: dict = {}

    def _cb(hwnd, _):
        cid = win32gui.GetDlgCtrlID(hwnd)
        if cid > 0:
            mapping[str(cid)] = hwnd
        return True

    try:
        win32gui.EnumChildWindows(parent_hwnd, _cb, None)
    except Exception:
        pass
    return mapping


# Focus / activation

def force_focus(hwnd: int) -> None:
    """Restore and bring a window to the foreground."""
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.1)


# UIA wrapper helper

def get_uia_window(hwnd: int):
    """Return a pywinauto UIA window wrapper for the given HWND."""
    app = Application(backend="uia").connect(handle=hwnd)
    return app.window(handle=hwnd)