import time

import win32gui
from pywinauto import keyboard
from pywinauto.application import Application

from navigation import press_escape
from win32_helpers import wc, we, wx
from window_utils import build_hwnd_map, force_focus, wait_for_popup


# ── Open / Create return ──────────────────────────────────────────────────────

def open_or_create_return(main_win, ssn: str, data: dict) -> None:
    main_win.child_window(
        title="Open/Create",
        auto_id="MainWindow_TextBlockToolbarOpenCreate",
        control_type="Text",
    ).click_input()

    ssn_input = main_win.child_window(
        auto_id="ClearableWatermarkTextbox_TextBoxInput", control_type="Edit"
    )
    ssn_input.click_input()
    ssn_input.type_keys("^a{BACKSPACE}")
    ssn_input.type_keys(ssn, with_spaces=True)

    main_win.child_window(
        title="OK",
        auto_id="FileOpenCreateWindow_ButtonOK",
        control_type="Button",
    ).click_input()

    print("[RETURN] Looking for 'Open Return' popup...")
    popup_hwnd = _wait_for_small_popup(
        ["Drake - Open Return", "Drake 2024 - Open Return",
         "Drake 2023 - Open Return", "Open Return"],
        timeout=10
    )

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
    s1 = data["client_basic_details"]["section_1"]
    fields = [
        ("CreateReturnWindow_TextBoxFirstName",     s1.get("first_name", "")),
        ("CreateReturnWindow_TextBoxMiddleInitial", s1.get("middle_initial", "")),
        ("CreateReturnWindow_TextBoxLastName",      s1.get("last_name", "")),
    ]
    for auto_id, value in fields:
        box = main_win.child_window(auto_id=auto_id, control_type="Edit")
        box.click_input()
        box.type_keys("^a{BACKSPACE}")
        box.type_keys(value, with_spaces=True)
    main_win.child_window(
        auto_id="CreateReturnWindow_TextBoxLastName", control_type="Edit"
    ).type_keys("{ENTER}")
    print("[RETURN] Create Return name fields filled.")


# ── Name and Address — main entry point ──────────────────────────────────────

def fill_name_and_address(data_entry_hwnd: int, data: dict) -> None:
    """
    Navigate to Name & Address and fill all fields.

    KEY FACTS from verified control dump of the Data Entry General tab:
      - Nav link "Name and Address" = auto_id="2002", control_type="Text" (Static)
      - Search Edit box              = auto_id="1003", control_type="Edit"
        (There is ALSO a GroupBox with auto_id="1003" — must filter by Edit type)
      - After clicking nav or typing "1"+Enter, the SAME Data Entry window
        gets populated with 15001+ controls (Name & Address form fields)
    """
    if not data_entry_hwnd:
        print("[NAME] ERROR: data_entry_hwnd is None — cannot navigate.")
        return

    force_focus(data_entry_hwnd)
    time.sleep(0.4)

    # [1] Navigate — try UIA click on nav link first (most reliable)
    print("[NAME] Navigating to Name and Address...")
    navigated = _click_nav_link(data_entry_hwnd)
    if not navigated:
        print("[NAME] Nav link failed — falling back to search box...")
        _navigate_via_search_box(data_entry_hwnd, "1")

    time.sleep(1.5)

    # [2] Find the form — same window will now have 15001/15050 controls
    form_hwnd = _find_name_form(timeout=15)
    if not form_hwnd:
        print("[NAME] !! Name & Address form not found — aborting.")
        return

    force_focus(form_hwnd)
    time.sleep(0.3)

    # [3] Build control map
    hm = build_hwnd_map(form_hwnd)
    print(f"[NAME] {len(hm)} controls mapped (HWND={form_hwnd})")

    if len(hm) < 10:
        print("[NAME] Controls sparse — waiting 1.5s and retrying...")
        time.sleep(1.5)
        hm = build_hwnd_map(form_hwnd)
        print(f"[NAME] Retry: {len(hm)} controls")

    # [4] Fill all sections
    print("[NAME] Filling Taxpayer...")
    _fill_taxpayer(hm, data)

    print("[NAME] Filling Spouse...")
    _fill_spouse(hm, data)

    print("[NAME] Filling Mailing Address...")
    _fill_mailing_address(hm, data)

    print("[NAME] Filling Resident State...")
    _fill_resident(hm, data)

    # [5] ESC = save
    press_escape(form_hwnd)
    time.sleep(0.5)

    # [6] Dismiss post-save popup if any
    _handle_post_name_popup()


# ── Navigation helpers ────────────────────────────────────────────────────────

