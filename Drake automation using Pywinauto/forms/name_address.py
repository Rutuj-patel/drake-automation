import time

import win32gui
from pywinauto import keyboard
from pywinauto.application import Application

from navigation import press_escape
from win32_helpers import wc, we, wx
from window_utils import build_hwnd_map, force_focus, wait_for_popup


# ── Open / Create return ──────────────────────────────────────────────────────

def open_or_create_return(main_win, ssn: str, data: dict) -> None:
    """
    Click Open/Create, enter SSN, click OK.
    Handles both cases:
      • New return  — 'Open Return' popup → click Yes → fill name fields
      • Existing    — Data Entry window opens directly, nothing extra needed
    """
    # Click the Open/Create toolbar item
    main_win.child_window(
        title="Open/Create",
        auto_id="MainWindow_TextBlockToolbarOpenCreate",
        control_type="Text",
    ).click_input()

    # Enter SSN
    ssn_input = main_win.child_window(
        auto_id="ClearableWatermarkTextbox_TextBoxInput", control_type="Edit"
    )
    ssn_input.click_input()
    ssn_input.type_keys("^a{BACKSPACE}")
    ssn_input.type_keys(ssn, with_spaces=True)

    # Click OK
    main_win.child_window(
        title="OK",
        auto_id="FileOpenCreateWindow_ButtonOK",
        control_type="Button",
    ).click_input()

    # ── Popup handling ────────────────────────────────────────────────────────
    print("[RETURN] Looking for 'Open Return' popup...")
    popup_hwnd = wait_for_popup("Drake - Open Return", timeout=15)

    # Try both Drake 2023 and 2024 popup titles
    if not popup_hwnd:
        popup_hwnd = wait_for_popup("Drake 2024 - Open Return", timeout=5)
    if not popup_hwnd:
        popup_hwnd = wait_for_popup("Drake 2023 - Open Return", timeout=5)

    if popup_hwnd:
        print(f"[RETURN] New-return popup found (HWND: {popup_hwnd})")
        popup_app = Application(backend="uia").connect(handle=popup_hwnd)
        popup_win = popup_app.window(handle=popup_hwnd)
        popup_win.child_window(title="Yes", control_type="Button").click_input()
        print("[RETURN] Clicked Yes — waiting for Create Return window...")
        time.sleep(1.5)
        _fill_create_return_form(main_win, data)
    else:
        print("[RETURN] No popup — existing return opened directly.")


def _fill_create_return_form(main_win, data: dict) -> None:
    """
    Fill First / Middle / Last name on the Create Return dialog.
    Uses UIA because this dialog has reliable named auto_ids.
    """
    s1 = data["client_basic_details"]["section_1"]

    fields = [
        ("CreateReturnWindow_TextBoxFirstName",    s1.get("first_name", "")),
        ("CreateReturnWindow_TextBoxMiddleInitial", s1.get("middle_initial", "")),
        ("CreateReturnWindow_TextBoxLastName",      s1.get("last_name", "")),
    ]

    for auto_id, value in fields:
        box = main_win.child_window(auto_id=auto_id, control_type="Edit")
        box.click_input()
        box.type_keys("^a{BACKSPACE}")
        box.type_keys(value, with_spaces=True)

    # Enter confirms the dialog
    main_win.child_window(
        auto_id="CreateReturnWindow_TextBoxLastName", control_type="Edit"
    ).type_keys("{ENTER}")

    print("[RETURN] Create Return name fields filled.")


# ── Name and Address form — main entry point ──────────────────────────────────

def fill_name_and_address(data_entry_hwnd: int, data: dict) -> None:
    """
    Full Name & Address form fill using pure Win32 — no coordinates anywhere.

    Flow:
      1. Use search box (auto_id="1003") to navigate to Name & Address
      2. Find the form window
      3. Build ctrl_id → hwnd map
      4. Fill Taxpayer / Spouse / Address / Resident sections via we() wc() wx()
      5. Press ESC to save
      6. Dismiss post-save popup
    """
    force_focus(data_entry_hwnd)
    time.sleep(0.3)

    # [1] Navigate via search box — more reliable than UIA nav link click
    # The search box always has auto_id="1003" in Drake Data Entry window
    _navigate_via_search(data_entry_hwnd, "1")   # "1" = Name and Address shortcode
    time.sleep(1.5)

    # [2] Find the form window — works for both Drake 2023 and 2024
    form_hwnd = _find_name_form(timeout=15)
    if not form_hwnd:
        print("[NAME] Name & Address window not found — skipping.")
        return

    force_focus(form_hwnd)
    time.sleep(0.3)

    # [3] Build Win32 control map  →  { "15001": hwnd, "15002": hwnd, ... }
    hm = build_hwnd_map(form_hwnd)
    print(f"[NAME] {len(hm)} controls mapped")

    if len(hm) < 5:
        print("[NAME] Too few controls — window may not have loaded yet, retrying...")
        time.sleep(1.5)
        hm = build_hwnd_map(form_hwnd)
        print(f"[NAME] Retry: {len(hm)} controls mapped")

    # [4] Fill sections
    print("[NAME] Filling Taxpayer...")
    _fill_taxpayer(hm, data)

    print("[NAME] Filling Spouse...")
    _fill_spouse(hm, data)

    print("[NAME] Filling Mailing Address...")
    _fill_mailing_address(hm, data)

    print("[NAME] Filling Resident State...")
    _fill_resident(hm, data)

    # [5] ESC = save in Drake
    press_escape(form_hwnd)

    # [6] Dismiss post-save popup
    _handle_post_name_popup()


