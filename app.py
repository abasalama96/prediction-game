import os, re, json, hashlib, secrets
import io, zipfile, tempfile, shutil
from datetime import datetime, date, time as dtime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

# ─────────────────────────────
# App setup
# ─────────────────────────────
st.set_page_config(page_title="⚽ Prediction Game", layout="wide")

DATA_DIR = "."
USERS_FILE         = os.path.join(DATA_DIR, "users.csv")
MATCHES_FILE       = os.path.join(DATA_DIR, "matches.csv")
MATCH_HISTORY_FILE = os.path.join(DATA_DIR, "match_history.csv")
PREDICTIONS_FILE   = os.path.join(DATA_DIR, "predictions.csv")
LEADERBOARD_FILE   = os.path.join(DATA_DIR, "leaderboard.csv")
SEASON_FILE        = os.path.join(DATA_DIR, "season.txt")
TEAM_LOGOS_FILE    = os.path.join(DATA_DIR, "team_logos.json")
LOGO_DIR           = os.path.join(DATA_DIR, "logos")
os.makedirs(LOGO_DIR, exist_ok=True)

ADMIN_PASSWORD = "madness"

# ─────────────────────────────
# i18n
# ─────────────────────────────
LANG = {
    "en": {
        "app_title": "⚽ Prediction Game",
        "sidebar_time": "⏱️ Time & Settings",
        "sidebar_lang": "Language",
        "lang_en": "English",
        "lang_ar": "العربية",
        "app_timezone": "App Timezone",

        "login_tab": "Login",
        "user_login": "User Login",
        "admin_login": "Admin Login",
        "your_name": "Your Name",
        "admin_pass": "Admin Password",
        "login": "Login",
        "register": "Register",
        "login_ok": "Logged in.",
        "admin_ok": "Admin authenticated.",
        "admin_bad": "Wrong password.",
        "need_name": "Please enter a name.",
        "please_login_first": "Please log in first",

        "tab_play": "Play",
        "tab_leaderboard": "Leaderboard",
        "tab_admin": "Admin",

        "no_matches": "No matches yet.",
        "kickoff": "Kickoff",
        "opens_in": "Opens in",
        "closes_in": "Closes in",
        "closed": "Predictions closed",
        "score": "Score (e.g. 2-1)",
        "winner": "Winner",
        "draw": "Draw",
        "gold_badge": "🔥 Golden Match 🔥",
        "already_submitted": "You already submitted.",
        "saved_ok": "Prediction saved.",
        "fmt_error": "Use format like 2-1 (numbers only)",
        "range_error": "Goals must be 0–20",
        "enter_both_teams": "Enter both teams.",
        "submit_btn": "Submit",

        "leaderboard": "Leaderboard",
        "no_scores_yet": "No scores yet.",
        "lb_rank": "Rank",
        "lb_user": "User",
        "lb_preds": "Predictions",
        "lb_exact": "Exact",
        "lb_outcome": "Outcome",
        "lb_points": "Points",

        "admin_panel": "Admin Panel",
        "season_settings": "Season",
        "season_name_label": "Season Name (e.g., Real Madrid 2025)",
        "season_saved": "Season name saved.",
        "reset_season": "Reset Season",
        "reset_confirm": "Season reset complete (team logos are kept).",
        "test_data": "Insert Test Data",
        "test_done": "Test data inserted.",

        # ✅ NEW (Backup & Restore)
        "backup_restore": "Backup & Restore",
        "backup_desc": "Download a backup ZIP of all data (users, matches, predictions, leaderboard, season, team logos, and uploaded logo files).",
        "backup_btn": "⬇️ Download Backup (ZIP)",
        "restore_desc": "Restore from a backup ZIP. This will overwrite current data files and logo files.",
        "restore_upload": "Upload backup ZIP",
        "restore_btn": "♻️ Restore from ZIP",
        "restore_done": "Restore completed. Leaderboard recalculated.",
        "restore_need_file": "Please upload a ZIP backup first.",

        "add_match": "➕ Add a match",
        "team_a": "Team A",
        "team_b": "Team B",
        "home_logo_url": "Home Logo URL",
        "away_logo_url": "Away Logo URL",
        "home_logo_upload": "Upload Home Logo",
        "away_logo_upload": "Upload Away Logo",
        "occasion": "Occasion",
        "occasion_logo_url": "Occasion Logo URL",
        "occasion_logo_upload": "Upload Occasion Logo",
        "round": "Round",
        "date_label": "Date",
        "hour": "Hour (1–12)",
        "minute": "Minute",
        "ampm": "AM/PM",
        "ampm_am": "AM",
        "ampm_pm": "PM",
        "big_game": "🔥 Golden Match 🔥",
        "btn_add_match": "Add Match",
        "match_added": "Match added.",

        "edit_matches": "Edit Matches",
        "final_score": "Final Score (e.g. 2-1)",
        "real_winner": "Real Winner",
        "save": "Save",
        "delete": "Delete",
        "updated": "Updated",
        "deleted": "Deleted",

        "match_history": "Match History (Admin only)",
        "registered_users": "Registered Users",
        "terminate": "Terminate",
        "terminated": "User terminated.",
    },
    "ar": {
        "app_title": "⚽ لعبة التوقعات",
        "sidebar_time": "⏱️ الوقت والإعدادات",
        "sidebar_lang": "اللغة",
        "lang_en": "English",
        "lang_ar": "العربية",
        "app_timezone": "المنطقة الزمنية للتطبيق",

        "login_tab": "تسجيل الدخول",
        "user_login": "دخول المشارك",
        "admin_login": "دخول المشرف",
        "your_name": "اسمك",
        "admin_pass": "كلمة مرور المشرف",
        "login": "تسجيل الدخول",
        "register": "تسجيل",
        "login_ok": "تم تسجيل الدخول.",
        "admin_ok": "تم التحقق من المشرف.",
        "admin_bad": "كلمة المرور غير صحيحة.",
        "need_name": "الرجاء إدخال الاسم.",
        "please_login_first": "الرجاء تسجيل الدخول أولًا",

        "tab_play": "اللعب",
        "tab_leaderboard": "الترتيب",
        "tab_admin": "الإدارة",

        "no_matches": "لا توجد مباريات بعد.",
        "kickoff": "ضربة البداية",
        "opens_in": "يفتح بعد",
        "closes_in": "يغلق بعد",
        "closed": "أُغلقت التوقعات",
        "score": "النتيجة (مثال 1-2)",
        "winner": "الفائز",
        "draw": "تعادل",
        "gold_badge": "🔥 المباراة الذهبية 🔥",
        "already_submitted": "لقد سجّلت توقعك.",
        "saved_ok": "تم حفظ التوقع.",
        "fmt_error": "استخدم الصيغة 1-2 (أرقام فقط)",
        "range_error": "الأهداف بين 0 و20",
        "enter_both_teams": "أدخل اسمي الفريقين.",
        "submit_btn": "إرسال",

        "leaderboard": "الترتيب",
        "no_scores_yet": "لا توجد نقاط بعد.",
        "lb_rank": "الترتيب",
        "lb_user": "المشارك",
        "lb_preds": "عدد التوقعات",
        "lb_exact": "التوقع الصحيح",
        "lb_outcome": "نصف التوقع",
        "lb_points": "النقاط",

        "admin_panel": "لوحة التحكم",
        "season_settings": "الموسم",
        "season_name_label": "اسم الموسم (مثال: ريال مدريد 2025)",
        "season_saved": "تم حفظ اسم الموسم.",
        "reset_season": "إعادة ضبط الموسم",
        "reset_confirm": "تمت إعادة ضبط الموسم (مع الاحتفاظ بالشعارات المحفوظة).",
        "test_data": "إدراج بيانات تجريبية",
        "test_done": "تم إدراج البيانات التجريبية.",

        # ✅ NEW (Backup & Restore)
        "backup_restore": "النسخ الاحتياطي والاستعادة",
        "backup_desc": "تحميل ملف ZIP يحتوي على كل البيانات (المستخدمين، المباريات، التوقعات، الترتيب، الموسم، شعارات الفرق، وملفات الشعارات المرفوعة).",
        "backup_btn": "⬇️ تحميل النسخة الاحتياطية (ZIP)",
        "restore_desc": "استعادة من ملف ZIP. سيتم استبدال البيانات الحالية وملفات الشعارات.",
        "restore_upload": "رفع ملف النسخة الاحتياطية ZIP",
        "restore_btn": "♻️ استعادة من ZIP",
        "restore_done": "تمت الاستعادة. تم إعادة حساب الترتيب.",
        "restore_need_file": "الرجاء رفع ملف ZIP أولاً.",

        "add_match": "➕ إضافة مباراة",
        "team_a": "الفريق (أ)",
        "team_b": "الفريق (ب)",
        "home_logo_url": "رابط شعار المضيف",
        "away_logo_url": "رابط شعار الضيف",
        "home_logo_upload": "رفع شعار المضيف",
        "away_logo_upload": "رفع شعار الضيف",
        "occasion": "المناسبة",
        "occasion_logo_url": "رابط شعار المناسبة",
        "occasion_logo_upload": "رفع شعار المناسبة",
        "round": "الجولة",
        "date_label": "التاريخ",
        "hour": "الساعة (1–12)",
        "minute": "الدقيقة",
        "ampm": "ص/م",
        "ampm_am": "صباحا",
        "ampm_pm": "مساء",
        "big_game": "🔥 المباراة الذهبية 🔥",
        "btn_add_match": "إضافة المباراة",
        "match_added": "تمت إضافة المباراة.",

        "edit_matches": "تعديل المباريات",
        "final_score": "النتيجة النهائية (مثال 2-1)",
        "real_winner": "الفائز الحقيقي",
        "save": "حفظ",
        "delete": "حذف",
        "updated": "تم التحديث",
        "deleted": "تم الحذف",

        "match_history": "سجل المباريات (للمشرف فقط)",
        "registered_users": "المستخدمون المسجّلون",
        "terminate": "إيقاف",
        "terminated": "تم إيقاف المستخدم.",
    }
}

