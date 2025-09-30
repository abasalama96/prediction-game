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

# Safe global tz_str (prevents NameError if referenced at top-level)
try:
    tz_str = st.query_params.get("tz", "Asia/Riyadh") or "Asia/Riyadh"
except Exception:
    tz_str = "Asia/Riyadh"

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
# Backup / Restore helpers  (Part A)
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
    Uploads the given in-memory ZIP to Supabase Storage.
    Returns the storage path if successful, else None.
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

# logo helpers
from urllib.parse import urlparse

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

# NEW: safe logo renderer
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
# Core game logic
# ─────────────────────────────
def compute_points(pred: str, actual: str, biggame: bool) -> tuple[int,int,int]:
    """
    Returns (points, exact, outcome)
    - 3 points exact, 1 outcome if not golden
    - 5 points exact, 2 outcome if golden
    """
    if not pred or not actual:
        return (0,0,0)
    try:
        pa, pb = [int(x) for x in normalize_digits(pred).split("-")]
        ra, rb = [int(x) for x in normalize_digits(actual).split("-")]
    except Exception:
        return (0,0,0)

    # exact
    if pa==ra and pb==rb:
        return (5,1,0) if biggame else (3,1,0)

    # outcome
    if (pa>pb and ra>rb) or (pa<pb and ra<rb) or (pa==pb and ra==rb):
        return (2,0,1) if biggame else (1,0,1)

    return (0,0,0)

def recompute_leaderboard():
    preds = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
    matches = load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
    lb = {}
    for _,row in preds.iterrows():
        u = row["User"]; m = row["Match"]; pred=row["Prediction"]
        if m not in matches["Match"].values: continue
        match_row = matches[matches["Match"]==m].iloc[0]
        res = match_row["Result"]; big = bool(match_row["BigGame"])
        pts,ex,out = compute_points(pred,res,big)
        if u not in lb: lb[u]={"Points":0,"Predictions":0,"Exact":0,"Outcome":0}
        lb[u]["Points"]+=pts
        lb[u]["Predictions"]+=1
        lb[u]["Exact"]+=ex
        lb[u]["Outcome"]+=out
    df = pd.DataFrame([
        {"User":u, **vals} for u,vals in lb.items()
    ])
    save_csv(df, LEADERBOARD_FILE)

# ─────────────────────────────
# Login / Auth
# ─────────────────────────────
def page_login(LANG_CODE: str):
    st.title(tr(LANG_CODE,"login_tab"))
    role = st.radio("", [tr(LANG_CODE,"user_login"), tr(LANG_CODE,"admin_login")])
    if role == tr(LANG_CODE,"user_login"):
        st.subheader(tr(LANG_CODE,"user_login"))
        name = st.text_input(tr(LANG_CODE,"your_name"), key="user_name")
        pin = st.text_input("PIN", type="password", key="user_pin")
        users = load_csv(USERS_FILE, ["User","CreatedAt","IsBanned","PinHash"])
        if st.button(tr(LANG_CODE,"login"), key="btn_user_login"):
            row = users[users["User"]==name]
            if not row.empty and _verify_pin(row.iloc[0]["PinHash"], pin):
                st.session_state["role"]="user"; st.session_state["current_name"]=name
                st.success(tr(LANG_CODE,"login_ok")); st.rerun()
            else:
                st.error(tr(LANG_CODE,"admin_bad"))
        if st.button(tr(LANG_CODE,"register"), key="btn_user_reg"):
            if not name: st.warning(tr(LANG_CODE,"need_name"))
            elif name in users["User"].values: st.warning("Name taken.")
            else:
                new = pd.DataFrame([{"User":name,"CreatedAt":datetime.now(),"IsBanned":0,"PinHash":_hash_pin(pin)}])
                save_csv(pd.concat([users,new], ignore_index=True), USERS_FILE)
                st.success("Registered. Please login.")

    elif role == tr(LANG_CODE,"admin_login"):
        st.subheader(tr(LANG_CODE,"admin_login"))
        pw = st.text_input(tr(LANG_CODE,"admin_pass"), type="password", key="admin_pw")
        if st.button(tr(LANG_CODE,"login"), key="btn_admin_login"):
            if pw == ADMIN_PASSWORD:
                st.session_state["role"]="admin"; st.session_state["current_name"]="Admin"
                st.success(tr(LANG_CODE,"admin_ok")); st.rerun()
            else:
                st.error(tr(LANG_CODE,"admin_bad"))