# ── Search box navigation helper ──────────────────────────────────────────────

def _navigate_via_search(data_entry_hwnd: int, term: str) -> None:
    """
    Type into the Drake search/shortcode box (auto_id="1003") and press Enter.
    Works for both Drake 2023 and Drake 2024.
    """
    try:
        app = Application(backend="uia").connect(handle=data_entry_hwnd)
        win = app.window(handle=data_entry_hwnd)
        search = win.child_window(auto_id="1003", control_type="Edit")
        search.wait("visible", timeout=10)
        search.click_input()
        time.sleep(0.1)
        keyboard.send_keys(f"^a{{DELETE}}{term}{{ENTER}}", pause=0.03)
        print(f"[NAME] Navigated via search box: '{term}'")
    except Exception as exc:
        print(f"[NAME] Search box navigation failed ({exc}) — trying UIA nav link...")
        # Fallback: try UIA nav link click (Drake 2024 style)
        try:
            app = Application(backend="uia").connect(handle=data_entry_hwnd)
            win = app.window(handle=data_entry_hwnd)
            win.child_window(
                title="Name and Address", auto_id="2002", control_type="Text"
            ).click_input()
            print("[NAME] Navigated via UIA nav link.")
        except Exception as exc2:
            print(f"[NAME] UIA nav link also failed ({exc2}) — proceeding anyway.")


# ── Window finder ─────────────────────────────────────────────────────────────