def tr(lang, key, **kwargs):
    d = LANG["ar" if lang == "ar" else "en"]
    txt = d.get(key, key)
    return txt.format(**kwargs) if kwargs else txt
# ─────────────────────────────
# Utilities & persistence
# ─────────────────────────────
def normalize_digits(text: str) -> str:
    if not isinstance(text, str): return text
    mapping = {
        ord('٠'):'0', ord('١'):'1', ord('٢'):'2', ord('٣'):'3', ord('٤'):'4',
        ord('٥'):'5', ord('٦'):'6', ord('٧'):'7', ord('٨'):'8', ord('٩'):'9',
        ord('۰'):'0', ord('۱'):'1', ord('۲'):'2', ord('۳'):'3', ord('۴'):'4',
        ord('۵'):'5', ord('۶'):'6', ord('۷'):'7', ord('۸'):'8', ord('۹'):'9',
    }
    text = text.translate(mapping).strip()
    for ch in ['–','—','−','ـ','‒','﹘','﹣','－']:
        text = text.replace(ch, '-')
    return text

def load_csv(file, cols):
    if os.path.exists(file) and os.path.getsize(file) > 0:
        df = pd.read_csv(file)
        for c in cols:
            if c not in df.columns: df[c] = None
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_csv(df, file):
    df.to_csv(file, index=False)

def _hash_pin(pin: str) -> str:
    salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + pin).encode("utf-8")).hexdigest()
    return f"{salt}:{h}"

def _verify_pin(stored: str | None, pin: str) -> bool:
    try:
        if stored is None: return False
        if isinstance(stored, float) and pd.isna(stored): return False
        s = str(stored)
        if ":" not in s: return False
        salt, h = s.split(":", 1)
        return hashlib.sha256((salt + pin).encode("utf-8")).hexdigest() == h
    except Exception:
        return False

def parse_iso_dt(val):
    try:
        return datetime.fromisoformat(str(val)) if pd.notna(val) and val else None
    except Exception:
        return None

def to_tz(dt: datetime | None, tz: ZoneInfo) -> datetime | None:
    if not dt: return None
    if dt.tzinfo is None: return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)

