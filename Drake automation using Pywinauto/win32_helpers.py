import ctypes

import win32gui

user32 = ctypes.windll.user32

WM_SETTEXT      = 0x000C
WM_COMMAND      = 0x0111
EN_CHANGE       = 0x0300   # Edit-change notification
CBN_SELCHANGE   = 0x0001   # ComboBox selection-change notification
CB_SELECTSTRING = 0x014D   # Select list item by string prefix
CB_SETCURSEL    = 0x014E   # Select list item by index
BM_SETCHECK     = 0x00F1   # Set button (checkbox) state
BM_GETCHECK     = 0x00F0   # Get button (checkbox) state
BST_CHECKED     = 1
BST_UNCHECKED   = 0
BN_CLICKED      = 0        # Button-click notification


# Edit (TextBox)

def we(hm: dict, ctrl_id: str | int, value) -> None:

    if value is None or str(value).strip() == "":
        return

    ctrl_id = str(ctrl_id)
    hwnd    = hm.get(ctrl_id)
    if not hwnd:
        print(f"    [!] Edit   {ctrl_id:>6}  not in map")
        return

    try:
        text = str(value)
        user32.SendMessageW(hwnd, WM_SETTEXT, 0, text)
        parent  = win32gui.GetParent(hwnd)
        cid_int = int(ctrl_id)
        user32.PostMessageW(
            parent, WM_COMMAND,
            (EN_CHANGE << 16) | (cid_int & 0xFFFF),
            hwnd,
        )
        print(f"    [E] {ctrl_id:>6} = {text}")
    except Exception as exc:
        print(f"    [!] Edit   {ctrl_id:>6}  error: {exc}")


# ComboBox

def wc(hm: dict, ctrl_id: str | int, value) -> None:

    if value is None or str(value).strip() == "":
        return

    ctrl_id = str(ctrl_id)
    hwnd    = hm.get(ctrl_id)
    if not hwnd:
        print(f"    [!] Combo  {ctrl_id:>6}  not in map")
        return

    try:
        text    = str(value)
        cls     = win32gui.GetClassName(hwnd)
        cid_int = int(ctrl_id)

        if "ComboBox" in cls or "combo" in cls.lower():
            result = user32.SendMessageW(hwnd, CB_SELECTSTRING, -1, text)
            if result == -1:
                inner  = win32gui.FindWindowEx(hwnd, 0, "Edit", None)
                target = inner if inner else hwnd
                user32.SendMessageW(target, WM_SETTEXT, 0, text)
        else:

            user32.SendMessageW(hwnd, WM_SETTEXT, 0, text)

        parent = win32gui.GetParent(hwnd)
        user32.PostMessageW(
            parent, WM_COMMAND,
            (CBN_SELCHANGE << 16) | (cid_int & 0xFFFF),
            hwnd,
        )
        print(f"    [C] {ctrl_id:>6} = {text}")
    except Exception as exc:
        print(f"    [!] Combo  {ctrl_id:>6}  error: {exc}")


def wc_index(hm: dict, ctrl_id: str | int, index: int) -> None:
    """
    Set a ComboBox by zero-based *index* using CB_SETCURSEL.
    More reliable than text matching when items have unpredictable labels.
    """
    if index is None:
        return

    ctrl_id = str(ctrl_id)
    hwnd    = hm.get(ctrl_id)
    if not hwnd:
        print(f"    [!] Combo  {ctrl_id:>6}  not in map")
        return

    try:
        cid_int = int(ctrl_id)
        user32.SendMessageW(hwnd, CB_SETCURSEL, index, 0)
        parent = win32gui.GetParent(hwnd)
        user32.PostMessageW(
            parent, WM_COMMAND,
            (CBN_SELCHANGE << 16) | (cid_int & 0xFFFF),
            hwnd,
        )
        print(f"    [C] {ctrl_id:>6} = index({index})")
    except Exception as exc:
        print(f"    [!] Combo  {ctrl_id:>6}  index error: {exc}")


# CheckBox

def wx(hm: dict, ctrl_id: str | int, desired: bool) -> None:
    """
    Set a CheckBox to *desired* state.
    Skips (does nothing) when *desired* is False, because the default state
    in Drake is unchecked.
    """
    if not desired:
        return

    ctrl_id = str(ctrl_id)
    hwnd    = hm.get(ctrl_id)
    if not hwnd:
        print(f"    [!] Check  {ctrl_id:>6}  not in map")
        return

    try:
        cid_int = int(ctrl_id)
        current = user32.SendMessageW(hwnd, BM_GETCHECK, 0, 0)
        if (current == BST_CHECKED) != desired:
            user32.SendMessageW(
                hwnd, BM_SETCHECK,
                BST_CHECKED if desired else BST_UNCHECKED, 0,
            )
            parent = win32gui.GetParent(hwnd)
            user32.PostMessageW(
                parent, WM_COMMAND,
                (BN_CLICKED << 16) | (cid_int & 0xFFFF),
                hwnd,
            )
        state = "checked" if desired else "unchecked"
        print(f"    [X] {ctrl_id:>6} = {state}")
    except Exception as exc:
        print(f"    [!] Check  {ctrl_id:>6}  error: {exc}")