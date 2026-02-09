# =========================
# app.py  (PART 1/6)
# =========================
import os, re, json, hashlib, secrets
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

# NEW: overrides store for manual admin edits (Predictions & Points)
LEADERBOARD_OVERRIDES_FILE = os.path.join(DATA_DIR, "leaderboard_overrides.csv")

# OTP store (admin generates OTP; user uses it to reset PIN)
OTP_FILE = os.path.join(DATA_DIR, "otp_reset.csv")

ADMIN_PASSWORD = "madness"

# ─────────────────────────────
# Backup / Restore helpers
# ─────────────────────────────
import zipfile
from io import BytesIO

BACKUP_FILES = [
    USERS_FILE,
    MATCHES_FILE,
    MATCH_HISTORY_FILE,
    PREDICTIONS_FILE,
    LEADERBOARD_FILE,
    SEASON_FILE,
    TEAM_LOGOS_FILE,
    LEADERBOARD_OVERRIDES_FILE,
    OTP_FILE,
]

def create_backup_zip() -> BytesIO:
    """Create an in-memory ZIP of all game data files."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in BACKUP_FILES:
            try:
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    z.write(path, arcname=os.path.basename(path))
            except Exception:
                pass
    buf.seek(0)
    return buf

def restore_from_zip(filelike) -> None:
    """Extract ZIP into DATA_DIR, overwriting existing files (only known files)."""
    with zipfile.ZipFile(filelike, "r") as z:
        allowed = {os.path.basename(p) for p in BACKUP_FILES}
        for member in z.namelist():
            base = os.path.basename(member)
            if base in allowed:
                z.extract(member, DATA_DIR)

# Optional: save backups to Supabase Storage if configured (silent no-op if not)
def _get_supabase_client():
    try:
        from supabase import create_client
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_SERVICE_ROLE") or st.secrets.get("SUPABASE_ANON_KEY")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None

def upload_backup_to_supabase(buf: BytesIO, bucket: str = "backups") -> str | None:
    """
    Upload the in-memory ZIP to Supabase Storage (if configured).
    Returns 'bucket/key' on success, else None.
    """
    sb = _get_supabase_client()
    if not sb:
        return None
    try:
        sb.storage.create_bucket(bucket, public=False)
    except Exception:
        pass
    ts = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%d_%H%M%S")
    key = f"prediction_backups/backup_{ts}.zip"
    try:
        sb.storage.from_(bucket).upload(key, buf.getvalue(), {"content-type": "application/zip"})
        return f"{bucket}/{key}"
    except Exception:
        return None

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
# =========================
# app.py  (PART 2/6)
# =========================

# ─────────────────────────────
# Utilities & persistence
# ─────────────────────────────
def normalize_digits(text: str) -> str:
    if not isinstance(text, str):
        return text
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
            if c not in df.columns:
                df[c] = None
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_csv(df, file):
    df.to_csv(file, index=False)

# ─────────────────────────────
# Manual overrides helpers
# ─────────────────────────────
def load_overrides() -> pd.DataFrame:
    return load_csv(LEADERBOARD_OVERRIDES_FILE, ["User","Predictions","Points"])

def save_overrides(df: pd.DataFrame):
    save_csv(df, LEADERBOARD_OVERRIDES_FILE)

# ─────────────────────────────
# PIN helpers (hashed)
# ─────────────────────────────
def _hash_pin(pin: str) -> str:
    salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + pin).encode("utf-8")).hexdigest()
    return f"{salt}:{h}"

def _verify_pin(stored: str | None, pin: str) -> bool:
    try:
        if stored is None:
            return False
        if isinstance(stored, float) and pd.isna(stored):
            return False
        s = str(stored)
        if ":" not in s:
            return False
        salt, h = s.split(":", 1)
        return hashlib.sha256((salt + pin).encode("utf-8")).hexdigest() == h
    except Exception:
        return False

# ─────────────────────────────
# OTP (admin generates; user resets PIN)
# ─────────────────────────────
def _otp_load() -> pd.DataFrame:
    return load_csv(OTP_FILE, ["User", "CodeHash", "ExpiresAt", "UsedAt", "CreatedAt"])

def _otp_save(df: pd.DataFrame):
    save_csv(df, OTP_FILE)

def _otp_hash(code: str) -> str:
    salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + code).encode("utf-8")).hexdigest()
    return f"{salt}:{h}"

def _otp_verify(codehash: str, code: str) -> bool:
    try:
        if not codehash or ":" not in str(codehash):
            return False
        salt, h = str(codehash).split(":", 1)
        return hashlib.sha256((salt + code).encode("utf-8")).hexdigest() == h
    except Exception:
        return False

def otp_cleanup_expired():
    """Remove expired/used OTP entries to keep file small."""
    df = _otp_load()
    if df.empty:
        return
    now = datetime.now(ZoneInfo("UTC"))
    df["ExpiresAt_dt"] = pd.to_datetime(df["ExpiresAt"], errors="coerce")
    df["UsedAt_dt"] = pd.to_datetime(df["UsedAt"], errors="coerce")
    keep = df["UsedAt_dt"].isna() & (df["ExpiresAt_dt"] > now)
    df = df.loc[keep, ["User","CodeHash","ExpiresAt","UsedAt","CreatedAt"]]
    _otp_save(df)

def otp_revoke(user: str):
    """Revoke any active OTP for user."""
    df = _otp_load()
    if df.empty:
        return
    u = str(user or "").strip()
    if not u:
        return
    df = df[df["User"].astype(str).str.strip().str.casefold() != u.casefold()]
    _otp_save(df)

def otp_generate(user: str, minutes_valid: int = 10) -> str:
    """
    Create a new OTP for a user. Returns the plain code to show admin once.
    Replaces any existing OTP for that user.
    """
    otp_cleanup_expired()
    u = str(user or "").strip()
    if not u:
        return ""
    otp_revoke(u)

    code = f"{secrets.randbelow(1000000):06d}"  # 6-digit
    now = datetime.now(ZoneInfo("UTC"))
    exp = now + timedelta(minutes=int(minutes_valid))

    df = _otp_load()
    row = pd.DataFrame([{
        "User": u,
        "CodeHash": _otp_hash(code),
        "ExpiresAt": exp.isoformat(),
        "UsedAt": "",
        "CreatedAt": now.isoformat(),
    }])
    df = pd.concat([df, row], ignore_index=True)
    _otp_save(df)
    return code

def otp_validate(user: str, code: str) -> tuple[bool, str]:
    """
    Validate OTP without consuming it.
    Returns (ok, message)
    """
    otp_cleanup_expired()
    u = str(user or "").strip()
    c = normalize_digits(str(code or "").strip())
    if not u or not c:
        return (False, "Missing user/code")

    df = _otp_load()
    if df.empty:
        return (False, "No OTP found")

    match = df[df["User"].astype(str).str.strip().str.casefold() == u.casefold()]
    if match.empty:
        return (False, "No OTP for this user")

    row = match.iloc[-1]
    if str(row.get("UsedAt") or "").strip():
        return (False, "OTP already used")

    exp = pd.to_datetime(row.get("ExpiresAt"), errors="coerce")
    now = datetime.now(ZoneInfo("UTC"))
    if pd.isna(exp) or exp <= now:
        return (False, "OTP expired")

    if not _otp_verify(str(row.get("CodeHash") or ""), c):
        return (False, "Wrong OTP")

    return (True, "OK")

def otp_consume(user: str, code: str) -> tuple[bool, str]:
    """
    Validate and mark OTP as used.
    """
    ok, msg = otp_validate(user, code)
    if not ok:
        return (False, msg)

    df = _otp_load()
    u = str(user or "").strip()
    now = datetime.now(ZoneInfo("UTC")).isoformat()

    mask = df["User"].astype(str).str.strip().str.casefold() == u.casefold()
    if not mask.any():
        return (False, "No OTP for this user")

    # mark latest as used
    idxs = df.index[mask].tolist()
    last_idx = idxs[-1]
    df.at[last_idx, "UsedAt"] = now
    _otp_save(df)
    return (True, "OK")

# ─────────────────────────────
# Date/time helpers
# ─────────────────────────────
def parse_iso_dt(val):
    try:
        return datetime.fromisoformat(str(val)) if pd.notna(val) and val else None
    except Exception:
        return None

def to_tz(dt: datetime | None, tz: ZoneInfo) -> datetime | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)

def format_dt_ampm(dt: datetime | None, tz: ZoneInfo, lang="en") -> str:
    if not dt:
        return ""
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
        day_w  = ("يوم" if days==1 else "ايام")
        hour_w = ("ساعة" if hours==1 else "ساعات")
        min_w  = ("دقيقة" if minutes==1 else "دقائق")
        parts = []
        if days:
            parts.append(f"{days} {day_w}")
        parts.append(f"{hours} {hour_w}")
        parts.append(f"{minutes} {min_w}")
        return " ".join(parts)
    parts = []
    if days:
        parts.append(f"{days} {'day' if days==1 else 'days'}")
    parts.append(f"{hours} {'hour' if hours==1 else 'hours'}")
    parts.append(f"{minutes} {'minute' if minutes==1 else 'minutes'}")
    return " ".join(parts)

# ─────────────────────────────
# Logo helpers
# ─────────────────────────────
def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    base = os.path.basename(parsed.path) or "logo.png"
    ext = os.path.splitext(base)[1] or ".png"
    stem = hashlib.md5(url.encode()).hexdigest()
    return f"{stem}{ext}"

def cache_logo_from_url(url: str) -> str | None:
    if not (isinstance(url, str) and url.lower().startswith(("http://","https://"))):
        return None
    try:
        fname = _filename_from_url(url)
        path = os.path.join(LOGO_DIR, fname)
        if os.path.exists(path):
            return path
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception:
        return None

def save_uploaded_logo(file, name_hint: str) -> str | None:
    try:
        ext = os.path.splitext(file.name)[1] or ".png"
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name_hint or "logo")
        path = os.path.join(LOGO_DIR, f"{safe}{ext}")
        with open(path, "wb") as f:
            f.write(file.read())
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
    if not team or not logo_path_or_url:
        return
    logos = _load_team_logos()
    logos[team] = logo_path_or_url
    _save_team_logos(logos)

def get_saved_logo(team: str) -> str | None:
    logos = _load_team_logos()
    return logos.get(team or "", None)

def ensure_history_schema(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols]

def show_logo_safe(img_ref, width=56, caption=""):
    try:
        if not img_ref or (isinstance(img_ref, float) and pd.isna(img_ref)):
            return
        s = str(img_ref).strip()
        if not s:
            return
        if os.path.exists(s) or s.lower().startswith(("http://", "https://")):
            st.image(s, width=width, caption=caption)
    except Exception:
        pass

# ─────────────────────────────
# Theme + UI helpers
# ─────────────────────────────
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
    if not name:
        return
    label = f"Welcome, <b>{name}</b>" if lang=="en" else f"مرحبًا، <b>{name}</b>"
    st.markdown(f"""<div class="welcome-wrap">{label}</div>""", unsafe_allow_html=True)

# browser timezone detection
def _setup_browser_timezone_param():
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
# =========================
# app.py  (PART 3/6)
# =========================

# ─────────────────────────────
# Users (Name + PIN)
# ─────────────────────────────
def load_users():
    cols = ["Name","CreatedAt","IsBanned","PinHash"]
    if os.path.exists(USERS_FILE) and os.path.getsize(USERS_FILE) > 0:
        df = pd.read_csv(USERS_FILE)
        for c in cols:
            if c not in df.columns:
                df[c] = None
        df["IsBanned"] = pd.to_numeric(df["IsBanned"], errors="coerce").fillna(0).astype(int)
        df["PinHash"] = df["PinHash"].astype("string")
        df.loc[df["PinHash"].isin([None, pd.NA, "nan", "NaN", "None"]), "PinHash"] = None
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_users(df):
    cols = ["Name","CreatedAt","IsBanned","PinHash"]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df["IsBanned"] = pd.to_numeric(df.get("IsBanned", 0), errors="coerce").fillna(0).astype(int)
    df[cols].to_csv(USERS_FILE, index=False)

# ─────────────────────────────
# Scoring helpers
# ─────────────────────────────
def split_match_name(match_name: str) -> tuple[str, str]:
    parts = re.split(r"\s*vs\s*", str(match_name or ""), flags=re.IGNORECASE)
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return (match_name or "").strip(), ""

def normalize_score_pair(score_str: str) -> tuple[int,int] | None:
    """Order-insensitive for non-draws (so 2-1 == 1-2). Draw remains (x,x)."""
    if not isinstance(score_str, str) or "-" not in score_str:
        return None
    try:
        a, b = map(int, score_str.split("-"))
    except Exception:
        return None
    if a == b:
        return (a, b)
    return (max(a, b), min(a, b))

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
    """(points, exact_flag, outcome_flag) using 6-2 for big games and 3-1 for normal."""
    real = match_row.get("Result")
    if not isinstance(real, str) or not isinstance(pred, str):
        return (0,0,0)

    real_pair = normalize_score_pair(real)
    pred_pair = normalize_score_pair(pred)
    if real_pair is None or pred_pair is None:
        return (0,0,0)

    # exact
    if real_pair == pred_pair:
        return (6 if big_game else 3, 1, 0)

    # outcome
    real_w = get_real_winner(match_row)
    pred_draw = (pred_pair[0] == pred_pair[1])

    if real_w == "Draw" and pred_draw:
        return (2 if big_game else 1, 0, 1)

    if real_w != "Draw" and isinstance(chosen_winner, str) and chosen_winner.strip() == real_w:
        return (2 if big_game else 1, 0, 1)

    return (0,0,0)

def _load_all_matches_for_scoring() -> pd.DataFrame:
    open_m = load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
    hist_m = load_csv(MATCH_HISTORY_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"])
    if not hist_m.empty:
        hist_m = hist_m.drop(columns=["CompletedAt"], errors="ignore")
    if open_m.empty and hist_m.empty:
        return pd.DataFrame(columns=["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
    return pd.concat([open_m, hist_m], ignore_index=True)

def recompute_leaderboard(predictions_df: pd.DataFrame) -> pd.DataFrame:
    """
    IMPORTANT FIX:
    - Computes base leaderboard from predictions + real match results
    - Then applies overrides (Predictions/Points) and WRITES the APPLIED result to leaderboard.csv
      so USERS see the overridden leaderboard.
    """
    cols = ["User","Points","Predictions","Exact","Outcome"]
    lb_base = pd.DataFrame(columns=cols)

    # no preds → write empty
    if predictions_df.empty:
        save_csv(lb_base, LEADERBOARD_FILE)
        return lb_base

    matches_full = _load_all_matches_for_scoring()
    if matches_full.empty:
        save_csv(lb_base, LEADERBOARD_FILE)
        return lb_base

    preds = predictions_df.copy()
    preds["SubmittedAt"] = pd.to_datetime(preds["SubmittedAt"], errors="coerce")
    preds = preds.sort_values(["User","Match","SubmittedAt"])

    # keep latest per (User, Match)
    latest = preds.drop_duplicates(subset=["User","Match"], keep="last")

    rows = []
    for _, p in latest.iterrows():
        mrow = matches_full[matches_full["Match"] == p["Match"]]
        if mrow.empty:
            continue
        m = mrow.iloc[0]
        real = m["Result"]
        if not isinstance(real, str) or "-" not in str(real):
            continue
        big = bool(m.get("BigGame", False))
        chosen_winner = str(p.get("Winner") or "")
        pts, ex, out = points_for_prediction(m, str(p["Prediction"]), big, chosen_winner)
        rows.append({"User": p["User"], "Points": pts, "Exact": ex, "Outcome": out})

    if not rows:
        save_csv(lb_base, LEADERBOARD_FILE)
        return lb_base

    per = pd.DataFrame(rows)
    lb_base = (per.groupby("User", as_index=False)
                 .agg(Points=("Points","sum"),
                      Predictions=("Points","count"),
                      Exact=("Exact","sum"),
                      Outcome=("Outcome","sum")))

    # sort base
    lb_base = lb_base.sort_values(["Points","Predictions","Exact"], ascending=[False, True, False]).reset_index(drop=True)

    # ---- APPLY OVERRIDES (THIS IS THE FIX USERS NEED) ----
    overrides = load_overrides()

    def _coalesce(a, b):
        return b if pd.notna(b) else a

    if not overrides.empty:
        applied = lb_base.merge(overrides, on="User", how="left", suffixes=("", "_ovr"))
        applied["Predictions"] = applied.apply(lambda r: _coalesce(r.get("Predictions"), r.get("Predictions_ovr")), axis=1)
        applied["Points"]      = applied.apply(lambda r: _coalesce(r.get("Points"),      r.get("Points_ovr")), axis=1)
        applied = applied[["User","Points","Predictions","Exact","Outcome"]]
    else:
        applied = lb_base[["User","Points","Predictions","Exact","Outcome"]].copy()

    applied = applied.sort_values(["Points","Predictions","Exact"], ascending=[False, True, False]).reset_index(drop=True)

    # write APPLIED so user sees it
    save_csv(applied, LEADERBOARD_FILE)
    return applied
# =========================
# app.py  (PART 4/6)
# =========================

# ─────────────────────────────
# Auth pages (Login + Register + OTP PIN Reset)
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

    # ─────────────────────────────
    # USER LOGIN
    # ─────────────────────────────
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
                    if int(row.get("IsBanned", 0)) == 1:
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

        # ─────────────────────────────
        # REGISTER
        # ─────────────────────────────
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
                exists = users_df["Name"].astype(str).str.strip().str.casefold().eq(reg_name.strip().casefold()).any()
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

        st.markdown("---")

        # ─────────────────────────────
        # OTP PIN RESET (USER SIDE)
        # ─────────────────────────────
        st.subheader("🔐 Reset PIN with OTP" if LANG_CODE=="en" else "🔐 إعادة تعيين الرقم السري عبر OTP")
        st.caption(
            "If admin gave you an OTP code, you can reset your PIN here."
            if LANG_CODE=="en"
            else "إذا أعطاك المشرف رمز OTP، يمكنك إعادة تعيين رقمك السري هنا."
        )

        otp_name = st.text_input("Username" if LANG_CODE=="en" else "اسم المستخدم", key="otp_reset_name")
        otp_code = st.text_input("OTP Code" if LANG_CODE=="en" else "رمز OTP", key="otp_reset_code")
        new_pin  = st.text_input(
            "New 4-digit PIN" if LANG_CODE=="en" else "رقم سري جديد من 4 أرقام",
            type="password",
            key="otp_reset_new_pin"
        )

        if st.button("Reset PIN" if LANG_CODE=="en" else "تحديث الرقم السري", key="btn_otp_reset"):
            otp_name_n = (otp_name or "").strip()
            otp_code_n = (otp_code or "").strip()
            new_pin_n  = normalize_digits(new_pin or "")

            if not otp_name_n:
                st.error("Enter username." if LANG_CODE=="en" else "أدخل اسم المستخدم.")
            elif not otp_code_n:
                st.error("Enter OTP code." if LANG_CODE=="en" else "أدخل رمز OTP.")
            elif not re.fullmatch(r"\d{4}", new_pin_n):
                st.error("PIN must be 4 digits." if LANG_CODE=="en" else "الرقم السري يجب أن يكون 4 أرقام.")
            else:
                ok, msg = otp_consume_and_reset_pin(otp_name_n, otp_code_n, new_pin_n)
                if ok:
                    st.success("PIN updated. You can log in now ✅" if LANG_CODE=="en" else "تم تحديث الرقم السري ✅ يمكنك تسجيل الدخول الآن")
                else:
                    st.error(msg)

    # ─────────────────────────────
    # ADMIN LOGIN
    # ─────────────────────────────
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
# =========================
# app.py  (PART 5/6)
# =========================

# ─────────────────────────────
# Play & Leaderboard (User)
# ─────────────────────────────
def _apply_overrides_to_lb(lb_current: pd.DataFrame) -> pd.DataFrame:
    """Apply manual overrides (Predictions/Points) for display to users too."""
    if lb_current is None or lb_current.empty:
        return lb_current

    overrides = load_overrides()
    if overrides is None or overrides.empty:
        return lb_current

    merged = lb_current.merge(overrides, on="User", how="left", suffixes=("", "_ovr"))

    def _coalesce(a, b):
        return b if pd.notna(b) else a

    merged["Predictions"] = merged.apply(lambda r: _coalesce(r.get("Predictions"), r.get("Predictions_ovr")), axis=1)
    merged["Points"]      = merged.apply(lambda r: _coalesce(r.get("Points"),      r.get("Points_ovr")), axis=1)

    merged = merged[["User", "Points", "Predictions", "Exact", "Outcome"]]
    merged = merged.sort_values(["Points", "Predictions", "Exact"], ascending=[False, True, False]).reset_index(drop=True)
    return merged


def page_play_and_leaderboard(LANG_CODE: str, tz: ZoneInfo):
    apply_theme()

    # Season title (if any)
    season_name = ""
    if os.path.exists(SEASON_FILE):
        try:
            with open(SEASON_FILE, "r", encoding="utf-8") as f:
                season_name = f.read().strip()
        except Exception:
            pass

    st.title(f"{tr(LANG_CODE, 'app_title')}" + (f" — {season_name}" if season_name else ""))
    show_welcome_top_right(st.session_state.get("current_name"), LANG_CODE)

    matches_df = load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
    predictions_df = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])

    tab1, tab2 = st.tabs([f"🎮 {tr(LANG_CODE,'tab_play')}", f"🏆 {tr(LANG_CODE,'tab_leaderboard')}"])

    # ------------- Play -------------
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
                    # Logos row
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
                        st.markdown(f"<span class='badge-gold'>{tr(LANG_CODE,'gold_badge')}</span>", unsafe_allow_html=True)

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
                                # reload latest predictions to avoid stale state
                                predictions_df = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])

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
                                        re.fullmatch(r"\s*(\d{1,2})-(\d{1,2})\s*", val) and val.split("-")[0] == val.split("-")[1]
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

                                                predictions_df = pd.concat([predictions_df, new_pred], ignore_index=True)
                                                save_csv(predictions_df, PREDICTIONS_FILE)

                                                # recompute base leaderboard (stored), but user display still applies overrides live
                                                recompute_leaderboard(predictions_df)

                                                st.success(tr(LANG_CODE, "saved_ok"))
                                                st.rerun()
                        else:
                            st.caption(f"🔒 {tr(LANG_CODE,'closed')}")

    # ------------- Leaderboard -------------
    with tab2:
        preds = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])

        # Base leaderboard from predictions (always correct)
        lb_base = recompute_leaderboard(preds)

        # IMPORTANT FIX: apply admin overrides for user view (so users SEE edited Points/Predictions)
        lb = _apply_overrides_to_lb(lb_base)

        st.subheader(tr(LANG_CODE,"leaderboard"))
        if lb.empty:
            st.info(tr(LANG_CODE,"no_scores_yet"))
        else:
            lb = lb.reset_index(drop=True)
            lb.insert(0, tr(LANG_CODE, "lb_rank"), range(1, len(lb) + 1))

            medal = []
            for i in lb.index:
                r_int = int(lb.loc[i, tr(LANG_CODE, "lb_rank")])
                if r_int == 1: medal.append("🥇")
                elif r_int == 2: medal.append("🥈")
                elif r_int == 3: medal.append("🥉")
                else: medal.append("")
            lb[tr(LANG_CODE,"lb_rank")] = lb[tr(LANG_CODE,"lb_rank")].astype(str) + " " + pd.Series(medal)

            col_map = {
                "User": tr(LANG_CODE,"lb_user"),
                "Predictions": tr(LANG_CODE,"lb_preds"),
                "Exact": tr(LANG_CODE,"lb_exact"),
                "Outcome": tr(LANG_CODE,"lb_outcome"),
                "Points": tr(LANG_CODE,"lb_points")
            }
            show = lb[[tr(LANG_CODE,"lb_rank"), "User","Predictions","Exact","Outcome","Points"]].rename(columns=col_map)
            st.dataframe(show, use_container_width=True)
# =========================
# app.py  (PART 6/6)
# =========================

# ─────────────────────────────
# Admin Page (Top Tabs Layout)
# ─────────────────────────────
def page_admin(LANG_CODE: str, tz: ZoneInfo):
    apply_theme()
    st.title(f"🔑 {tr(LANG_CODE,'admin_panel')}")
    show_welcome_top_right(st.session_state.get("current_name") or "Admin", LANG_CODE)

    # ─────────────────────────
    # TOP ADMIN TABS
    # ─────────────────────────
    tab_matches, tab_predictions, tab_settings, tab_manual = st.tabs([
        "⚽ Matches",
        "👀 Predictions",
        "⚙️ Settings",
        "✏️ Manual Edit",
    ])

    # =========================================================
    # TAB 1: Matches (Add / Edit / Delete)
    # =========================================================
    with tab_matches:
        st.subheader("⚽ Matches")

        # ADD MATCH
        st.markdown("### ➕ Add Match")
        colA, colB = st.columns(2)
        with colA:
            teamA = st.text_input(tr(LANG_CODE,"team_a"), key="adm_add_teamA")
        with colB:
            teamB = st.text_input(tr(LANG_CODE,"team_b"), key="adm_add_teamB")

        colD1, colD2, colD3 = st.columns(3)
        with colD1:
            date_val = st.date_input(tr(LANG_CODE,"date_label"), key="adm_add_date")
        with colD2:
            hour = st.number_input(tr(LANG_CODE,"hour"), 1, 12, 9, key="adm_add_hour")
        with colD3:
            minute = st.number_input(tr(LANG_CODE,"minute"), 0, 59, 0, key="adm_add_min")

        big = st.checkbox(tr(LANG_CODE,"big_game"), key="adm_add_big")

        if st.button(tr(LANG_CODE,"btn_add_match"), key="adm_add_match_btn"):
            if not teamA or not teamB:
                st.error(tr(LANG_CODE,"enter_both_teams"))
            else:
                ko = datetime.combine(date_val, dtime(hour % 24, minute)).replace(tzinfo=tz)
                m = load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
                row = pd.DataFrame([{
                    "Match": f"{teamA} vs {teamB}",
                    "Kickoff": ko.isoformat(),
                    "Result": None,
                    "HomeLogo": None,
                    "AwayLogo": None,
                    "BigGame": bool(big),
                    "RealWinner": "",
                    "Occasion": "",
                    "OccasionLogo": "",
                    "Round": "",
                }])
                m = pd.concat([m, row], ignore_index=True)
                save_csv(m, MATCHES_FILE)
                st.success(tr(LANG_CODE,"match_added"))
                st.rerun()

        st.markdown("---")
        st.markdown("### ✏️ Edit / Delete Matches")

        mdf = load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
        if mdf.empty:
            st.info(tr(LANG_CODE,"no_matches"))
        else:
            for idx, row in mdf.iterrows():
                st.markdown(f"**{row['Match']}**")
                if st.button("❌ Delete Match", key=f"adm_del_match_{idx}"):
                    # delete match + its predictions
                    mdf = mdf[mdf["Match"] != row["Match"]]
                    save_csv(mdf, MATCHES_FILE)

                    p = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
                    p = p[p["Match"] != row["Match"]]
                    save_csv(p, PREDICTIONS_FILE)

                    recompute_leaderboard(p)
                    st.success("Match & predictions deleted")
                    st.rerun()

    # =========================================================
    # TAB 2: View & Delete Predictions
    # =========================================================
    with tab_predictions:
        st.subheader("👀 User Predictions")

        preds = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
        if preds.empty:
            st.info("No predictions yet.")
        else:
            st.dataframe(preds, use_container_width=True)

            st.markdown("---")
            del_user = st.selectbox("Select user", options=sorted(preds["User"].unique()))
            del_match = st.selectbox(
                "Select match",
                options=sorted(preds[preds["User"] == del_user]["Match"].unique())
            )

            if st.button("🗑️ Delete Selected Prediction"):
                preds = preds[~((preds["User"] == del_user) & (preds["Match"] == del_match))]
                save_csv(preds, PREDICTIONS_FILE)
                recompute_leaderboard(preds)
                st.success("Prediction deleted")
                st.rerun()

    # =========================================================
    # TAB 3: Settings (Season + Backup + Users + OTP)
    # =========================================================
    with tab_settings:
        st.subheader("⚙️ Settings")

        # SEASON
        st.markdown("### 🏁 Season")
        season_name = st.text_input(tr(LANG_CODE,"season_name_label"), key="adm_season_name")
        if st.button("Save Season"):
            with open(SEASON_FILE,"w",encoding="utf-8") as f:
                f.write(season_name or "")
            st.success(tr(LANG_CODE,"season_saved"))

        st.markdown("---")

        # BACKUP / RESTORE
        st.markdown("### 📦 Backup & Restore")
        if st.button("⬇️ Backup Now"):
            buf = create_backup_zip()
            st.download_button("Download backup.zip", buf.getvalue(), "prediction_backup.zip")

        up = st.file_uploader("Restore backup.zip", type="zip")
        if up and st.button("Restore"):
            restore_from_zip(up)
            preds = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
            recompute_leaderboard(preds)
            st.success("Backup restored")
            st.rerun()

        st.markdown("---")

        # USERS + OTP
        st.markdown("### 👤 Users & OTP")
        users_df = load_users()
        if users_df.empty:
            st.info("No users yet.")
        else:
            st.dataframe(users_df, use_container_width=True)
            u = st.selectbox("Select user", options=users_df["Name"].tolist())

            if st.button("Generate OTP"):
                code = otp_generate(u)
                st.code(f"OTP for {u}: {code}")

            if st.button("Revoke OTP"):
                otp_revoke(u)
                st.success("OTP revoked")

    # =========================================================
    # TAB 4: Manual Overrides (Already fixed for users)
    # =========================================================
    with tab_manual:
        st.subheader("✏️ Manual Leaderboard Overrides")

        preds = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
        lb = recompute_leaderboard(preds)
        overrides = load_overrides()

        if lb.empty:
            st.info(tr(LANG_CODE,"no_scores_yet"))
        else:
            st.dataframe(lb, use_container_width=True)

            user_pick = st.selectbox("User", options=lb["User"].tolist())
            new_preds = st.number_input("Predictions", 0, 999, int(lb.loc[lb["User"]==user_pick,"Predictions"].iloc[0]))
            new_points = st.number_input("Points", 0, 999, int(lb.loc[lb["User"]==user_pick,"Points"].iloc[0]))

            if st.button("Save Override"):
                o = load_overrides()
                o = o[o["User"] != user_pick]
                o = pd.concat([o, pd.DataFrame([{
                    "User": user_pick,
                    "Predictions": int(new_preds),
                    "Points": int(new_points),
                }])])
                save_overrides(o)
                st.success("Override saved (users will see it)")
                st.rerun()
 return