def format_dt_ampm(dt: datetime | None, tz: ZoneInfo, lang="en") -> str:
    if not dt: return ""
    loc = to_tz(dt, tz) if dt.tzinfo else dt.replace(tzinfo=tz)
    if lang == "ar":
        ampm = "صباحا" if loc.strftime("%p") == "AM" else "مساء"
        return loc.strftime("%Y-%m-%d %I:%M ") + ampm
    return loc.strftime("%Y-%m-%d %I:%M %p")

def human_delta(delta: timedelta, lang: str) -> str:
    total = int(max(0, delta.total_seconds()))
    days = total // 86400
    hours = (total % 86400) // 3600
    minutes = (total % 3600) // 60
    if lang == "ar":
        day_w, hour_w, min_w = ("يوم" if days==1 else "ايام", "ساعة" if hours==1 else "ساعات", "دقيقة" if minutes==1 else "دقائق")
        parts = []
        if days: parts.append(f"{days} {day_w}")
        parts.append(f"{hours} {hour_w}")
        parts.append(f"{minutes} {min_w}")
        return " ".join(parts)
    parts = []
    if days: parts.append(f"{days} {'day' if days==1 else 'days'}")
    parts.append(f"{hours} {'hour' if hours==1 else 'hours'}")
    parts.append(f"{minutes} {'minute' if minutes==1 else 'minutes'}")
    return " ".join(parts)

# ─────────────────────────────
# ✅ Backup & Restore helpers (NEW)
# ─────────────────────────────
_BACKUP_FILES = [
    USERS_FILE,
    MATCHES_FILE,
    MATCH_HISTORY_FILE,
    PREDICTIONS_FILE,
    LEADERBOARD_FILE,
    SEASON_FILE,
    TEAM_LOGOS_FILE,
]

def _backup_zip_bytes() -> bytes:
    """Create a ZIP of current CSV/JSON/TXT files + logos folder (if any)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # data files
        for fp in _BACKUP_FILES:
            if os.path.exists(fp) and os.path.getsize(fp) > 0:
                z.write(fp, arcname=os.path.basename(fp))
        # logos folder
        if os.path.isdir(LOGO_DIR):
            for root, _, files in os.walk(LOGO_DIR):
                for name in files:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, DATA_DIR)
                    z.write(full, arcname=rel)
    return buf.getvalue()

def _restore_from_zip_bytes(zip_bytes: bytes):
    """
    Restore data files and logos folder from the ZIP.
    Overwrites existing files.
    Then recompute leaderboard from predictions.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        zpath = os.path.join(tmpdir, "backup.zip")
        with open(zpath, "wb") as f:
            f.write(zip_bytes)

        with zipfile.ZipFile(zpath, "r") as z:
            z.extractall(tmpdir)

        # Restore data files (by basename)
        for fp in _BACKUP_FILES:
            base = os.path.basename(fp)
            src = os.path.join(tmpdir, base)
            if os.path.exists(src):
                shutil.copy2(src, fp)

        # Restore logos directory if present in ZIP
        extracted_logo_dir = os.path.join(tmpdir, os.path.basename(LOGO_DIR))
        if os.path.isdir(extracted_logo_dir):
            # wipe current LOGO_DIR then copy
            if os.path.isdir(LOGO_DIR):
                shutil.rmtree(LOGO_DIR, ignore_errors=True)
            shutil.copytree(extracted_logo_dir, LOGO_DIR, dirs_exist_ok=True)
        else:
            # ZIP might have logos/<files> structure
            possible = os.path.join(tmpdir, "logos")
            if os.path.isdir(possible):
                if os.path.isdir(LOGO_DIR):
                    shutil.rmtree(LOGO_DIR, ignore_errors=True)
                shutil.copytree(possible, LOGO_DIR, dirs_exist_ok=True)

    # Recompute leaderboard after restore (keeps everything consistent)
    preds = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
    recompute_leaderboard(preds)

# ─────────────────────────────
# logo helpers
# ─────────────────────────────
def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    base = os.path.basename(parsed.path) or "logo.png"
    ext = os.path.splitext(base)[1] or ".png"
    stem = hashlib.md5(url.encode()).hexdigest()
    return f"{stem}{ext}"

def cache_logo_from_url(url: str) -> str | None:
    if not (isinstance(url, str) and url.lower().startswith(("http://","https://"))): return None
    try:
        fname = _filename_from_url(url)
        path = os.path.join(LOGO_DIR, fname)
        if os.path.exists(path): return path
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(path, "wb") as f: f.write(r.content)
        return path
    except Exception:
        return None

def save_uploaded_logo(file, name_hint: str) -> str | None:
    try:
        ext = os.path.splitext(file.name)[1] or ".png"
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name_hint or "logo")
        path = os.path.join(LOGO_DIR, f"{safe}{ext}")
        with open(path, "wb") as f: f.write(file.read())
        return path
    except Exception:
        return None