def _click_nav_link(data_entry_hwnd: int) -> bool:
    """
    Click the 'Name and Address' Static/Text control (auto_id='2002').
    Confirmed present in General tab control dump.
    """
    try:
        app = Application(backend="uia").connect(handle=data_entry_hwnd)
        win = app.window(handle=data_entry_hwnd)
        nav = win.child_window(auto_id="2002", control_type="Text")
        nav.wait("visible", timeout=5)
        nav.click_input()
        print("[NAME] Clicked nav link (auto_id=2002)")
        return True
    except Exception as exc:
        print(f"[NAME] Nav link (2002) failed: {exc}")
        return False


def _navigate_via_search_box(data_entry_hwnd: int, term: str) -> None:
    """
    Type into the search/shortcode Edit box (auto_id='1003', control_type='Edit').

    IMPORTANT: There are TWO controls with auto_id='1003' in the window:
      1. GroupBox  (Due Diligence group)   — auto_id="1003", control_type="Group"
      2. Edit      (search/nav box)        — auto_id="1003", control_type="Edit"
    We must filter by control_type="Edit" to get the right one.
    """
    try:
        app = Application(backend="uia").connect(handle=data_entry_hwnd)
        win = app.window(handle=data_entry_hwnd)
        # Explicitly filter by Edit type to avoid the GroupBox with same auto_id
        search = win.child_window(auto_id="1003", control_type="Edit")
        search.wait("visible", timeout=8)
        search.click_input()
        time.sleep(0.15)
        keyboard.send_keys(f"^a{{DELETE}}{term}{{ENTER}}", pause=0.05)
        print(f"[NAME] Search box: typed '{term}' + Enter")
    except Exception as exc:
        print(f"[NAME] Search box navigation failed: {exc}")


# ── Window finder ─────────────────────────────────────────────────────────────

def _find_name_form(timeout: int = 15) -> int | None:
    """
    Find the Data Entry window that has Name & Address controls loaded.

    After clicking the nav link, the SAME Data Entry window gets the
    15001+ controls. We distinguish it from the General tab by checking
    for controls that only appear on the Name & Address form:
      15001 = Filing Status combo  (always on Name & Address)
      15050 = Street address edit  (always on Name & Address)

    The General tab only has controls 1001-1004 and 2001-2072 — no 15xxx.
    """
    deadline = time.time() + timeout
    print("[NAME] Waiting for Name & Address controls", end="", flush=True)

    while time.time() < deadline:
        candidates = []

        def _cb(hwnd, _):
            title = win32gui.GetWindowText(hwnd)
            # Accept any Drake year: 2023, 2024, 2025...
            if "DRAKE 20" in title and "Data Entry" in title \
                    and win32gui.IsWindowVisible(hwnd):
                candidates.append(hwnd)

        win32gui.EnumWindows(_cb, None)

        for hwnd in candidates:
            hm = build_hwnd_map(hwnd)
            # Name & Address form: has both 15001 (filing status) and 15050 (street)
            if "15001" in hm and "15050" in hm:
                print(f"\n[NAME] Form ready: HWND={hwnd}, {len(hm)} controls")
                return hwnd

        print(".", end="", flush=True)
        time.sleep(0.3)

    print("\n[NAME] Timeout — Name & Address form not found")
    return None


# ── Section fillers ───────────────────────────────────────────────────────────

def _fill_taxpayer(hm: dict, data: dict) -> None:
    s1      = data["client_basic_details"]["section_1"]
    s2      = data["client_basic_details"]["section_2"]
    contact = data["client_basic_details"].get("contact", {})

    wc(hm, "15001", s2.get("filing_status", ""))

    # 15002=SSN, 15003=First, 15005=Last — pre-filled at create step, skip
    print("    [SKIP] 15002/15003/15005 — pre-filled at create")

    we(hm, "15004", s1.get("middle_initial", ""))
    wc(hm, "15006", s2.get("suffix", ""))
    we(hm, "15007", s2.get("date_of_birth", "").replace("-", "").replace("/", ""))
    we(hm, "15008", s2.get("date_of_death", "").replace("-", "").replace("/", ""))
    we(hm, "15009", s2.get("occupation", ""))

    we(hm, "15010", contact.get("daytime_phone", ""))
    we(hm, "15011", contact.get("daytime_ext",   ""))
    we(hm, "15012", contact.get("evening_phone", ""))
    we(hm, "15013", contact.get("evening_ext",   ""))
    we(hm, "15014", contact.get("cell_phone",    ""))
    we(hm, "15017", contact.get("fax",           ""))
    we(hm, "15018", contact.get("email",         ""))

    wx(hm, "15019", bool(s2.get("dependent_of_another",  False)))
    wx(hm, "15020", bool(s2.get("full_time_student",      False)))
    wx(hm, "15021", bool(s2.get("presidential_campaign",  False)))
    wx(hm, "15022", bool(s2.get("blind",                  False)))