# ─────────────────────────────
# Play page (users submit predictions)
# ─────────────────────────────
def page_play_and_leaderboard(LANG_CODE: str, tz: ZoneInfo):
    tab1, tab2 = st.tabs([tr(LANG_CODE,"tab_play"), tr(LANG_CODE,"tab_leaderboard")])
    with tab1:
        matches = load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
        if matches.empty:
            st.info(tr(LANG_CODE,"no_matches")); return
        now = datetime.now(tz)
        for _,row in matches.iterrows():
            match_id=row["Match"]; kickoff=parse_iso_dt(row["Kickoff"])
            result=row["Result"]; big=bool(row["BigGame"])
            teamA,teamB = match_id.split(" vs ") if " vs " in match_id else ("Team A","Team B")
            st.markdown("### "+match_id)
            show_logo_safe(row["HomeLogo"] or get_saved_logo(teamA),56,teamA)
            show_logo_safe(row["AwayLogo"] or get_saved_logo(teamB),56,teamB)
            st.write(tr(LANG_CODE,"kickoff")+": "+format_dt_ampm(kickoff,tz,LANG_CODE))
            if kickoff and now<kickoff:
                delta=kickoff-now
                if delta>timedelta(hours=2):
                    st.write(tr(LANG_CODE,"opens_in")+": "+human_delta(delta-timedelta(hours=2),LANG_CODE)); continue
                st.write(tr(LANG_CODE,"closes_in")+": "+human_delta(delta,LANG_CODE))
            elif kickoff and now>=kickoff:
                st.write(tr(LANG_CODE,"closed")); continue
            preds=load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
            user=st.session_state.get("current_name")
            if not user: st.warning(tr(LANG_CODE,"please_login_first")); return
            if ((preds["User"]==user)&(preds["Match"]==match_id)).any():
                st.info(tr(LANG_CODE,"already_submitted")); continue
            pred=st.text_input(tr(LANG_CODE,"score"), key=f"pred_{match_id}")
            winner=st.selectbox(tr(LANG_CODE,"winner"), [tr(LANG_CODE,"draw"),teamA,teamB], key=f"win_{match_id}")
            if st.button(tr(LANG_CODE,"submit_btn"), key=f"btn_{match_id}"):
                p=normalize_digits(pred)
                try:
                    ga,gb=[int(x) for x in p.split("-")]
                    if not (0<=ga<=20 and 0<=gb<=20): raise ValueError
                except Exception:
                    st.error(tr(LANG_CODE,"fmt_error")); continue
                new=pd.DataFrame([{"User":user,"Match":match_id,"Prediction":p,"Winner":winner,"SubmittedAt":datetime.now(tz)}])
                save_csv(pd.concat([preds,new], ignore_index=True), PREDICTIONS_FILE)
                st.success(tr(LANG_CODE,"saved_ok")); st.rerun()

    with tab2:
        lb=load_csv(LEADERBOARD_FILE, ["User","Points","Predictions","Exact","Outcome"])
        if lb.empty:
            st.info(tr(LANG_CODE,"no_scores_yet")); return
        lb=lb.sort_values(by=["Points","Predictions"], ascending=[False,True]).reset_index(drop=True)
        st.table(lb.rename(columns={
            "User":tr(LANG_CODE,"lb_user"),
            "Points":tr(LANG_CODE,"lb_points"),
            "Predictions":tr(LANG_CODE,"lb_preds"),
            "Exact":tr(LANG_CODE,"lb_exact"),
            "Outcome":tr(LANG_CODE,"lb_outcome"),
        }))