def _load_team_logos() -> dict:
    if os.path.exists(TEAM_LOGOS_FILE) and os.path.getsize(TEAM_LOGOS_FILE) > 0:
        try:
            with open(TEAM_LOGOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_team_logos(mapping: dict):
    try:
        with open(TEAM_LOGOS_FILE, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_team_logo(team: str, logo_path_or_url: str | None):
    if not team or not logo_path_or_url: return
    logos = _load_team_logos()
    logos[team] = logo_path_or_url
    _save_team_logos(logos)

def get_saved_logo(team: str) -> str | None:
    logos = _load_team_logos()
    return logos.get(team or "", None)

def get_known_teams() -> list:
    logos = _load_team_logos()
    return sorted([k for k in logos.keys() if k])

def ensure_history_schema(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"]
    if df.empty: return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns: df[c] = None
    return df[cols]

# NEW: safe logo renderer (works for local paths & URLs, ignores bad images)
def show_logo_safe(img_ref, width=56, caption=""):
    """Render a logo whether it is a local file path or a URL; ignore unreadable images."""
    try:
        if not img_ref or (isinstance(img_ref, float) and pd.isna(img_ref)):
            return
        s = str(img_ref).strip()
        if not s:
            return
        # Render only if it's a local file that exists, or a valid http(s) URL
        if os.path.exists(s) or s.lower().startswith(("http://", "https://")):
            st.image(s, width=width, caption=caption)
    except Exception:
        # Fail silently if the image can't be loaded
        pass

# theme
def apply_theme():
    st.markdown("""
    <style>
      html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg,#0a1f0f,#08210c);
        color:#eafbea;
      }
      .card { background: rgba(255,255,255,0.06); border: 1px solid #134e29;
              border-radius: 16px; padding: 12px 16px; box-shadow: 0 6px 18px rgba(0,0,0,0.25); margin-bottom:10px; }
      .badge-gold { background:#FFF4C2; color:#000; border:1px solid #111; padding:4px 10px; border-radius:999px; font-weight:700; }
      .welcome-wrap { width:100%; text-align:right; margin-top:-6px; margin-bottom:6px; color:#eafbea; opacity:0.9; }
    </style>
    """, unsafe_allow_html=True)

def show_welcome_top_right(name: str, lang: str):
    if not name: return
    label = f"Welcome, <b>{name}</b>" if lang=="en" else f"مرحبًا، <b>{name}</b>"
    st.markdown(f"""<div class="welcome-wrap">{label}</div>""", unsafe_allow_html=True)

# --- Browser time zone detection + query param bridge (uses st.query_params) ---
def _setup_browser_timezone_param():
    """
    Detects the browser time zone with JS and stores it in the URL (?tz=...).
    No reloads; just updates the address bar so Streamlit can read it.
    """
    import streamlit.components.v1 as components
    components.html("""
    <script>
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      const url = new URL(window.location);
      const current = url.searchParams.get('tz') || '';
      if (tz && tz !== current) {
        url.searchParams.set('tz', tz);
        window.history.replaceState({}, "", url);
      }
    } catch (e) {}
    </script>
    """, height=0)

def _get_tz_from_query_params(default_tz="Asia/Riyadh"):
    try:
        return st.query_params.get("tz", default_tz) or default_tz
    except Exception:
        return default_tz
# ─────────────────────────────
# Users (Name + PIN)
# ─────────────────────────────
def load_users():
    cols = ["Name","CreatedAt","IsBanned","PinHash"]
    if os.path.exists(USERS_FILE) and os.path.getsize(USERS_FILE) > 0:
        df = pd.read_csv(USERS_FILE)
        for c in cols:
            if c not in df.columns: df[c] = None
        df["IsBanned"] = pd.to_numeric(df["IsBanned"], errors="coerce").fillna(0).astype(int)
        df["PinHash"] = df["PinHash"].astype("string")
        df.loc[df["PinHash"].isin([None, pd.NA, "nan", "NaN", "None"]), "PinHash"] = None
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_users(df):
    cols = ["Name","CreatedAt","IsBanned","PinHash"]
    for c in cols:
        if c not in df.columns: df[c] = None
    df["IsBanned"] = pd.to_numeric(df.get("IsBanned", 0), errors="coerce").fillna(0).astype(int)
    df[cols].to_csv(USERS_FILE, index=False)
# ─────────────────────────────
# OTP PIN Reset (Admin generates OTP, user resets PIN)
# ─────────────────────────────
OTP_FILE = os.path.join(DATA_DIR, "otp_reset.json")

def _load_otp_store() -> dict:
    if os.path.exists(OTP_FILE) and os.path.getsize(OTP_FILE) > 0:
        try:
            with open(OTP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_otp_store(store: dict) -> None:
    try:
        with open(OTP_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def otp_generate(username: str, minutes_valid: int = 10) -> str:
    username = (username or "").strip()
    code = f"{secrets.randbelow(10**6):06d}"
    expires_at = (datetime.now(ZoneInfo("UTC")) + timedelta(minutes=minutes_valid)).isoformat()

    store = _load_otp_store()
    store[username] = {"code": code, "expires_at": expires_at}
    _save_otp_store(store)
    return code

def otp_clear(username: str) -> None:
    store = _load_otp_store()
    store.pop(username.strip(), None)
    _save_otp_store(store)

def otp_verify(username: str, code: str) -> bool:
    username = username.strip()
    code = normalize_digits(code or "").strip()

    store = _load_otp_store()
    entry = store.get(username)
    if not entry:
        return False

    if entry["code"] != code:
        return False

    exp = parse_iso_dt(entry["expires_at"])
    if not exp or datetime.now(ZoneInfo("UTC")) > exp:
        return False

    return True

def set_user_pin(username: str, new_pin: str) -> bool:
    if not re.fullmatch(r"\d{4}", normalize_digits(new_pin or "")):
        return False

    users_df = load_users()
    mask = users_df["Name"].str.casefold() == username.casefold()
    if not mask.any():
        return False

    users_df.loc[mask, "PinHash"] = _hash_pin(normalize_digits(new_pin))
    save_users(users_df)
    return True

# ─────────────────────────────
# Scoring helpers
# ─────────────────────────────
def split_match_name(match_name: str) -> tuple[str, str]:
    parts = re.split(r"\s*vs\s*", str(match_name or ""), flags=re.IGNORECASE)
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return (match_name or "").strip(), ""

def normalize_score_pair(score_str: str) -> tuple[int,int] | None:
    if not isinstance(score_str, str) or "-" not in score_str:
        return None
    try:
        a, b = map(int, score_str.split("-"))
    except Exception:
        return None
    if a == b:
        return (a, b)
    return (max(a, b), min(a, b))  # order-insensitive

def get_real_winner(match_row: pd.Series) -> str:
    rw = str(match_row.get("RealWinner") or "").strip()
    if rw:
        if rw.casefold() in {"draw", "تعادل"}:
            return "Draw"
        return rw
    result = match_row.get("Result")
    match_name = match_row.get("Match") or ""
    if not isinstance(result, str) or "-" not in result:
        return "Draw"
    try:
        team_a, team_b = [p.strip() for p in re.split(r"\s*vs\s*", match_name, flags=re.IGNORECASE)]
    except Exception:
        team_a, team_b = "A", "B"
    r_a, r_b = map(int, result.split("-"))
    if r_a == r_b:
        return "Draw"
    return team_a if r_a > r_b else team_b

def points_for_prediction(match_row: pd.Series, pred: str, big_game: bool, chosen_winner: str) -> tuple[int,int,int]:
    """
    (points, exact_flag, outcome_flag)
    exact is order-insensitive
    scoring:
      Normal match: exact=3, outcome=1
      Golden match: exact=6, outcome=2
    """
    real = match_row.get("Result")
    if not isinstance(real, str) or not isinstance(pred, str):
        return (0,0,0)

    real_pair = normalize_score_pair(real)
    pred_pair = normalize_score_pair(pred)
    if real_pair is None or pred_pair is None:
        return (0,0,0)

    # exact score (order-insensitive)
    if real_pair == pred_pair:
        return (6 if big_game else 3, 1, 0)

    # outcome (winner or draw)
    real_w = get_real_winner(match_row)
    pred_draw = (pred_pair[0] == pred_pair[1])

    if real_w == "Draw" and pred_draw:
        return (2 if big_game else 1, 0, 1)

    if real_w != "Draw" and isinstance(chosen_winner, str) and chosen_winner.strip() == real_w:
        return (2 if big_game else 1, 0, 1)

    return (0,0,0)

def _load_all_matches_for_scoring() -> pd.DataFrame:
    open_m = load_csv(
        MATCHES_FILE,
        ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"]
    )
    hist_m = load_csv(
        MATCH_HISTORY_FILE,
        ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"]
    )
    if not hist_m.empty:
        hist_m = hist_m.drop(columns=["CompletedAt"], errors="ignore")
    if open_m.empty and hist_m.empty:
        return pd.DataFrame(columns=open_m.columns)
    return pd.concat([open_m, hist_m], ignore_index=True)

def recompute_leaderboard(predictions_df: pd.DataFrame) -> pd.DataFrame:
    cols = ["User","Points","Predictions","Exact","Outcome"]
    lb = pd.DataFrame(columns=cols)
    if predictions_df.empty:
        save_csv(lb, LEADERBOARD_FILE)
        return lb

    matches_full = _load_all_matches_for_scoring()
    if matches_full.empty:
        save_csv(lb, LEADERBOARD_FILE)
        return lb

    preds = predictions_df.copy()
    preds["SubmittedAt"] = pd.to_datetime(preds["SubmittedAt"], errors="coerce")
    preds = preds.sort_values(["User","Match","SubmittedAt"])
    latest = preds.drop_duplicates(subset=["User","Match"], keep="last")

    rows = []
    for _, p in latest.iterrows():
        mrow = matches_full[matches_full["Match"] == p["Match"]]
        if mrow.empty: continue
        m = mrow.iloc[0]
        real = m["Result"]
        if not isinstance(real, str) or "-" not in str(real): continue
        big = bool(m["BigGame"])
        chosen_winner = str(p.get("Winner") or "")
        pts, ex, out = points_for_prediction(m, str(p["Prediction"]), big, chosen_winner)
        rows.append({"User": p["User"], "Points": pts, "Exact": ex, "Outcome": out})

    if not rows:
        save_csv(lb, LEADERBOARD_FILE)
        return lb

    per = pd.DataFrame(rows)
    lb = (
        per.groupby("User", as_index=False)
           .agg(
               Points=("Points","sum"),
               Predictions=("Points","count"),
               Exact=("Exact","sum"),
               Outcome=("Outcome","sum")
           )
    )
    lb = lb.sort_values(["Points","Predictions","Exact"], ascending=[False, True, False])
    save_csv(lb, LEADERBOARD_FILE)
    return lb
# ─────────────────────────────
# Auth pages
# ─────────────────────────────
def page_login(LANG_CODE: str):
    apply_theme()
    st.title(tr(LANG_CODE, "login_tab"))

    role = st.radio(
        "",
        [tr(LANG_CODE, "user_login"), tr(LANG_CODE, "admin_login")],
        horizontal=True,
        key="login_role_selector"
    )

    if role == tr(LANG_CODE, "user_login"):
        users_df = load_users()
        st.subheader(tr(LANG_CODE, "user_login"))
        name_in = st.text_input(tr(LANG_CODE, "your_name"), key="login_name")
        pin_in  = st.text_input(
            "PIN (4 digits)" if LANG_CODE=="en" else "الرقم السري (4 أرقام)",
            type="password",
            key="login_pin"
        )
        name_norm = (name_in or "").strip()

        if st.button(tr(LANG_CODE, "login"), key="btn_user_login"):
            if not name_norm or not re.fullmatch(r"\d{4}", normalize_digits(pin_in or "")):
                st.error(tr(LANG_CODE, "please_login_first"))
            else:
                candidates = users_df[
                    users_df["Name"].astype(str).str.strip().str.casefold() == name_norm.casefold()
                ]
                if candidates.empty:
                    st.error(tr(LANG_CODE, "please_login_first"))
                else:
                    row = candidates.iloc[0]
                    if int(row.get("IsBanned",0)) == 1:
                        st.error("User is banned." if LANG_CODE=="en" else "المستخدم محظور.")
                    else:
                        if _verify_pin(row.get("PinHash"), normalize_digits(pin_in)):
                            st.session_state["role"] = "user"
                            st.session_state["current_name"] = str(row["Name"]).strip()
                            st.success(tr(LANG_CODE, "login_ok"))
                            st.rerun()
                        else:
                            st.error("Wrong PIN." if LANG_CODE=="en" else "الرقم السري غير صحيح.")

        st.markdown("---")
        st.subheader(tr(LANG_CODE, "register"))
        reg_name = st.text_input(tr(LANG_CODE, "your_name"), key="reg_name")
        reg_pin  = st.text_input(
            "Choose a 4-digit PIN" if LANG_CODE=="en" else "اختر رقماً سرياً من 4 أرقام",
            type="password",
            key="reg_pin"
        )

        if st.button(tr(LANG_CODE, "register"), key="btn_register"):
            if not reg_name or not reg_name.strip():
                st.error(tr(LANG_CODE, "need_name"))
            elif not re.fullmatch(r"\d{4}", normalize_digits(reg_pin or "")):
                st.error("PIN must be 4 digits." if LANG_CODE=="en" else "الرقم السري يجب أن يكون 4 أرقام.")
            else:
                users_df = load_users()
                exists = users_df["Name"].astype(str).str.strip().str.casefold().eq(
                    reg_name.strip().casefold()
                ).any()
                if exists:
                    st.error(
                        "Name already exists. Please choose a different name."
                        if LANG_CODE=="en"
                        else "الاسم موجود مسبقًا. الرجاء اختيار اسم مختلف."
                    )
                else:
                    new_row = pd.DataFrame([{
                        "Name": reg_name.strip(),
                        "CreatedAt": datetime.now(ZoneInfo("UTC")).isoformat(),
                        "IsBanned": 0,
                        "PinHash": _hash_pin(normalize_digits(reg_pin))
                    }])
                    users_df = pd.concat([users_df, new_row], ignore_index=True)
                    save_users(users_df)
                    st.success(tr(LANG_CODE, "login_ok"))
                    st.session_state["role"] = "user"
                    st.session_state["current_name"] = reg_name.strip()
                    st.rerun()

    else:
        st.subheader(tr(LANG_CODE, "admin_login"))
        pwd = st.text_input(tr(LANG_CODE, "admin_pass"), type="password")
        if st.button(tr(LANG_CODE, "admin_login"), key="btn_admin_login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state["role"] = "admin"
                st.session_state["current_name"] = "Admin"
                st.success(tr(LANG_CODE, "admin_ok"))
                st.rerun()
            else:
                st.error(tr(LANG_CODE, "admin_bad"))

# ─────────────────────────────
# Play & Leaderboard (User)
# ─────────────────────────────
def page_play_and_leaderboard(LANG_CODE: str, tz: ZoneInfo):
    apply_theme()

    season_name = ""
    if os.path.exists(SEASON_FILE):
        try:
            with open(SEASON_FILE, "r", encoding="utf-8") as f:
                season_name = f.read().strip()
        except Exception:
            pass

    st.title(
        f"{tr(LANG_CODE, 'app_title')}" + (f" — {season_name}" if season_name else "")
    )
    show_welcome_top_right(st.session_state.get("current_name"), LANG_CODE)

    matches_df = load_csv(
        MATCHES_FILE,
        ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"]
    )
    predictions_df = load_csv(
        PREDICTIONS_FILE,
        ["User","Match","Prediction","Winner","SubmittedAt"]
    )

    tab1, tab2 = st.tabs([
        f"🎮 {tr(LANG_CODE,'tab_play')}",
        f"🏆 {tr(LANG_CODE,'tab_leaderboard')}"
    ])

    # ---------- Play ----------
    with tab1:
        current_name = st.session_state.get("current_name")
        if matches_df.empty:
            st.info(tr(LANG_CODE, "no_matches"))
        else:
            tmp = matches_df.copy()
            tmp["KO"] = tmp["Kickoff"].apply(parse_iso_dt)
            tmp = tmp.sort_values("KO").reset_index(drop=True)

            for idx, row in tmp.iterrows():
                match = row["Match"]
                team_a, team_b = split_match_name(match)
                ko = row["KO"]
                big = bool(row.get("BigGame", False))

                with st.container():
                    c_logo_a, c_logo_mid, c_logo_b = st.columns([1,1,1])
                    with c_logo_a:
                        show_logo_safe(row.get("HomeLogo"), width=56, caption=team_a or " ")
                    with c_logo_mid:
                        show_logo_safe(row.get("OccasionLogo"), width=56, caption=row.get("Occasion") or " ")
                    with c_logo_b:
                        show_logo_safe(row.get("AwayLogo"), width=56, caption=team_b or " ")

                    st.markdown(f"### {team_a} &nbsp;vs&nbsp; {team_b}")

                    aux = []
                    if row.get("Round"): aux.append(f"**{tr(LANG_CODE,'round')}**: {row.get('Round')}")
                    if row.get("Occasion"): aux.append(f"**{tr(LANG_CODE,'occasion')}**: {row.get('Occasion')}")
                    if aux: st.caption(" | ".join(aux))

                    ko_txt = format_dt_ampm(ko, tz, LANG_CODE)
                    st.caption(f"{tr(LANG_CODE,'kickoff')}: {ko_txt}")

                    if big:
                        st.markdown(
                            f"<span class='badge-gold'>{tr(LANG_CODE,'gold_badge')}</span>",
                            unsafe_allow_html=True
                        )

                    if ko:
                        open_at = (to_tz(ko, tz) - timedelta(hours=2))
                        now_local = datetime.now(tz)

                        if now_local < open_at:
                            remain = open_at - now_local
                            st.info(f"{tr(LANG_CODE,'opens_in')}: {human_delta(remain, LANG_CODE)}")
                        elif open_at <= now_local < to_tz(ko, tz):
                            if not current_name:
                                st.warning(tr(LANG_CODE, "please_login_first"))
                            else:
                                already = predictions_df[
                                    (predictions_df["User"] == current_name) &
                                    (predictions_df["Match"] == match)
                                ]
                                if not already.empty:
                                    st.info(tr(LANG_CODE, "already_submitted"))
                                else:
                                    short_hash = abs(hash(match)) % 1_000_000_000
                                    score_key = f"pred_score_{idx}_{short_hash}"
                                    sel_key   = f"pred_winner_{idx}_{short_hash}"
                                    btn_key   = f"btn_{idx}_{short_hash}"

                                    raw = st.text_input(tr(LANG_CODE,"score"), key=score_key)
                                    val = normalize_digits(raw or "")

                                    options = [team_a, team_b, tr(LANG_CODE,"draw")]
                                    is_draw_typed = bool(
                                        re.fullmatch(r"\s*(\d{1,2})-(\d{1,2})\s*", val)
                                        and val.split("-")[0] == val.split("-")[1]
                                    )
                                    default_ix = 2 if is_draw_typed else 0
                                    winner = st.selectbox(
                                        tr(LANG_CODE,"winner"),
                                        options=options,
                                        index=default_ix,
                                        key=sel_key,
                                        disabled=is_draw_typed
                                    )

                                    if st.button(tr(LANG_CODE,"submit_btn"), key=btn_key):
                                        if not re.fullmatch(r"\d{1,2}-\d{1,2}", val):
                                            st.error(tr(LANG_CODE,"fmt_error"))
                                        else:
                                            h1, h2 = map(int, val.split("-"))
                                            if not (0 <= h1 <= 20 and 0 <= h2 <= 20):
                                                st.error(tr(LANG_CODE,"range_error"))
                                            else:
                                                if h1 == h2:
                                                    winner = tr(LANG_CODE,"draw")
                                                new_pred = pd.DataFrame([{
                                                    "User": current_name,
                                                    "Match": match,
                                                    "Prediction": f"{h1}-{h2}",
                                                    "Winner": winner,
                                                    "SubmittedAt": datetime.now(ZoneInfo("UTC")).isoformat()
                                                }])
                                                predictions_df = pd.concat(
                                                    [predictions_df, new_pred],
                                                    ignore_index=True
                                                )
                                                save_csv(predictions_df, PREDICTIONS_FILE)
                                                recompute_leaderboard(predictions_df)
                                                st.success(tr(LANG_CODE, "saved_ok"))
                        else:
                            st.caption(f"🔒 {tr(LANG_CODE,'closed')}")

    # ---------- Leaderboard ----------
    with tab2:
        preds = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
        lb = recompute_leaderboard(preds)
        st.subheader(tr(LANG_CODE,"leaderboard"))
        if lb.empty:
            st.info(tr(LANG_CODE,"no_scores_yet"))
        else:
            lb = lb.reset_index(drop=True)
            lb.insert(0, tr(LANG_CODE, "lb_rank"), range(1, len(lb) + 1))

            medal = []
            for i in lb.index:
                r_int = int(str(lb.loc[i, tr(LANG_CODE, "lb_rank")]).split()[0])
                medal.append("🥇" if r_int==1 else "🥈" if r_int==2 else "🥉" if r_int==3 else "")
            lb[tr(LANG_CODE,"lb_rank")] = lb[tr(LANG_CODE,"lb_rank")].astype(str) + " " + pd.Series(medal)

            col_map = {
                "User": tr(LANG_CODE,"lb_user"),
                "Predictions": tr(LANG_CODE,"lb_preds"),
                "Exact": tr(LANG_CODE,"lb_exact"),
                "Outcome": tr(LANG_CODE,"lb_outcome"),
                "Points": tr(LANG_CODE,"lb_points")
            }
            show = lb[
                [tr(LANG_CODE,"lb_rank"), "User","Predictions","Exact","Outcome","Points"]
            ].rename(columns=col_map)
            st.dataframe(show, use_container_width=True)
# ─────────────────────────────
# Admin page
# ─────────────────────────────
def page_admin(LANG_CODE: str, tz: ZoneInfo):
    apply_theme()
    st.title(tr(LANG_CODE, "admin_panel"))
    show_welcome_top_right("Admin", LANG_CODE)

    matches_df = load_csv(
        MATCHES_FILE,
        ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"]
    )
    history_df = ensure_history_schema(
        load_csv(
            MATCH_HISTORY_FILE,
            ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"]
        )
    )
    preds_df = load_csv(
        PREDICTIONS_FILE,
        ["User","Match","Prediction","Winner","SubmittedAt"]
    )
    users_df = load_users()

    tab_add, tab_edit, tab_users, tab_backup = st.tabs([
        f"➕ {tr(LANG_CODE,'admin_add_match')}",
        f"✏️ {tr(LANG_CODE,'admin_edit_match')}",
        f"👥 {tr(LANG_CODE,'admin_users')}",
        f"💾 {tr(LANG_CODE,'admin_backup')}",
    ])

    # ---------- Add match ----------
    with tab_add:
        st.subheader(tr(LANG_CODE,"admin_add_match"))

        team_a = st.text_input(tr(LANG_CODE,"team_a"))
        team_b = st.text_input(tr(LANG_CODE,"team_b"))
        ko = st.date_input(tr(LANG_CODE,"kickoff_date"))
        ko_t = st.time_input(tr(LANG_CODE,"kickoff_time"))
        big = st.checkbox(tr(LANG_CODE,"gold_badge"))
        occasion = st.text_input(tr(LANG_CODE,"occasion"))
        round_name = st.text_input(tr(LANG_CODE,"round"))

        col1, col2 = st.columns(2)
        with col1:
            home_logo_url = st.text_input(tr(LANG_CODE,"home_logo_url"))
            home_logo_file = st.file_uploader(
                tr(LANG_CODE,"home_logo_upload"),
                type=["png","jpg","jpeg"],
                key="home_logo_up"
            )
        with col2:
            away_logo_url = st.text_input(tr(LANG_CODE,"away_logo_url"))
            away_logo_file = st.file_uploader(
                tr(LANG_CODE,"away_logo_upload"),
                type=["png","jpg","jpeg"],
                key="away_logo_up"
            )

        occ_logo_url = st.text_input(tr(LANG_CODE,"occasion_logo_url"))
        occ_logo_file = st.file_uploader(
            tr(LANG_CODE,"occasion_logo_upload"),
            type=["png","jpg","jpeg"],
            key="occ_logo_up"
        )

        if st.button(tr(LANG_CODE,"add_match_btn")):
            if not team_a or not team_b:
                st.error(tr(LANG_CODE,"need_teams"))
            else:
                match_name = f"{team_a.strip()} vs {team_b.strip()}"
                kickoff = datetime.combine(ko, ko_t).replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))

                hlogo = cache_logo_from_url(home_logo_url) if home_logo_url else None
                if home_logo_file:
                    hlogo = save_uploaded_logo(home_logo_file, team_a)

                alogo = cache_logo_from_url(away_logo_url) if away_logo_url else None
                if away_logo_file:
                    alogo = save_uploaded_logo(away_logo_file, team_b)

                ologo = cache_logo_from_url(occ_logo_url) if occ_logo_url else None
                if occ_logo_file:
                    ologo = save_uploaded_logo(occ_logo_file, occasion or "occasion")

                save_team_logo(team_a, hlogo)
                save_team_logo(team_b, alogo)

                new_row = pd.DataFrame([{
                    "Match": match_name,
                    "Kickoff": kickoff.isoformat(),
                    "Result": None,
                    "HomeLogo": hlogo,
                    "AwayLogo": alogo,
                    "BigGame": int(big),
                    "RealWinner": None,
                    "Occasion": occasion,
                    "OccasionLogo": ologo,
                    "Round": round_name,
                }])
                matches_df = pd.concat([matches_df, new_row], ignore_index=True)
                save_csv(matches_df, MATCHES_FILE)
                st.success(tr(LANG_CODE,"saved_ok"))
                st.rerun()

    # ---------- Edit / Close match ----------
    with tab_edit:
        st.subheader(tr(LANG_CODE,"admin_edit_match"))

        if matches_df.empty:
            st.info(tr(LANG_CODE,"no_matches"))
        else:
            sel = st.selectbox(
                tr(LANG_CODE,"select_match"),
                matches_df["Match"].tolist()
            )
            row = matches_df[matches_df["Match"] == sel].iloc[0]

            result = st.text_input(tr(LANG_CODE,"final_result"), value=row.get("Result") or "")
            real_w = st.selectbox(
                tr(LANG_CODE,"winner"),
                [split_match_name(sel)[0], split_match_name(sel)[1], tr(LANG_CODE,"draw")],
                index=0
            )

            if st.button(tr(LANG_CODE,"close_match")):
                idx = matches_df.index[matches_df["Match"] == sel][0]
                matches_df.at[idx,"Result"] = normalize_digits(result)
                matches_df.at[idx,"RealWinner"] = real_w if real_w != tr(LANG_CODE,"draw") else "Draw"

                done = matches_df.loc[idx].to_dict()
                done["CompletedAt"] = datetime.now(ZoneInfo("UTC")).isoformat()

                history_df = pd.concat([history_df, pd.DataFrame([done])], ignore_index=True)
                matches_df = matches_df.drop(index=idx).reset_index(drop=True)

                save_csv(matches_df, MATCHES_FILE)
                save_csv(history_df, MATCH_HISTORY_FILE)
                recompute_leaderboard(preds_df)
                st.success(tr(LANG_CODE,"saved_ok"))
                st.rerun()

    # ---------- Users ----------
    with tab_users:
        st.subheader(tr(LANG_CODE,"admin_users"))

        if users_df.empty:
            st.info(tr(LANG_CODE,"no_users"))
        else:
            sel_user = st.selectbox(
                tr(LANG_CODE,"select_user"),
                users_df["Name"].tolist()
            )
            uidx = users_df.index[users_df["Name"] == sel_user][0]

            ban = st.checkbox(
                tr(LANG_CODE,"ban_user"),
                value=bool(users_df.at[uidx,"IsBanned"])
            )

            if st.button(tr(LANG_CODE,"save_user")):
                users_df.at[uidx,"IsBanned"] = int(ban)
                save_users(users_df)
                st.success(tr(LANG_CODE,"saved_ok"))
                st.rerun()

    # ---------- Backup / Restore ----------
    with tab_backup:
        st.subheader(tr(LANG_CODE,"backup_restore"))

        backup_bytes = _backup_zip_bytes()
        st.download_button(
            tr(LANG_CODE,"download_backup"),
            data=backup_bytes,
            file_name="football_predictions_backup.zip",
            mime="application/zip"
        )

        up = st.file_uploader(
            tr(LANG_CODE,"restore_backup"),
            type=["zip"],
            key="restore_zip"
        )

        if up is not None:
            if st.button(tr(LANG_CODE,"restore_now")):
                try:
                    _restore_from_zip_bytes(up.read())
                    st.success(tr(LANG_CODE,"restore_ok"))
                    st.rerun()
                except Exception as e:
                    st.error(tr(LANG_CODE,"restore_fail"))
                    st.exception(e)
# ─────────────────────────────
# Router & App runner
# ─────────────────────────────
def run_app():
    # Sidebar — language
    st.sidebar.subheader(tr("en","sidebar_lang") + " / " + tr("ar","sidebar_lang"))
    lang_choice = st.sidebar.radio(
        "",
        [tr("en","lang_en"), tr("ar","lang_ar")],
        index=0,
        horizontal=True
    )
    LANG_CODE = "ar" if lang_choice == tr("ar","lang_ar") else "en"

    # Sidebar — timezone
    st.sidebar.subheader(tr(LANG_CODE,"sidebar_time"))

    _setup_browser_timezone_param()
    detected_tz = _get_tz_from_query_params(default_tz="Asia/Riyadh") or "Asia/Riyadh"

    common_tz = [
        "UTC",
        "Europe/London","Europe/Madrid","Europe/Paris","Europe/Berlin","Europe/Rome",
        "Africa/Cairo",
        "Asia/Riyadh","Asia/Dubai","Asia/Kolkata","Asia/Singapore","Asia/Tokyo",
        "Asia/Shanghai","Asia/Hong_Kong",
        "Australia/Sydney",
        "America/Sao_Paulo",
        "America/New_York","America/Chicago","America/Denver","America/Los_Angeles",
    ]
    if detected_tz not in common_tz:
        common_tz.insert(0, detected_tz)

    label_auto = f"🧭 {detected_tz}"
    tz_choice = st.sidebar.selectbox(
        tr(LANG_CODE,"app_timezone"),
        [label_auto] + common_tz,
        index=0
    )
    tz_str = detected_tz if tz_choice == label_auto else tz_choice

    # persist tz in URL (new Streamlit API)
    try:
        st.query_params["tz"] = tz_str
    except Exception:
        pass

    tz = ZoneInfo(tz_str)

    # Logout
    if st.sidebar.button("Logout" if LANG_CODE=="en" else "تسجيل الخروج"):
        st.session_state.clear()
        st.rerun()

    # Routing
    role = st.session_state.get("role")

    if role == "user":
        page_play_and_leaderboard(LANG_CODE, tz)
    elif role == "admin":
        page_admin(LANG_CODE, tz)
    else:
        page_login(LANG_CODE)


# ─────────────────────────────
# Entry point
# ─────────────────────────────
if __name__ == "__main__":
    run_app()
