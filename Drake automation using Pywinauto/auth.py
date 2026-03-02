import base64
import hashlib
import hmac
import struct
import threading
import time

import win32gui
from pywinauto import Desktop
from pywinauto.application import Application

import config


# TOTP helpers

def get_totp_code(secret_key: str) -> str:
    """Generate a 6-digit TOTP code from the given base32 secret."""
    key = base64.b32decode(secret_key.upper().replace(" ", ""))
    msg = struct.pack(">Q", int(time.time() // 30))
    h   = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code   = struct.unpack(">I", h[offset:offset + 4])[0]
    return str((code & 0x7FFFFFFF) % 1_000_000).zfill(6)


def get_fresh_totp_code(secret_key: str) -> str:
    """Return a TOTP code that has at least 10 seconds remaining on its window."""
    remaining = 30 - int(time.time() % 30)
    if remaining < 10:
        print(f"  [TOTP] Only {remaining}s left, waiting for next window...")
        time.sleep(remaining + 1)
    code      = get_totp_code(secret_key)
    remaining = 30 - int(time.time() % 30)
    print(f"  [TOTP] Fresh code generated with {remaining}s remaining: {code}")
    return code


# Login

def launch_and_login(app: Application) -> object:

    print("[AUTH] Connecting to Drake main window...")
    main_win = Desktop(backend="uia").window(
    title_re=".*Drake 20(23|24) Tax Software.*"
    )
    main_win.wait("visible", timeout=config.WINDOW_TIMEOUT)
    main_win.set_focus()
    print("[AUTH] Main window visible.")

    # Username
    username_box = main_win.child_window(
        auto_id="MainWindow_TextBoxUserName", control_type="Edit"
    )
    username_box.wait("visible", timeout=20)
    username_box.click_input()
    username_box.set_edit_text(config.USERNAME)

    # Password
    password_box = main_win.child_window(
        auto_id="MainWindow_PasswordBoxLoginPassword", control_type="Edit"
    )
    password_box.wait("visible", timeout=5)
    password_box.click_input()
    password_box.type_keys(config.PASSWORD, with_spaces=True)

    # Login button
    login_btn = main_win.child_window(
        auto_id="MainWindow_ButtonLogin", control_type="Button"
    )
    login_btn.wait("visible", timeout=5)
    login_btn.click_input()
    print("[AUTH] Login button clicked.")

    return main_win

# Multi-Factor Authentication

def _wait_for_mfa_hwnd(timeout: int) -> int | None:
    """Poll until the MFA dialog window is visible; return its HWND or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = win32gui.FindWindow(None, "Drake Tax Security 2024")
        if hwnd and win32gui.IsWindowVisible(hwnd):
            return hwnd
        time.sleep(0.3)
    return None


def submit_mfa(max_retries: int = config.MFA_MAX_RETRIES) -> bool:
    """
    Attempt to submit the MFA OTP up to *max_retries* times.
    Returns True on success, False if all attempts fail.
    """
    for attempt in range(1, max_retries + 1):
        print(f"\n[MFA] Attempt {attempt}/{max_retries}")

        # Start generating the TOTP code in the background while we wait
        # for the dialog so we don't waste time.
        code_holder: dict = {}

        def _gen():
            code_holder["code"] = get_fresh_totp_code(config.TOTP_SECRET)

        threading.Thread(target=_gen, daemon=True).start()

        # Wait for the MFA dialog
        print("[MFA] Scanning for MFA dialog...")
        mfa_hwnd = _wait_for_mfa_hwnd(config.MFA_TIMEOUT)
        if not mfa_hwnd:
            raise RuntimeError("[MFA] Dialog not found within timeout!")
        print(f"[MFA] Dialog found (HWND: {mfa_hwnd})")

        # Wait for TOTP code to be ready
        while "code" not in code_holder:
            time.sleep(0.1)
        mfa_code = code_holder["code"]
        print(f"[MFA] Using code: {mfa_code}")

        # Enter OTP
        mfa_app = Application(backend="uia").connect(handle=mfa_hwnd)
        mfa_win = mfa_app.window(handle=mfa_hwnd)

        code_box = mfa_win.child_window(auto_id="1012", control_type="Edit")
        code_box.click_input()
        code_box.set_edit_text("")
        code_box.set_edit_text(mfa_code)

        # Click OK
        ok_btn = mfa_win.child_window(auto_id="1001", control_type="Button")
        ok_btn.click_input()
        print("[MFA] OK clicked — waiting for response...")
        time.sleep(config.MFA_RESPONSE_DELAY)

        # Check whether the dialog is still open (failure case)
        error_hwnd = win32gui.FindWindow(None, "Drake Tax Security 2024")
        if error_hwnd and win32gui.IsWindowVisible(error_hwnd):
            print(f"[MFA] Attempt {attempt} FAILED — OTP invalid or expired.")
            # Dismiss any inner error popup
            try:
                err_app = Application(backend="uia").connect(handle=error_hwnd)
                err_win = err_app.window(handle=error_hwnd)
                err_ok  = err_win.child_window(title="OK", control_type="Button")
                if err_ok.exists():
                    err_ok.click_input()
                    time.sleep(1)
            except Exception:
                pass
            continue

        print("[MFA] MFA submitted successfully!")
        return True

    print("[MFA] All attempts exhausted — login FAILED.")

    return False
