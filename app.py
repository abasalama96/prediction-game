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

ADMIN_PASSWORD = "madness"

# One-time PIN settings (NEW)
OTP_VALID_MINUTES = 10

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

        # NEW: one-time pin text
        "otp_section": "One-time PIN (Admin only)",
        "otp_generate": "Generate one-time PIN",
        "otp_expires": "Expires at",
        "otp_show": "Temporary PIN",
        "otp_force_title": "🔒 Security: Set a new PIN",
        "otp_force_msg": "You logged in with a temporary PIN. Please set a new 4-digit PIN to continue.",
        "otp_new_pin": "New PIN (4 digits)",
        "otp_save_new": "Save new PIN",
        "otp_saved": "New PIN saved. You can continue now.",
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

        # NEW: one-time pin text
        "otp_section": "الرقم السري المؤقت (للمشرف فقط)",
        "otp_generate": "إنشاء رقم سري مؤقت",
        "otp_expires": "ينتهي في",
        "otp_show": "الرقم المؤقت",
        "otp_force_title": "🔒 الأمان: تعيين رقم سري جديد",
        "otp_force_msg": "تم تسجيل الدخول برقم سري مؤقت. الرجاء تعيين رقم سري جديد من 4 أرقام للمتابعة.",
        "otp_new_pin": "الرقم السري الجديد (4 أرقام)",
        "otp_save_new": "حفظ الرقم السري الجديد",
        "otp_saved": "تم حفظ الرقم السري الجديد. يمكنك المتابعة الآن.",
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

def _now_utc() -> datetime:
    return datetime.now(ZoneInfo("UTC"))

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

# safe logo renderer
def show_logo_safe(img_ref, width=56, caption=""):
    """Render a logo whether it is a local file path or a URL; ignore unreadable images."""
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
# theme
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
    if not name: return
    label = f"Welcome, <b>{name}</b>" if lang=="en" else f"مرحبًا، <b>{name}</b>"
    st.markdown(f"""<div class="welcome-wrap">{label}</div>""", unsafe_allow_html=True)

# ─────────────────────────────
# Browser time zone detection + query param bridge (uses st.query_params)
# ─────────────────────────────
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

# ─────────────────────────────
# Users (Name + PIN) + One-time PIN (NEW)
# ─────────────────────────────
def load_users():
    cols = ["Name","CreatedAt","IsBanned","PinHash","OTPHash","OTPExpiresAt","OTPUsed","ForceReset"]
    if os.path.exists(USERS_FILE) and os.path.getsize(USERS_FILE) > 0:
        df = pd.read_csv(USERS_FILE)
        for c in cols:
            if c not in df.columns: df[c] = None
        df["IsBanned"] = pd.to_numeric(df["IsBanned"], errors="coerce").fillna(0).astype(int)
        df["OTPUsed"] = pd.to_numeric(df["OTPUsed"], errors="coerce").fillna(0).astype(int)
        df["ForceReset"] = pd.to_numeric(df["ForceReset"], errors="coerce").fillna(0).astype(int)
        df["PinHash"] = df["PinHash"].astype("string")
        df["OTPHash"] = df["OTPHash"].astype("string")
        for col in ["PinHash","OTPHash","OTPExpiresAt"]:
            df.loc[df[col].isin([None, pd.NA, "nan", "NaN", "None"]), col] = None
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_users(df):
    cols = ["Name","CreatedAt","IsBanned","PinHash","OTPHash","OTPExpiresAt","OTPUsed","ForceReset"]
    for c in cols:
        if c not in df.columns: df[c] = None
    df["IsBanned"] = pd.to_numeric(df.get("IsBanned", 0), errors="coerce").fillna(0).astype(int)
    df["OTPUsed"] = pd.to_numeric(df.get("OTPUsed", 0), errors="coerce").fillna(0).astype(int)
    df["ForceReset"] = pd.to_numeric(df.get("ForceReset", 0), errors="coerce").fillna(0).astype(int)
    df[cols].to_csv(USERS_FILE, index=False)

def _hash_otp(pin: str) -> str:
    # same hashing format as normal pins (salt:hash)
    return _hash_pin(pin)

def _otp_is_valid(row: pd.Series) -> bool:
    try:
        if int(row.get("OTPUsed", 0)) == 1:
            return False
        exp = parse_iso_dt(row.get("OTPExpiresAt"))
        if not exp:
            return False
        return _now_utc() <= exp
    except Exception:
        return False

def _set_user_otp(users_df: pd.DataFrame, name: str) -> tuple[pd.DataFrame, str, datetime] | tuple[None,None,None]:
    # returns (updated_df, otp_pin, expires_dt_utc)
    name_norm = (name or "").strip()
    if not name_norm:
        return (None, None, None)
    mask = users_df["Name"].astype(str).str.strip().str.casefold() == name_norm.casefold()
    if not mask.any():
        return (None, None, None)

    otp_pin = f"{secrets.randbelow(10000):04d}"
    expires = _now_utc() + timedelta(minutes=OTP_VALID_MINUTES)

    users_df.loc[mask, "OTPHash"] = _hash_otp(otp_pin)
    users_df.loc[mask, "OTPExpiresAt"] = expires.isoformat()
    users_df.loc[mask, "OTPUsed"] = 0
    users_df.loc[mask, "ForceReset"] = 1
    return (users_df, otp_pin, expires)

def _clear_user_otp(users_df: pd.DataFrame, name: str) -> pd.DataFrame:
    name_norm = (name or "").strip()
    mask = users_df["Name"].astype(str).str.strip().str.casefold() == name_norm.casefold()
    if mask.any():
        users_df.loc[mask, ["OTPHash","OTPExpiresAt","OTPUsed"]] = [None, None, 1]
    return users_df