def _find_name_form(timeout: int = 15) -> int | None:
    """
    Poll until a visible Drake Data Entry window appears that contains
    the Name & Address controls (15001 = Filing Status combo is always present).
    Works for both 'DRAKE 2023 - Data Entry' and 'DRAKE 2024 - Data Entry'.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = []

        def _cb(hwnd, _):
            title = win32gui.GetWindowText(hwnd)
            # Match any Drake year — "DRAKE 20" covers 2023, 2024, 2025...
            if "DRAKE 20" in title and "Data Entry" in title \
                    and win32gui.IsWindowVisible(hwnd):
                found.append(hwnd)

        win32gui.EnumWindows(_cb, None)

        # Among all Data Entry windows, find the one with Name & Address controls
        # (15001 = Filing Status is a reliable anchor control on this form)
        for hwnd in found:
            from window_utils import build_hwnd_map as _bm
            hm = _bm(hwnd)
            # Name & Address has both 15001 (filing status) and 15003 (first name)
            if "15001" in hm and "15003" in hm:
                print(f"[NAME] Form window found (HWND: {hwnd})")
                return hwnd

        # If only one Data Entry window and no anchor check passes yet, return it
        if len(found) == 1:
            print(f"[NAME] Single Data Entry window found (HWND: {found[0]}) — using it")
            return found[0]

        time.sleep(0.3)
    return None


# ── Section fillers ───────────────────────────────────────────────────────────

def _fill_taxpayer(hm: dict, data: dict) -> None:
    s1      = data["client_basic_details"]["section_1"]
    s2      = data["client_basic_details"]["section_2"]
    contact = data["client_basic_details"].get("contact", {})

    # Filing status
    wc(hm, "15001", s2.get("filing_status", ""))

    # 15002 SSN, 15003 First Name, 15005 Last Name — pre-filled at create step
    print("    [SKIP] 15002 SSN       — pre-filled")
    print("    [SKIP] 15003 FirstName — pre-filled")
    print("    [SKIP] 15005 LastName  — pre-filled")

    # Middle initial & suffix
    we(hm, "15004", s1.get("middle_initial", ""))
    wc(hm, "15006", s2.get("suffix", ""))

    # Dates — remove separators, Drake expects MMDDYYYY
    we(hm, "15007", s2.get("date_of_birth",  "").replace("-", "").replace("/", ""))
    we(hm, "15008", s2.get("date_of_death",  "").replace("-", "").replace("/", ""))

    # Occupation
    we(hm, "15009", s2.get("occupation", ""))

    # Phone / contact
    we(hm, "15010", contact.get("daytime_phone", ""))
    we(hm, "15011", contact.get("daytime_ext",   ""))
    we(hm, "15012", contact.get("evening_phone", ""))
    we(hm, "15013", contact.get("evening_ext",   ""))
    we(hm, "15014", contact.get("cell_phone",    ""))
    we(hm, "15017", contact.get("fax",           ""))
    we(hm, "15018", contact.get("email",         ""))

    # Checkboxes
    wx(hm, "15019", bool(s2.get("dependent_of_another",   False)))
    wx(hm, "15020", bool(s2.get("full_time_student",       False)))
    wx(hm, "15021", bool(s2.get("presidential_campaign",   False)))
    wx(hm, "15022", bool(s2.get("blind",                   False)))


def _fill_spouse(hm: dict, data: dict) -> None:
    spouse = data["client_basic_details"].get("spouse_info", {})
    if not spouse:
        print("    [SKIP] No spouse_info in JSON")
        return

    sp_contact = spouse.get("contact", {})

    # SSN — remove all separators
    we(hm, "15024", spouse.get("ssn_or_itin", "").replace("-", "").replace(" ", ""))

    # Name
    we(hm, "15025", spouse.get("first_name",     ""))
    we(hm, "15026", spouse.get("middle_initial", ""))
    we(hm, "15027", spouse.get("last_name",      ""))
    wc(hm, "15028", spouse.get("suffix",         ""))

    # Dates
    we(hm, "15029", spouse.get("date_of_birth", "").replace("-", "").replace("/", ""))
    we(hm, "15030", spouse.get("date_of_death", "").replace("-", "").replace("/", ""))

    # Occupation
    we(hm, "15031", spouse.get("occupation", ""))

    # Phone / contact
    we(hm, "15032", sp_contact.get("daytime_phone", ""))
    we(hm, "15033", sp_contact.get("daytime_ext",   ""))
    we(hm, "15034", sp_contact.get("evening_phone", ""))
    we(hm, "15035", sp_contact.get("evening_ext",   ""))
    we(hm, "15036", sp_contact.get("cell_phone",    ""))
    we(hm, "15039", sp_contact.get("fax",           ""))
    we(hm, "15040", sp_contact.get("email",         ""))

    # Checkboxes
    wx(hm, "15041", bool(spouse.get("dependent_of_another",          False)))
    wx(hm, "15042", bool(spouse.get("full_time_student",              False)))
    wx(hm, "15043", bool(spouse.get("presidential_campaign",          False)))
    wx(hm, "15044", bool(spouse.get("blind",                          False)))
    wx(hm, "15045", bool(spouse.get("nonresident_alien",              False)))
    wx(hm, "15046", bool(spouse.get("nonresident_alien_us_resident",  False)))
    wx(hm, "15047", bool(spouse.get("spouse_not_filing",              False)))
    wx(hm, "15048", bool(spouse.get("spouse_no_us_income",            False)))


def _fill_mailing_address(hm: dict, data: dict) -> None:
    addr = data["client_basic_details"].get("mailing_address", {})

    we(hm, "15049", addr.get("in_care_of",  ""))
    we(hm, "15050", addr.get("street",      ""))
    we(hm, "15051", addr.get("apt_number",  ""))
    we(hm, "15052", addr.get("city",        ""))

    # State — take only the 2-letter abbreviation if stored as "FL FLORIDA"
    state = addr.get("state", "")
    wc(hm, "15053", state.split()[0] if state else "")

    we(hm, "15054", addr.get("zip_code", ""))
    we(hm, "15055", addr.get("county",   ""))

    # Optional checkboxes
    wx(hm, "15056", bool(addr.get("stateside_military",  False)))
    wx(hm, "15057", bool(addr.get("change_of_address",   False)))

    # Foreign address (only filled when present in JSON)
    we(hm, "15058", addr.get("foreign_province_state", ""))
    wc(hm, "15059", addr.get("foreign_country",        ""))
    we(hm, "15060", addr.get("foreign_postal_code",    ""))


def _fill_resident(hm: dict, data: dict) -> None:
    s2 = data["client_basic_details"].get("section_2", {})

    res_state = s2.get("residential_state", "")
    wc(hm, "15061", res_state.split()[0] if res_state else "")

    wc(hm, "15062", s2.get("resident_city",    ""))
    wc(hm, "15063", s2.get("school_district",  ""))


# ── Post-save popup handler ───────────────────────────────────────────────────

def _handle_post_name_popup() -> None:
    """
    After ESC on the Name & Address form, Drake sometimes shows a
    'DRAKE 20XX - Data Entry' confirmation dialog.  Click Cancel to dismiss.
    """
    print("[NAME] Checking for post-save popup...")

    # Try both Drake year variants
    popup_hwnd = wait_for_popup("DRAKE 2024 - Data Entry", timeout=5)
    if not popup_hwnd:
        popup_hwnd = wait_for_popup("DRAKE 2023 - Data Entry", timeout=5)
    if not popup_hwnd:
        popup_hwnd = wait_for_popup("DRAKE 20", timeout=3)   # generic catch-all

    if not popup_hwnd:
        print("[NAME] No popup — all clear.")
        return

    print(f"[NAME] Post-save popup found (HWND: {popup_hwnd})")
    popup_app = Application(backend="uia").connect(handle=popup_hwnd)
    popup_win = popup_app.window(handle=popup_hwnd)

    try:
        popup_win.child_window(title="Cancel", control_type="Button").click_input()
        print("[NAME] Popup dismissed via Cancel.")
    except Exception as exc:
        print(f"[NAME] Cancel not found ({exc}) — pressing ESC as fallback.")
        keyboard.send_keys("{ESC}")