def _fill_spouse(hm: dict, data: dict) -> None:
    spouse = data["client_basic_details"].get("spouse_info", {})
    if not spouse:
        print("    [SKIP] No spouse_info in JSON")
        return

    sp_contact = spouse.get("contact", {})

    we(hm, "15024", spouse.get("ssn_or_itin", "").replace("-", "").replace(" ", ""))
    we(hm, "15025", spouse.get("first_name",     ""))
    we(hm, "15026", spouse.get("middle_initial", ""))
    we(hm, "15027", spouse.get("last_name",      ""))
    wc(hm, "15028", spouse.get("suffix",         ""))
    we(hm, "15029", spouse.get("date_of_birth", "").replace("-", "").replace("/", ""))
    we(hm, "15030", spouse.get("date_of_death", "").replace("-", "").replace("/", ""))
    we(hm, "15031", spouse.get("occupation", ""))

    we(hm, "15032", sp_contact.get("daytime_phone", ""))
    we(hm, "15033", sp_contact.get("daytime_ext",   ""))
    we(hm, "15034", sp_contact.get("evening_phone", ""))
    we(hm, "15035", sp_contact.get("evening_ext",   ""))
    we(hm, "15036", sp_contact.get("cell_phone",    ""))
    we(hm, "15039", sp_contact.get("fax",           ""))
    we(hm, "15040", sp_contact.get("email",         ""))

    wx(hm, "15041", bool(spouse.get("dependent_of_another",         False)))
    wx(hm, "15042", bool(spouse.get("full_time_student",             False)))
    wx(hm, "15043", bool(spouse.get("presidential_campaign",         False)))
    wx(hm, "15044", bool(spouse.get("blind",                         False)))
    wx(hm, "15045", bool(spouse.get("nonresident_alien",             False)))
    wx(hm, "15046", bool(spouse.get("nonresident_alien_us_resident", False)))
    wx(hm, "15047", bool(spouse.get("spouse_not_filing",             False)))
    wx(hm, "15048", bool(spouse.get("spouse_no_us_income",           False)))


def _fill_mailing_address(hm: dict, data: dict) -> None:
    addr = data["client_basic_details"].get("mailing_address", {})

    we(hm, "15049", addr.get("in_care_of", ""))
    we(hm, "15050", addr.get("street",     ""))
    we(hm, "15051", addr.get("apt_number", ""))
    we(hm, "15052", addr.get("city",       ""))

    state = addr.get("state", "")
    wc(hm, "15053", state.split()[0] if state else "")

    we(hm, "15054", addr.get("zip_code", ""))
    we(hm, "15055", addr.get("county",   ""))

    wx(hm, "15056", bool(addr.get("stateside_military", False)))
    wx(hm, "15057", bool(addr.get("change_of_address",  False)))

    we(hm, "15058", addr.get("foreign_province_state", ""))
    wc(hm, "15059", addr.get("foreign_country",        ""))
    we(hm, "15060", addr.get("foreign_postal_code",    ""))


def _fill_resident(hm: dict, data: dict) -> None:
    s2 = data["client_basic_details"].get("section_2", {})

    res_state = s2.get("residential_state", "")
    wc(hm, "15061", res_state.split()[0] if res_state else "")
    wc(hm, "15062", s2.get("resident_city",   ""))
    wc(hm, "15063", s2.get("school_district", ""))


# ── Post-save popup handler ───────────────────────────────────────────────────

def _handle_post_name_popup() -> None:
    print("[NAME] Checking for post-save popup...")
    popup_hwnd = _wait_for_small_popup(
        ["DRAKE 2024 - Data Entry", "DRAKE 2023 - Data Entry", "DRAKE 20"],
        timeout=6
    )
    if not popup_hwnd:
        print("[NAME] No popup — all clear.")
        return

    print(f"[NAME] Post-save popup (HWND={popup_hwnd}) — dismissing...")
    popup_app = Application(backend="uia").connect(handle=popup_hwnd)
    popup_win = popup_app.window(handle=popup_hwnd)
    try:
        popup_win.child_window(title="Cancel", control_type="Button").click_input()
        print("[NAME] Dismissed via Cancel.")
    except Exception as exc:
        print(f"[NAME] Cancel not found ({exc}) — pressing ESC.")
        keyboard.send_keys("{ESC}")


# ── Utility: wait for a small popup dialog ────────────────────────────────────

def _wait_for_small_popup(title_fragments: list, timeout: int = 10) -> int | None:
    """
    Wait for a popup window whose title contains any of the given strings.
    Uses control count < 20 to distinguish real popups from the main
    Data Entry window (which has 70+ controls).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        results = []

        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            for frag in title_fragments:
                if frag in title:
                    results.append(hwnd)
                    break

        win32gui.EnumWindows(_cb, None)

        for hwnd in results:
            hm = build_hwnd_map(hwnd)
            if len(hm) < 20:   # real popup, not the full Data Entry window
                return hwnd

        time.sleep(0.2)
    return None