# ─────────────────────────────
# Scoring helpers (MATCH-ID SAFE)
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
    Returns (points, exact_flag, outcome_flag)

    🔹 Exact score:
       - Normal match: 3 points
       - Golden match: 6 points

    🔹 Correct outcome only:
       - Normal match: 1 point
       - Golden match: 2 points
    """
    real = match_row.get("Result")
    if not isinstance(real, str) or not isinstance(pred, str):
        return (0,0,0)

    real_pair = normalize_score_pair(real)
    pred_pair = normalize_score_pair(pred)
    if real_pair is None or pred_pair is None:
        return (0,0,0)

    # Exact score (order-insensitive)
    if real_pair == pred_pair:
        return (6 if big_game else 3, 1, 0)

    # Outcome (winner / draw)
    real_w = get_real_winner(match_row)
    pred_draw = (pred_pair[0] == pred_pair[1])

    if real_w == "Draw" and pred_draw:
        return (2 if big_game else 1, 0, 1)

    if real_w != "Draw" and isinstance(chosen_winner, str) and chosen_winner.strip() == real_w:
        return (2 if big_game else 1, 0, 1)

    return (0,0,0)

def _load_all_matches_for_scoring() -> pd.DataFrame:
    """
    IMPORTANT FIX:
    Matches are joined by MatchID (not by Match name),
    so repeated team matchups are handled correctly.
    """
    cols_open = ["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"]
    cols_hist = cols_open + ["CompletedAt"]

    open_m = load_csv(MATCHES_FILE, cols_open)
    hist_m = load_csv(MATCH_HISTORY_FILE, cols_hist)

    if not hist_m.empty:
        hist_m = hist_m.drop(columns=["CompletedAt"], errors="ignore")

    if open_m.empty and hist_m.empty:
        return pd.DataFrame(columns=cols_open)

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

    # 🔹 KEY FIX:
    # latest prediction PER USER PER MATCH-ID
    preds = preds.sort_values(["User","MatchID","SubmittedAt"])
    latest = preds.drop_duplicates(subset=["User","MatchID"], keep="last")

    rows = []
    for _, p in latest.iterrows():
        mrow = matches_full[matches_full["MatchID"] == p["MatchID"]]
        if mrow.empty:
            continue

        m = mrow.iloc[0]
        real = m["Result"]
        if not isinstance(real, str) or "-" not in str(real):
            continue

        big = bool(m["BigGame"])
        chosen_winner = str(p.get("Winner") or "")
        pts, ex, out = points_for_prediction(
            m,
            str(p["Prediction"]),
            big,
            chosen_winner
        )
        rows.append({
            "User": p["User"],
            "Points": pts,
            "Exact": ex,
            "Outcome": out
        })

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
               Outcome=("Outcome","sum"),
           )
    )

    lb = lb.sort_values(["Points","Predictions","Exact"], ascending=[False, True, False])
    save_csv(lb, LEADERBOARD_FILE)
    return lb
# ─────────────────────────────
# UI helpers (NiceGUI)
# ─────────────────────────────
from nicegui import ui, app

def notify_ok(msg: str):
    ui.notify(msg, type='positive')

def notify_err(msg: str):
    ui.notify(msg, type='negative')

def notify_info(msg: str):
    ui.notify(msg, type='info')

def _ensure_defaults():
    # Safe defaults (requires storage_secret in ui.run)
    app.storage.user.setdefault('lang', 'en')
    app.storage.user.setdefault('role', None)          # 'user' | 'admin' | None
    app.storage.user.setdefault('current_name', None)  # username string

def get_lang() -> str:
    _ensure_defaults()
    return app.storage.user.get('lang', 'en') or 'en'

def set_lang(v: str):
    _ensure_defaults()
    app.storage.user['lang'] = 'ar' if v == 'ar' else 'en'

def get_role():
    _ensure_defaults()
    return app.storage.user.get('role', None)

def set_role(v):
    _ensure_defaults()
    app.storage.user['role'] = v

def get_current_name():
    _ensure_defaults()
    return app.storage.user.get('current_name', None)

def set_current_name(v):
    _ensure_defaults()
    app.storage.user['current_name'] = v

def logout():
    set_role(None)
    set_current_name(None)
    ui.open('/')

def top_bar():
    lang = get_lang()

    with ui.row().classes('w-full items-center justify-between'):
        ui.label(tr(lang, 'app_title')).classes('text-2xl font-bold')

        with ui.row().classes('items-center gap-2'):
            # Language toggle
            ui.label('Language / اللغة').classes('text-sm opacity-80')
            ui.toggle(['en', 'ar'], value=lang, on_change=lambda e: (set_lang(e.value), ui.open('/')))

            # Logout button (only if logged)
            if get_role() in ('user', 'admin'):
                ui.button('Logout' if lang == 'en' else 'تسجيل الخروج', on_click=logout).props('outline')

    # Small welcome line (top-right feel)
    name = get_current_name()
    if name:
        msg = f"Welcome, {name}" if lang == 'en' else f"مرحبًا، {name}"
        ui.label(msg).classes('w-full text-right opacity-80')


# ─────────────────────────────
# Login page
# ─────────────────────────────
def page_login():
    lang = get_lang()

    top_bar()
    ui.separator()

    ui.label(tr(lang, 'login_tab')).classes('text-xl font-semibold')

    role_choice = ui.radio(
        options=[
            ('user', tr(lang, 'user_login')),
            ('admin', tr(lang, 'admin_login')),
        ],
        value='user',
    ).props('inline')

    ui.separator()

    users_df = load_users()

    # ---- USER LOGIN ----
    user_box = ui.column().classes('w-full')
    admin_box = ui.column().classes('w-full')

    def refresh_visibility():
        is_user = (role_choice.value == 'user')
        user_box.set_visibility(is_user)
        admin_box.set_visibility(not is_user)

    role_choice.on('update:model-value', lambda _: refresh_visibility())

    with user_box:
        ui.label(tr(lang, 'user_login')).classes('text-lg font-semibold')

        name_in = ui.input(tr(lang, 'your_name')).props('clearable')
        pin_in = ui.input('PIN (4 digits)' if lang == 'en' else 'الرقم السري (4 أرقام)').props('type=password clearable')

        def do_user_login():
            nonlocal users_df
            users_df = load_users()
            name_norm = (name_in.value or '').strip()
            pin_norm = normalize_digits(pin_in.value or '')

            if not name_norm or not re.fullmatch(r"\d{4}", pin_norm):
                notify_err(tr(lang, "please_login_first"))
                return

            candidates = users_df[
                users_df["Name"].astype(str).str.strip().str.casefold() == name_norm.casefold()
            ]
            if candidates.empty:
                notify_err(tr(lang, "please_login_first"))
                return

            row = candidates.iloc[0]
            if int(row.get("IsBanned", 0)) == 1:
                notify_err("User is banned." if lang == "en" else "المستخدم محظور.")
                return

            if _verify_pin(row.get("PinHash"), pin_norm):
                set_role('user')
                set_current_name(str(row["Name"]).strip())
                notify_ok(tr(lang, "login_ok"))
                ui.open('/')
            else:
                notify_err("Wrong PIN." if lang == "en" else "الرقم السري غير صحيح.")

        ui.button(tr(lang, 'login'), on_click=do_user_login).classes('mt-2')

        ui.separator()
        ui.label(tr(lang, 'register')).classes('text-lg font-semibold')

        reg_name = ui.input(tr(lang, 'your_name')).props('clearable')
        reg_pin = ui.input('Choose a 4-digit PIN' if lang == 'en' else 'اختر رقماً سرياً من 4 أرقام').props('type=password clearable')

        def do_register():
            nonlocal users_df
            users_df = load_users()

            nm = (reg_name.value or '').strip()
            pn = normalize_digits(reg_pin.value or '')

            if not nm:
                notify_err(tr(lang, "need_name"))
                return
            if not re.fullmatch(r"\d{4}", pn):
                notify_err("PIN must be 4 digits." if lang == "en" else "الرقم السري يجب أن يكون 4 أرقام.")
                return

            exists = users_df["Name"].astype(str).str.strip().str.casefold().eq(nm.casefold()).any()
            if exists:
                notify_err("Name already exists. Please choose a different name." if lang=="en" else "الاسم موجود مسبقًا. الرجاء اختيار اسم مختلف.")
                return

            new_row = pd.DataFrame([{
                "Name": nm,
                "CreatedAt": datetime.now(ZoneInfo("UTC")).isoformat(),
                "IsBanned": 0,
                "PinHash": _hash_pin(pn),
            }])
            users_df = pd.concat([users_df, new_row], ignore_index=True)
            save_users(users_df)

            set_role('user')
            set_current_name(nm)
            notify_ok(tr(lang, "login_ok"))
            ui.open('/')

        ui.button(tr(lang, 'register'), on_click=do_register).classes('mt-2')

    # ---- ADMIN LOGIN ----
    with admin_box:
        ui.label(tr(lang, 'admin_login')).classes('text-lg font-semibold')
        pwd = ui.input(tr(lang, 'admin_pass')).props('type=password clearable')

        def do_admin_login():
            if (pwd.value or '') == ADMIN_PASSWORD:
                set_role('admin')
                set_current_name('Admin')
                notify_ok(tr(lang, 'admin_ok'))
                ui.open('/')
            else:
                notify_err(tr(lang, 'admin_bad'))

        ui.button(tr(lang, 'admin_login'), on_click=do_admin_login).classes('mt-2')

    refresh_visibility()


# ─────────────────────────────
# Main router (entry)
# ─────────────────────────────
@ui.page('/')
def route_index():
    _ensure_defaults()
    role = get_role()

    if role not in ('user', 'admin'):
        page_login()
        return

    # user/admin main content will be in Part 5
    # (we keep this stub minimal, then extend in next part)
    top_bar()
    ui.separator()
    ui.label('Loading...').classes('opacity-70')
# ─────────────────────────────
# User pages (Play + Leaderboard)
# ─────────────────────────────
def page_play_and_leaderboard():
    lang = get_lang()
    top_bar()

    # Season title
    season_name = ""
    if os.path.exists(SEASON_FILE):
        try:
            with open(SEASON_FILE, "r", encoding="utf-8") as f:
                season_name = f.read().strip()
        except Exception:
            season_name = ""

    if season_name:
        ui.label(season_name).classes('text-sm opacity-80 w-full text-center')

    ui.separator()

    matches_df = load_csv(
        MATCHES_FILE,
        ["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"]
    )
    predictions_df = load_csv(PREDICTIONS_FILE, ["User","MatchID","Match","Prediction","Winner","SubmittedAt"])

    current_name = get_current_name()
    tz_str = DEFAULT_TZ
    try:
        tz_str = app.storage.user.get('tz', DEFAULT_TZ) or DEFAULT_TZ
    except Exception:
        tz_str = DEFAULT_TZ
    tz = ZoneInfo(tz_str)

    with ui.tabs().classes('w-full') as tabs:
        tab_play = ui.tab(f"🎮 {tr(lang, 'tab_play')}")
        tab_lb   = ui.tab(f"🏆 {tr(lang, 'tab_leaderboard')}")

    with ui.tab_panels(tabs, value=tab_play).classes('w-full'):
        # ---------------- Play ----------------
        with ui.tab_panel(tab_play):
            if matches_df.empty:
                notify_info(tr(lang, "no_matches"))
            else:
                tmp = matches_df.copy()
                tmp["KO"] = tmp["Kickoff"].apply(parse_iso_dt)
                tmp = tmp.sort_values("KO").reset_index(drop=True)

                for idx, row in tmp.iterrows():
                    match_id = str(row.get("MatchID") or "")
                    match = row.get("Match") or ""
                    team_a, team_b = split_match_name(match)
                    ko = row.get("KO")
                    big = bool(row.get("BigGame", False))

                    with ui.card().classes('w-full'):
                        # logos row
                        with ui.row().classes('w-full items-center justify-between'):
                            # home
                            with ui.column().classes('items-center'):
                                img_a = row.get("HomeLogo") or ""
                                if img_a:
                                    ui.image(img_a).classes('w-14 h-14')
                                ui.label(team_a or " ").classes('text-sm opacity-80')

                            # occasion
                            with ui.column().classes('items-center'):
                                occ_logo = row.get("OccasionLogo") or ""
                                if occ_logo:
                                    ui.image(occ_logo).classes('w-14 h-14')
                                ui.label((row.get("Occasion") or " ")[:40]).classes('text-sm opacity-80')

                            # away
                            with ui.column().classes('items-center'):
                                img_b = row.get("AwayLogo") or ""
                                if img_b:
                                    ui.image(img_b).classes('w-14 h-14')
                                ui.label(team_b or " ").classes('text-sm opacity-80')

                        ui.label(f"{team_a} vs {team_b}").classes('text-lg font-semibold')

                        aux = []
                        if row.get("Round"):
                            aux.append(f"{tr(lang,'round')}: {row.get('Round')}")
                        if row.get("Occasion"):
                            aux.append(f"{tr(lang,'occasion')}: {row.get('Occasion')}")
                        if aux:
                            ui.label(" | ".join(aux)).classes('text-sm opacity-80')

                        ui.label(f"{tr(lang,'kickoff')}: {format_dt_ampm(ko, tz, lang)}").classes('text-sm opacity-80')

                        if big:
                            ui.label(tr(lang, 'gold_badge')).classes('px-3 py-1 rounded-full font-bold bg-amber-200 text-black w-fit')

                        # timing gates
                        if ko:
                            open_at = (to_tz(ko, tz) - timedelta(hours=2))
                            now_local = datetime.now(tz)

                            if now_local < open_at:
                                remain = open_at - now_local
                                ui.label(f"{tr(lang,'opens_in')}: {human_delta(remain, lang)}").classes('text-sm')
                            elif open_at <= now_local < to_tz(ko, tz):
                                if not current_name:
                                    ui.label(tr(lang, "please_login_first")).classes('text-sm text-red-200')
                                else:
                                    already = predictions_df[
                                        (predictions_df["User"] == current_name) &
                                        (predictions_df["MatchID"].astype(str) == match_id)
                                    ]
                                    if not already.empty:
                                        ui.label(tr(lang, "already_submitted")).classes('text-sm opacity-80')
                                    else:
                                        # Prediction inputs
                                        score_in = ui.input(tr(lang, "score")).props('clearable')
                                        # winner options: if draw typed, we disable later
                                        winner_select = ui.select(
                                            [team_a, team_b, tr(lang, "draw")],
                                            value=team_a,
                                            label=tr(lang, "winner"),
                                        )

                                        def _is_draw_score(val: str) -> bool:
                                            v = normalize_digits(val or "")
                                            if not re.fullmatch(r"\d{1,2}-\d{1,2}", v):
                                                return False
                                            a, b = map(int, v.split("-"))
                                            return a == b

                                        def _on_score_change(_):
                                            if _is_draw_score(score_in.value):
                                                winner_select.value = tr(lang, "draw")
                                                winner_select.disable()
                                            else:
                                                winner_select.enable()

                                        score_in.on('change', _on_score_change)

                                        def submit_pred():
                                            nonlocal predictions_df
                                            v = normalize_digits(score_in.value or "")
                                            if not re.fullmatch(r"\d{1,2}-\d{1,2}", v):
                                                notify_err(tr(lang, "fmt_error"))
                                                return
                                            h1, h2 = map(int, v.split("-"))
                                            if not (0 <= h1 <= 20 and 0 <= h2 <= 20):
                                                notify_err(tr(lang, "range_error"))
                                                return

                                            win = winner_select.value
                                            if h1 == h2:
                                                win = tr(lang, "draw")

                                            new_pred = pd.DataFrame([{
                                                "User": current_name,
                                                "MatchID": match_id,
                                                "Match": match,
                                                "Prediction": f"{h1}-{h2}",
                                                "Winner": win,
                                                "SubmittedAt": datetime.now(ZoneInfo("UTC")).isoformat(),
                                            }])
                                            predictions_df = pd.concat([predictions_df, new_pred], ignore_index=True)
                                            save_csv(predictions_df, PREDICTIONS_FILE)
                                            recompute_leaderboard(predictions_df)
                                            notify_ok(tr(lang, "saved_ok"))
                                            ui.open('/')

                                        ui.button(tr(lang, "submit_btn"), on_click=submit_pred).classes('mt-2')
                            else:
                                ui.label(f"🔒 {tr(lang,'closed')}").classes('text-sm opacity-80')

        # ---------------- Leaderboard ----------------
        with ui.tab_panel(tab_lb):
            preds = load_csv(PREDICTIONS_FILE, ["User","MatchID","Match","Prediction","Winner","SubmittedAt"])
            lb = recompute_leaderboard(preds)

            ui.label(tr(lang, "leaderboard")).classes('text-xl font-semibold')
            if lb.empty:
                notify_info(tr(lang, "no_scores_yet"))
            else:
                # add rank + medals
                lb = lb.reset_index(drop=True)
                ranks = list(range(1, len(lb) + 1))
                medals = []
                for r in ranks:
                    if r == 1: medals.append("🥇")
                    elif r == 2: medals.append("🥈")
                    elif r == 3: medals.append("🥉")
                    else: medals.append("")
                lb_view = lb.copy()
                lb_view.insert(0, tr(lang, "lb_rank"), [f"{r} {m}".strip() for r, m in zip(ranks, medals)])

                col_map = {
                    "User": tr(lang,"lb_user"),
                    "Predictions": tr(lang,"lb_preds"),
                    "Exact": tr(lang,"lb_exact"),
                    "Outcome": tr(lang,"lb_outcome"),
                    "Points": tr(lang,"lb_points"),
                }
                # NiceGUI table
                rows = lb_view.to_dict(orient="records")
                columns = [
                    {"name": tr(lang,"lb_rank"), "label": tr(lang,"lb_rank"), "field": tr(lang,"lb_rank"), "align": "left"},
                    {"name": "User", "label": col_map["User"], "field": "User", "align": "left"},
                    {"name": "Predictions", "label": col_map["Predictions"], "field": "Predictions", "align": "left"},
                    {"name": "Exact", "label": col_map["Exact"], "field": "Exact", "align": "left"},
                    {"name": "Outcome", "label": col_map["Outcome"], "field": "Outcome", "align": "left"},
                    {"name": "Points", "label": col_map["Points"], "field": "Points", "align": "left"},
                ]
                ui.table(columns=columns, rows=rows, row_key="User").classes('w-full')


# ─────────────────────────────
# Admin page
# ─────────────────────────────
def page_admin():
    lang = get_lang()
    top_bar()
    ui.separator()

    ui.label(f"🔑 {tr(lang,'admin_panel')}").classes('text-xl font-semibold')
    ui.separator()

    # ---- Season controls ----
    ui.label(tr(lang,'season_settings')).classes('text-lg font-semibold')
    current_season = ""
    if os.path.exists(SEASON_FILE):
        try:
            with open(SEASON_FILE,"r",encoding="utf-8") as f:
                current_season = f.read().strip()
        except Exception:
            current_season = ""

    season_in = ui.input(tr(lang,"season_name_label"), value=current_season).props('clearable')

    with ui.row().classes('gap-2'):
        def save_season():
            try:
                with open(SEASON_FILE,"w",encoding="utf-8") as f:
                    f.write((season_in.value or "").strip())
                notify_ok(tr(lang,"season_saved"))
            except Exception as e:
                notify_err(str(e))

        def reset_season():
            def _safe_remove(p):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            for f in [USERS_FILE, MATCHES_FILE, MATCH_HISTORY_FILE, PREDICTIONS_FILE, LEADERBOARD_FILE, SEASON_FILE]:
                _safe_remove(f)
            logout()

        ui.button(tr(lang,"season_saved"), on_click=save_season).props('outline')
        ui.button(tr(lang,"reset_season"), on_click=reset_season).props('outline')

    ui.separator()

    # ---- Registered Users (Terminate + Delete + Reset PIN) ----
    ui.label(tr(lang,'registered_users')).classes('text-lg font-semibold')
    users_df = load_users()

    if users_df.empty:
        ui.label("No users yet." if lang=="en" else "لا يوجد مستخدمون بعد.").classes('opacity-80')
    else:
        show = users_df.copy().sort_values("CreatedAt")
        user_list = show["Name"].astype(str).tolist()

        target = ui.select(user_list, value=user_list[0], label=("Select user" if lang=="en" else "اختر مستخدمًا")).classes('w-80')

        with ui.row().classes('gap-2 items-end'):
            # terminate
            def do_terminate():
                df = load_users()
                nm = str(target.value).strip()
                df.loc[df["Name"].astype(str).str.strip().str.casefold() == nm.casefold(), "IsBanned"] = 1
                save_users(df)
                notify_ok(tr(lang,"terminated"))
                ui.open('/')

            ui.button(tr(lang,"terminate"), on_click=do_terminate).props('outline')

            # delete
            def do_delete_user():
                df = load_users()
                nm = str(target.value).strip()
                mask = df["Name"].astype(str).str.strip().str.casefold() != nm.casefold()
                if mask.all():
                    notify_err("User not found." if lang=="en" else "المستخدم غير موجود.")
                    return
                df = df[mask]
                save_users(df)
                notify_ok("User deleted." if lang=="en" else "تم حذف المستخدم.")
                ui.open('/')

            ui.button("Delete user" if lang=="en" else "حذف المستخدم", on_click=do_delete_user).props('outline')

        # IMPORTANT: PINs are hashed → cannot be “viewed”
        ui.separator()
        ui.label("Forgot PIN / Reset PIN" if lang=="en" else "نسيت الرقم السري / إعادة تعيين").classes('text-md font-semibold')
        ui.label(
            "You cannot view the old PIN because it's stored securely (hashed). But you can reset it."
            if lang=="en" else
            "لا يمكن عرض الرقم السري القديم لأنه محفوظ بشكل آمن (مشفّر). لكن يمكنك إعادة تعيينه."
        ).classes('text-sm opacity-80')

        new_pin = ui.input("New 4-digit PIN" if lang=="en" else "رقم سري جديد (4 أرقام)").props('type=password clearable').classes('w-60')

        def do_reset_pin():
            df = load_users()
            nm = str(target.value).strip()
            pn = normalize_digits(new_pin.value or "")
            if not re.fullmatch(r"\d{4}", pn):
                notify_err("PIN must be 4 digits." if lang=="en" else "الرقم السري يجب أن يكون 4 أرقام.")
                return
            idxs = df.index[df["Name"].astype(str).str.strip().str.casefold() == nm.casefold()].tolist()
            if not idxs:
                notify_err("User not found." if lang=="en" else "المستخدم غير موجود.")
                return
            df.loc[idxs[0], "PinHash"] = _hash_pin(pn)
            save_users(df)
            notify_ok("PIN reset saved." if lang=="en" else "تم حفظ الرقم السري الجديد.")
            ui.open('/')

        ui.button("Reset PIN" if lang=="en" else "تعيين الرقم السري", on_click=do_reset_pin).props('outline')

    ui.separator()

    # NOTE: Admin match management + prediction deletion stays as in your last update.
    # It will be included in Part 6 (the rest of the admin: add/edit matches, delete match + its predictions, delete selected prediction, history, backup/restore if present).


# ─────────────────────────────
# Router (updated)
# ─────────────────────────────
@ui.page('/')
def route_index():
    _ensure_defaults()
    role = get_role()

    # defaults for timezone (kept simple here)
    app.storage.user.setdefault('tz', DEFAULT_TZ)

    if role not in ('user', 'admin'):
        page_login()
        return

    if role == 'admin':
        page_admin()
    else:
        page_play_and_leaderboard()
# ─────────────────────────────
# Admin: Matches + Predictions Management (DELETE MATCH + DELETE PREDICTION)
# ─────────────────────────────
def page_admin_matches_and_predictions():
    lang = get_lang()

    # ---------- Load data ----------
    mdf = load_csv(
        MATCHES_FILE,
        ["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"]
    )
    preds_df = load_csv(PREDICTIONS_FILE, ["User","MatchID","Match","Prediction","Winner","SubmittedAt"])
    hist_df = load_csv(
        MATCH_HISTORY_FILE,
        ["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"]
    )

    ui.label(tr(lang, "add_match")).classes('text-lg font-semibold')

    # ---------- Add Match ----------
    with ui.card().classes('w-full'):
        teamA_in = ui.input(tr(lang, "team_a")).props('clearable').classes('w-80')
        teamB_in = ui.input(tr(lang, "team_b")).props('clearable').classes('w-80')

        home_url = ui.input(tr(lang, "home_logo_url")).props('clearable').classes('w-full')
        away_url = ui.input(tr(lang, "away_logo_url")).props('clearable').classes('w-full')

        occ_in = ui.input(tr(lang, "occasion")).props('clearable').classes('w-80')
        occ_logo_url = ui.input(tr(lang, "occasion_logo_url")).props('clearable').classes('w-full')
        round_in = ui.input(tr(lang, "round")).props('clearable').classes('w-80')

        big_chk = ui.checkbox(tr(lang, "big_game"))

        # datetime inputs (simple)
        date_in = ui.input(tr(lang, "date_label"), value=str(date.today())).props('type=date').classes('w-60')
        hour_in = ui.number(tr(lang, "hour"), value=9, min=1, max=12).classes('w-40')
        min_in  = ui.number(tr(lang, "minute"), value=0, min=0, max=59).classes('w-40')
        ampm_in = ui.select([tr(lang,"ampm_am"), tr(lang,"ampm_pm")], value=tr(lang,"ampm_pm"), label=tr(lang,"ampm")).classes('w-40')

        def add_match():
            nonlocal mdf
            A = (teamA_in.value or "").strip()
            B = (teamB_in.value or "").strip()
            if not A or not B:
                notify_err(tr(lang, "enter_both_teams"))
                return

            # timezone: admin uses current selected/default tz in user storage if available
            tz_str = app.storage.user.get('tz', DEFAULT_TZ) or DEFAULT_TZ
            tz = ZoneInfo(tz_str)

            # build kickoff datetime
            try:
                d = datetime.fromisoformat(str(date_in.value))
                hr = int(hour_in.value or 9)
                mi = int(min_in.value or 0)
                is_pm = (ampm_in.value in ["PM", "مساء", tr(lang,"ampm_pm")])
                hr24 = (0 if hr == 12 else hr) + (12 if is_pm else 0)
                ko = datetime(d.year, d.month, d.day, hr24, mi, tzinfo=tz)
            except Exception:
                notify_err("Invalid date/time" if lang=="en" else "وقت/تاريخ غير صحيح")
                return

            # resolve logos (cache if URL)
            hlogo = (home_url.value or "").strip()
            alogo = (away_url.value or "").strip()
            ologo = (occ_logo_url.value or "").strip()

            hlogo_final = cache_logo_from_url(hlogo) or (hlogo if hlogo else None)
            alogo_final = cache_logo_from_url(alogo) or (alogo if alogo else None)
            ologo_final = cache_logo_from_url(ologo) or (ologo if ologo else None)

            if hlogo_final: save_team_logo(A, hlogo_final)
            if alogo_final: save_team_logo(B, alogo_final)

            # create unique MatchID automatically (doesn't care if same teams repeat)
            match_id = new_match_id()

            row = pd.DataFrame([{
                "MatchID": match_id,
                "Match": f"{A} vs {B}",
                "Kickoff": ko.astimezone(ZoneInfo("UTC")).isoformat(),
                "Result": None,
                "HomeLogo": hlogo_final,
                "AwayLogo": alogo_final,
                "BigGame": bool(big_chk.value),
                "RealWinner": "",
                "Occasion": (occ_in.value or "").strip(),
                "OccasionLogo": ologo_final,
                "Round": (round_in.value or "").strip(),
            }])

            mdf = pd.concat([mdf, row], ignore_index=True)
            save_csv(mdf, MATCHES_FILE)
            notify_ok(tr(lang, "match_added"))
            ui.open('/')

        ui.button(tr(lang, "btn_add_match"), on_click=add_match).classes('mt-2')

    ui.separator()

    # ---------- Edit Matches + Delete Match (and delete its predictions) ----------
    ui.label(tr(lang, "edit_matches")).classes('text-lg font-semibold')

    if mdf.empty:
        ui.label(tr(lang, "no_matches")).classes('opacity-80')
    else:
        mdf2 = mdf.copy()
        mdf2["KO"] = mdf2["Kickoff"].apply(parse_iso_dt)
        mdf2 = mdf2.sort_values("KO").reset_index(drop=True)

        for idx, row in mdf2.iterrows():
            match_id = str(row.get("MatchID") or "")
            match_name = str(row.get("Match") or "")
            team_a, team_b = split_match_name(match_name)

            ko = parse_iso_dt(row.get("Kickoff"))
            tz_str = app.storage.user.get('tz', DEFAULT_TZ) or DEFAULT_TZ
            tz = ZoneInfo(tz_str)

            with ui.card().classes('w-full'):
                ui.label(f"{match_name}").classes('text-md font-semibold')
                ui.label(f"{tr(lang,'kickoff')}: {format_dt_ampm(ko, tz, lang)}").classes('text-sm opacity-80')
                ui.label(f"MatchID: {match_id}").classes('text-xs opacity-70')

                # details editors
                newA = ui.input(tr(lang,"team_a"), value=team_a).props('clearable').classes('w-80')
                newB = ui.input(tr(lang,"team_b"), value=team_b).props('clearable').classes('w-80')

                new_home = ui.input(tr(lang,"home_logo_url"), value=str(row.get("HomeLogo") or "")).props('clearable').classes('w-full')
                new_away = ui.input(tr(lang,"away_logo_url"), value=str(row.get("AwayLogo") or "")).props('clearable').classes('w-full')

                new_occ = ui.input(tr(lang,"occasion"), value=str(row.get("Occasion") or "")).props('clearable').classes('w-80')
                new_occ_logo = ui.input(tr(lang,"occasion_logo_url"), value=str(row.get("OccasionLogo") or "")).props('clearable').classes('w-full')

                new_round = ui.input(tr(lang,"round"), value=str(row.get("Round") or "")).props('clearable').classes('w-80')
                big_val = ui.checkbox(tr(lang,"big_game"), value=bool(row.get("BigGame", False)))

                # score editor
                res_in = ui.input(tr(lang,"final_score"), value=str(row.get("Result") or "")).props('clearable').classes('w-60')

                # real winner select
                rw_opts = [newA.value or team_a, newB.value or team_b, tr(lang,"draw")]
                rw_current = str(row.get("RealWinner") or "").strip() or tr(lang,"draw")
                rw_in = ui.select(rw_opts, value=rw_current if rw_current in rw_opts else tr(lang,"draw"), label=tr(lang,"real_winner")).classes('w-60')

                with ui.row().classes('gap-2'):
                    # Save details
                    def save_details(match_id=match_id, old_match=match_name):
                        nonlocal mdf
                        A = (newA.value or "").strip()
                        B = (newB.value or "").strip()
                        if not A or not B:
                            notify_err(tr(lang, "enter_both_teams"))
                            return

                        hlogo = cache_logo_from_url(new_home.value or "") or ((new_home.value or "").strip() or None)
                        alogo = cache_logo_from_url(new_away.value or "") or ((new_away.value or "").strip() or None)
                        ologo = cache_logo_from_url(new_occ_logo.value or "") or ((new_occ_logo.value or "").strip() or None)

                        if hlogo: save_team_logo(A, hlogo)
                        if alogo: save_team_logo(B, alogo)

                        new_match_name = f"{A} vs {B}"

                        mdf.loc[mdf["MatchID"].astype(str) == str(match_id), ["Match","HomeLogo","AwayLogo","BigGame","Occasion","OccasionLogo","Round"]] = [
                            new_match_name, hlogo, alogo, bool(big_val.value), (new_occ.value or "").strip(), ologo, (new_round.value or "").strip()
                        ]
                        save_csv(mdf, MATCHES_FILE)

                        # also keep predictions "Match" text in sync (optional but helpful)
                        pdf = load_csv(PREDICTIONS_FILE, ["User","MatchID","Match","Prediction","Winner","SubmittedAt"])
                        if not pdf.empty:
                            pdf.loc[pdf["MatchID"].astype(str) == str(match_id), "Match"] = new_match_name
                            save_csv(pdf, PREDICTIONS_FILE)

                        notify_ok(tr(lang, "updated"))
                        ui.open('/')

                    ui.button(tr(lang,"save") + " (Details)", on_click=save_details).props('outline')

                    # Save score
                    def save_score(match_id=match_id):
                        nonlocal mdf
                        val = normalize_digits(res_in.value or "")
                        if val and not re.fullmatch(r"\d{1,2}-\d{1,2}", val):
                            notify_err(tr(lang,"fmt_error"))
                            return

                        # update in matches
                        mdf.loc[mdf["MatchID"].astype(str) == str(match_id), ["Result","RealWinner"]] = [
                            (val if val else None), (rw_in.value or "")
                        ]
                        save_csv(mdf, MATCHES_FILE)

                        # recompute LB
                        pdf = load_csv(PREDICTIONS_FILE, ["User","MatchID","Match","Prediction","Winner","SubmittedAt"])
                        recompute_leaderboard(pdf)

                        # move to history if scored
                        if val:
                            hist = load_csv(
                                MATCH_HISTORY_FILE,
                                ["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"]
                            )
                            if hist.empty:
                                hist = pd.DataFrame(columns=["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"])

                            current_row = mdf[mdf["MatchID"].astype(str) == str(match_id)].copy()
                            current_row["CompletedAt"] = datetime.now(ZoneInfo("UTC")).isoformat()
                            hist = pd.concat([hist, current_row], ignore_index=True)
                            save_csv(hist, MATCH_HISTORY_FILE)

                            # remove from open matches
                            mdf = mdf[mdf["MatchID"].astype(str) != str(match_id)]
                            save_csv(mdf, MATCHES_FILE)

                        notify_ok(tr(lang, "updated"))
                        ui.open('/')

                    ui.button(tr(lang,"save") + " (Score)", on_click=save_score).props('outline')

                    # DELETE MATCH (and delete all predictions of that match)
                    def delete_match_and_predictions(match_id=match_id):
                        nonlocal mdf
                        # delete match from open matches
                        mdf = mdf[mdf["MatchID"].astype(str) != str(match_id)]
                        save_csv(mdf, MATCHES_FILE)

                        # also delete from history if exists (optional but usually desired)
                        hist = load_csv(
                            MATCH_HISTORY_FILE,
                            ["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"]
                        )
                        if not hist.empty:
                            hist = hist[hist["MatchID"].astype(str) != str(match_id)]
                            save_csv(hist, MATCH_HISTORY_FILE)

                        # delete predictions of that match
                        pdf = load_csv(PREDICTIONS_FILE, ["User","MatchID","Match","Prediction","Winner","SubmittedAt"])
                        if not pdf.empty:
                            pdf = pdf[pdf["MatchID"].astype(str) != str(match_id)]
                            save_csv(pdf, PREDICTIONS_FILE)

                        # recompute LB (IMPORTANT after deleting)
                        recompute_leaderboard(pdf)

                        notify_ok(tr(lang, "deleted"))
                        ui.open('/')

                    ui.button(tr(lang,"delete") + " (Match+Preds)", on_click=delete_match_and_predictions).props('color=negative outline')

    ui.separator()

    # ---------- Admin: Delete a selected prediction ----------
    ui.label("Predictions (Admin)" if lang=="en" else "التوقعات (مشرف)").classes('text-lg font-semibold')

    preds_df = load_csv(PREDICTIONS_FILE, ["User","MatchID","Match","Prediction","Winner","SubmittedAt"])
    if preds_df.empty:
        ui.label("No predictions yet." if lang=="en" else "لا توجد توقعات بعد.").classes('opacity-80')
    else:
        # filter by match
        match_options = []
        # show: "MatchID | Match"
        for _, r in preds_df.drop_duplicates(subset=["MatchID"]).iterrows():
            mid = str(r.get("MatchID") or "")
            mn  = str(r.get("Match") or "")
            match_options.append(f"{mid} | {mn}")
        match_options = sorted(match_options)

        sel_match = ui.select(match_options, value=match_options[0], label=("Filter by match" if lang=="en" else "فلترة حسب المباراة")).classes('w-full')

        def _get_selected_match_id():
            s = str(sel_match.value or "")
            return s.split("|", 1)[0].strip()

        # table container
        table_container = ui.column().classes('w-full')

        def render_preds_table():
            table_container.clear()
            mid = _get_selected_match_id()
            view = preds_df[preds_df["MatchID"].astype(str) == str(mid)].copy()
            view["SubmittedAt"] = pd.to_datetime(view["SubmittedAt"], errors="coerce")
            view = view.sort_values("SubmittedAt", ascending=False)

            rows = []
            for i, r in view.iterrows():
                rows.append({
                    "_rowid": str(i),
                    "User": str(r.get("User") or ""),
                    "Prediction": str(r.get("Prediction") or ""),
                    "Winner": str(r.get("Winner") or ""),
                    "SubmittedAt": str(r.get("SubmittedAt") or ""),
                    "MatchID": str(r.get("MatchID") or ""),
                    "Match": str(r.get("Match") or ""),
                })

            with table_container:
                if not rows:
                    ui.label("No predictions for this match." if lang=="en" else "لا توجد توقعات لهذه المباراة.").classes('opacity-80')
                    return

                ui.label(f"{len(rows)} prediction(s)").classes('text-sm opacity-80')

                # choose a row to delete (by index)
                # show readable key: "User | Prediction | Winner"
                pick_options = [
                    f"{r['_rowid']} | {r['User']} | {r['Prediction']} | {r['Winner']}"
                    for r in rows
                ]
                pick = ui.select(pick_options, value=pick_options[0], label=("Select prediction to delete" if lang=="en" else "اختر التوقع للحذف")).classes('w-full')

                def delete_selected_prediction():
                    nonlocal preds_df
                    rowid = str(pick.value).split("|", 1)[0].strip()

                    pdf = load_csv(PREDICTIONS_FILE, ["User","MatchID","Match","Prediction","Winner","SubmittedAt"])
                    if pdf.empty:
                        notify_err("No predictions file." if lang=="en" else "لا يوجد ملف توقعات.")
                        return
                    # drop by original dataframe index stored in _rowid (works because we used current file read indices)
                    try:
                        rid = int(rowid)
                        pdf2 = pdf.drop(index=rid, errors="ignore")
                        if len(pdf2) == len(pdf):
                            notify_err("Prediction not found." if lang=="en" else "لم يتم العثور على التوقع.")
                            return
                        save_csv(pdf2, PREDICTIONS_FILE)
                        preds_df = pdf2
                        recompute_leaderboard(preds_df)
                        notify_ok("Prediction deleted." if lang=="en" else "تم حذف التوقع.")
                        ui.open('/')
                    except Exception:
                        notify_err("Failed deleting prediction." if lang=="en" else "فشل حذف التوقع.")

                ui.button("Delete selected prediction" if lang=="en" else "حذف التوقع المحدد", on_click=delete_selected_prediction)\
                  .props('color=negative outline')

                # quick view table
                cols = [
                    {"name":"User","label":"User" if lang=="en" else "المستخدم","field":"User","align":"left"},
                    {"name":"Prediction","label":"Prediction" if lang=="en" else "التوقع","field":"Prediction","align":"left"},
                    {"name":"Winner","label":"Winner" if lang=="en" else "الفائز","field":"Winner","align":"left"},
                    {"name":"SubmittedAt","label":"SubmittedAt","field":"SubmittedAt","align":"left"},
                ]
                ui.table(columns=cols, rows=rows, row_key="_rowid").classes('w-full')

        sel_match.on('update:model-value', lambda _: render_preds_table())
        render_preds_table()

    ui.separator()

    # ---------- Match History ----------
    ui.label(tr(lang, "match_history")).classes('text-lg font-semibold')
    hist = load_csv(
        MATCH_HISTORY_FILE,
        ["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"]
    )
    if hist.empty:
        ui.label(tr(lang,"no_matches")).classes('opacity-80')
    else:
        view = hist.copy()
        view["Kickoff"] = view["Kickoff"].apply(parse_iso_dt)
        view["CompletedAt"] = pd.to_datetime(view["CompletedAt"], errors="coerce")
        view = view.sort_values("CompletedAt", ascending=False)

        tz_str = app.storage.user.get('tz', DEFAULT_TZ) or DEFAULT_TZ
        tz = ZoneInfo(tz_str)

        rows = []
        for _, r in view.iterrows():
            rows.append({
                "MatchID": str(r.get("MatchID") or ""),
                "Match": str(r.get("Match") or ""),
                "Kickoff": format_dt_ampm(r.get("Kickoff"), tz, lang),
                "Result": str(r.get("Result") or ""),
                "RealWinner": str(r.get("RealWinner") or ""),
                "Occasion": str(r.get("Occasion") or ""),
                "Round": str(r.get("Round") or ""),
                "CompletedAt": str(r.get("CompletedAt") or ""),
            })

        cols = [{"name":k,"label":k,"field":k,"align":"left"} for k in ["MatchID","Match","Kickoff","Result","RealWinner","Occasion","Round","CompletedAt"]]
        ui.table(columns=cols, rows=rows, row_key="MatchID").classes('w-full')


# ─────────────────────────────
# Hook admin page to include match & prediction tools
# ─────────────────────────────
def page_admin():
    lang = get_lang()
    top_bar()
    ui.separator()

    ui.label(f"🔑 {tr(lang,'admin_panel')}").classes('text-xl font-semibold')
    ui.separator()

    # Season controls + Users (terminate/delete/reset pin) from Part 5:
    # (already included in Part 5 as page_admin; keep it the same)
    # Here we just call the already-defined sections:
    # 1) season controls + registered users + reset pin
    # 2) matches + predictions admin tools

    # --- Season + Users section (from Part 5) ---
    # We reuse the Part 5 body by calling helper function if you had it;
    # if not, keep Part 5 content as-is and remove the next line.
    # (To keep minimal changes, we simply call the match/pred section after it.)
    page_admin_matches_and_predictions()


# ─────────────────────────────
# Main run (FIX storage_secret + multiprocessing guard)
# ─────────────────────────────
def _storage_secret():
    # Use env var if you want stable sessions across restarts
    s = os.environ.get("NICEGUI_STORAGE_SECRET", "").strip()
    if s:
        return s
    # fallback stable secret file on disk
    secret_file = os.path.join(DATA_DIR, ".storage_secret")
    try:
        if os.path.exists(secret_file) and os.path.getsize(secret_file) > 0:
            return open(secret_file, "r", encoding="utf-8").read().strip()
        s = secrets.token_hex(32)
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(s)
        return s
    except Exception:
        return secrets.token_hex(32)


# IMPORTANT: NiceGUI needs this guard for multiprocessing on Windows/Python 3.13
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="⚽ Football Predictions",
        reload=False,             # keep False for stability on Windows
        storage_secret=_storage_secret(),
    )