# ─────────────────────────────
# Admin page
# ─────────────────────────────
def page_admin(LANG_CODE: str, tz: ZoneInfo):
    st.title(tr(LANG_CODE,"admin_panel"))

    # Season
    st.header(tr(LANG_CODE,"season_settings"))
    season_name = st.text_input(tr(LANG_CODE,"season_name_label"))
    if st.button(tr(LANG_CODE,"save"), key="btn_season"):
        with open(SEASON_FILE,"w",encoding="utf-8") as f: f.write(season_name or "")
        st.success(tr(LANG_CODE,"season_saved"))
    if st.button(tr(LANG_CODE,"reset_season"), key="btn_reset"):
        for f in [USERS_FILE,MATCHES_FILE,MATCH_HISTORY_FILE,PREDICTIONS_FILE,LEADERBOARD_FILE]:
            if os.path.exists(f): os.remove(f)
        st.success(tr(LANG_CODE,"reset_confirm"))

    # Backup / Restore (Part B)
    st.header("📦 Backup & Restore")
    if st.button("⬇️ Backup Now"):
        buf = create_backup_zip()
        st.download_button("Download Backup ZIP", data=buf.getvalue(), file_name="prediction_backup.zip", mime="application/zip")
        loc = upload_backup_to_supabase(buf)
        if loc: st.info(f"Also saved to Supabase Storage at: {loc}")
    up = st.file_uploader("⬆️ Restore from Backup ZIP", type="zip")
    if up and st.button("Restore Now"):
        restore_from_zip(up)
        st.success("Backup restored. Please reload the app.")
        st.rerun()

    # Test data
    if st.button(tr(LANG_CODE,"test_data")):
        df=pd.DataFrame([{
            "Match":"TeamA vs TeamB",
            "Kickoff":(datetime.now(tz)+timedelta(hours=3)).isoformat(),
            "Result":None,"HomeLogo":None,"AwayLogo":None,
            "BigGame":False,"RealWinner":None,"Occasion":"Friendly",
            "OccasionLogo":None,"Round":"1"}])
        save_csv(df, MATCHES_FILE)
        st.success(tr(LANG_CODE,"test_done"))

    # Add match
    st.header(tr(LANG_CODE,"add_match"))
    teamA=st.text_input(tr(LANG_CODE,"team_a"))
    teamB=st.text_input(tr(LANG_CODE,"team_b"))
    urlA=st.text_input(tr(LANG_CODE,"home_logo_url"))
    urlB=st.text_input(tr(LANG_CODE,"away_logo_url"))
    upA=st.file_uploader(tr(LANG_CODE,"home_logo_upload"))
    upB=st.file_uploader(tr(LANG_CODE,"away_logo_upload"))
    occasion=st.text_input(tr(LANG_CODE,"occasion"))
    occ_url=st.text_input(tr(LANG_CODE,"occasion_logo_url"))
    occ_up=st.file_uploader(tr(LANG_CODE,"occasion_logo_upload"))
    roundtxt=st.text_input(tr(LANG_CODE,"round"))
    d=st.date_input(tr(LANG_CODE,"date_label"), date.today())
    hour=st.number_input(tr(LANG_CODE,"hour"),1,12,7)
    minute=st.number_input(tr(LANG_CODE,"minute"),0,59,0)
    ampm=st.radio(tr(LANG_CODE,"ampm"), [tr(LANG_CODE,"ampm_am"), tr(LANG_CODE,"ampm_pm")])
    big=st.checkbox(tr(LANG_CODE,"big_game"))
    if st.button(tr(LANG_CODE,"btn_add_match")):
        if not teamA or not teamB: st.warning(tr(LANG_CODE,"enter_both_teams"))
        else:
            hh=hour%12 + (12 if ampm==tr(LANG_CODE,"ampm_pm") else 0)
            ko=datetime.combine(d, dtime(hh,minute), tz)
            match_id=f"{teamA} vs {teamB}"
            df=load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
            logos=(_save_logo(teamA,urlA,upA), _save_logo(teamB,urlB,upB))
            occlogo=_save_logo(occasion,occ_url,occ_up)
            new=pd.DataFrame([{"Match":match_id,"Kickoff":ko.isoformat(),"Result":None,
                               "HomeLogo":logos[0],"AwayLogo":logos[1],"BigGame":big,
                               "RealWinner":None,"Occasion":occasion,"OccasionLogo":occlogo,"Round":roundtxt}])
            save_csv(pd.concat([df,new], ignore_index=True), MATCHES_FILE)
            st.success(tr(LANG_CODE,"match_added"))

    # Edit matches
    st.header(tr(LANG_CODE,"edit_matches"))
    df=load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
    for i,row in df.iterrows():
        st.subheader(row["Match"])
        score=st.text_input(tr(LANG_CODE,"final_score"), value=row["Result"] or "", key=f"res_{i}")
        realwinner=st.text_input(tr(LANG_CODE,"real_winner"), value=row["RealWinner"] or "", key=f"rw_{i}")
        if st.button(tr(LANG_CODE,"save"), key=f"save_{i}"):
            df.at[i,"Result"]=normalize_digits(score)
            df.at[i,"RealWinner"]=realwinner
            save_csv(df, MATCHES_FILE)
            recompute_leaderboard()
            st.success(tr(LANG_CODE,"updated"))
        if st.button(tr(LANG_CODE,"delete"), key=f"del_{i}"):
            df=df.drop(i); save_csv(df, MATCHES_FILE); st.success(tr(LANG_CODE,"deleted")); st.rerun()

    # Match history
    st.header(tr(LANG_CODE,"match_history"))
    hist=load_csv(MATCH_HISTORY_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"])
    st.dataframe(hist)

    # Users
    st.header(tr(LANG_CODE,"registered_users"))
    users=load_csv(USERS_FILE, ["User","CreatedAt","IsBanned","PinHash"])
    for _,u in users.iterrows():
        st.write(u["User"])
        if st.button(tr(LANG_CODE,"terminate")+" "+u["User"], key=f"ban_{u['User']}"):
            users.loc[users["User"]==u["User"],"IsBanned"]=1
            save_csv(users, USERS_FILE)
            st.success(tr(LANG_CODE,"terminated"))
        if st.button("Delete "+u["User"], key=f"deluser_{u['User']}"):
            users=users[users["User"]!=u["User"]]
            save_csv(users, USERS_FILE)
            st.success("User deleted."); st.rerun()

def _save_logo(team, url, up):
    if up: return save_uploaded_logo(up, team)
    if url: return cache_logo_from_url(url)
    return get_saved_logo(team)
# ─────────────────────────────
# Router and app runner
# ─────────────────────────────
def run_app():
    apply_theme()

    # Browser timezone detection script
    _setup_browser_timezone_param()
    tz_str = _get_tz_from_query_params()

    # Sidebar: language + timezone
    with st.sidebar:
        LANG_CODE = st.radio("🌐 Language", ["en","ar"], index=0 if st.session_state.get("lang")=="en" else 1)
        st.session_state["lang"] = LANG_CODE

        # List of common zones
        zones = ["Asia/Riyadh","UTC","Europe/London","Europe/Paris","America/New_York","America/Los_Angeles"]
        if tz_str not in zones: zones.insert(0, tz_str)
        sel = st.selectbox("⏰ Time zone", zones, index=0)
        try:
            st.query_params["tz"] = sel
        except Exception:
            try:
                st.query_params = {"tz": sel}
            except Exception:
                pass
        tz_str = sel
        tz = ZoneInfo(tz_str)

        if st.session_state.get("role"):
            if st.button("🔒 Log out"):
                for k in ["role","current_name"]:
                    if k in st.session_state: del st.session_state[k]
                st.rerun()

    role = st.session_state.get("role")
    show_welcome_top_right(st.session_state.get("current_name"), LANG_CODE)

    if not role:
        page_login(LANG_CODE)
    elif role=="user":
        page_play_and_leaderboard(LANG_CODE, tz)
    elif role=="admin":
        page_admin(LANG_CODE, tz)

# ─────────────────────────────
# Entrypoint
# ─────────────────────────────
if __name__ == "__main__":
    run_app()