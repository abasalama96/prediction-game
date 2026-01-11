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
st.set_page_config(page_title="⚽ Football Predictions", layout="wide")

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
# Central schemas (NEW: MatchID)
# ─────────────────────────────
MATCH_COLS = ["MatchID","Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"]
HIST_COLS  = MATCH_COLS + ["CompletedAt"]
PRED_COLS  = ["User","MatchID","Match","Prediction","Winner","SubmittedAt"]

# ─────────────────────────────
# i18n
# ─────────────────────────────
LANG = {
    "en": {
        "app_title": "⚽ Football Predictions",
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
        "app_title": "⚽ توقعات كرة القدم",
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

def _gen_match_id(match_name: str, kickoff_iso: str) -> str:
    # Stable ID based on kickoff + match name (unique even if teams repeat at different times)
    base = f"{str(match_name or '').strip()}|{str(kickoff_iso or '').strip()}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

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
        day_w  = "يوم" if days==1 else "ايام"
        hour_w = "ساعة" if hours==1 else "ساعات"
        min_w  = "دقيقة" if minutes==1 else "دقائق"
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

def get_known_teams() -> list:
    logos = _load_team_logos()
    return sorted([k for k in logos.keys() if k])

def ensure_history_schema(df: pd.DataFrame) -> pd.DataFrame:
    cols = HIST_COLS
    if df.empty: 
        return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns: 
            df[c] = None
    return df[cols]

# Safe logo renderer (works for local paths & URLs, ignores bad images)
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
# Theme
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
# NEW: Auto-migrate existing CSVs to MatchID-based system
# ─────────────────────────────
def _migrate_matches_add_ids():
    m = load_csv(MATCHES_FILE, MATCH_COLS)
    if not m.empty:
        # If MatchID missing/empty, generate from Match+Kickoff
        m["MatchID"] = m.apply(lambda r: (str(r.get("MatchID") or "").strip() or _gen_match_id(r.get("Match"), r.get("Kickoff"))), axis=1)
        save_csv(m, MATCHES_FILE)

    h = load_csv(MATCH_HISTORY_FILE, HIST_COLS)
    if not h.empty:
        h["MatchID"] = h.apply(lambda r: (str(r.get("MatchID") or "").strip() or _gen_match_id(r.get("Match"), r.get("Kickoff"))), axis=1)
        save_csv(h, MATCH_HISTORY_FILE)

def _migrate_predictions_add_ids():
    preds = load_csv(PREDICTIONS_FILE, PRED_COLS)
    if preds.empty:
        return

    # Build lookup from existing matches+history (best-effort for old predictions)
    matches_full = pd.concat([
        load_csv(MATCHES_FILE, MATCH_COLS),
        load_csv(MATCH_HISTORY_FILE, HIST_COLS).drop(columns=["CompletedAt"], errors="ignore")
    ], ignore_index=True)

    if matches_full.empty:
        # still ensure columns exist
        preds["MatchID"] = preds.get("MatchID", None)
        save_csv(preds, PREDICTIONS_FILE)
        return

    # Fill missing MatchID by matching the stored "Match" string (best effort).
    def _fill_id(row):
        mid = str(row.get("MatchID") or "").strip()
        if mid:
            return mid
        mname = str(row.get("Match") or "").strip()
        hit = matches_full[matches_full["Match"].astype(str).str.strip() == mname]
        if hit.empty:
            return ""
        return str(hit.iloc[0]["MatchID"] or "").strip()

    preds["MatchID"] = preds.apply(_fill_id, axis=1)
    save_csv(preds, PREDICTIONS_FILE)

def ensure_matchid_system_ready():
    _migrate_matches_add_ids()
    _migrate_predictions_add_ids()
# ─────────────────────────────
# Scoring & leaderboard (MatchID-based)
# ─────────────────────────────

def _score_prediction(pred_score: str, real_score: str, is_golden: bool) -> tuple[int,int,int]:
    """
    Returns (points, exact_count, outcome_count)
    Scoring:
      - Exact score: 6 points (golden: 12)
      - Correct outcome (W/L/Draw): 2 points (golden: 4)
    """
    try:
        ps = normalize_digits(pred_score)
        rs = normalize_digits(real_score)
        pa, pb = map(int, ps.split("-"))
        ra, rb = map(int, rs.split("-"))
    except Exception:
        return (0, 0, 0)

    if pa == ra and pb == rb:
        pts = 12 if is_golden else 6
        return (pts, 1, 0)

    # outcome
    if (pa > pb and ra > rb) or (pa < pb and ra < rb) or (pa == pb and ra == rb):
        pts = 4 if is_golden else 2
        return (pts, 0, 1)

    return (0, 0, 0)

def recompute_leaderboard(preds_df: pd.DataFrame | None = None):
    # Load all data
    preds = preds_df if isinstance(preds_df, pd.DataFrame) else load_csv(PREDICTIONS_FILE, PRED_COLS)
    matches = load_csv(MATCHES_FILE, MATCH_COLS)
    history = load_csv(MATCH_HISTORY_FILE, HIST_COLS)

    if preds.empty:
        save_csv(pd.DataFrame(columns=["User","Predictions","Exact","Outcome","Points"]), LEADERBOARD_FILE)
        return

    # Build finished matches lookup (history preferred)
    finished = pd.concat([
        history,
        matches[matches["Result"].notna() & (matches["Result"]!="")]
    ], ignore_index=True)

    lb = {}

    for _, p in preds.iterrows():
        user = p["User"]
        mid  = str(p.get("MatchID") or "").strip()
        if not mid:
            continue

        # find finished match by MatchID
        mrow = finished[finished["MatchID"] == mid]
        if mrow.empty:
            continue

        m = mrow.iloc[0]
        pts, ex, oc = _score_prediction(p["Prediction"], m["Result"], bool(m["BigGame"]))

        if user not in lb:
            lb[user] = {"User": user, "Predictions": 0, "Exact": 0, "Outcome": 0, "Points": 0}

        lb[user]["Predictions"] += 1
        lb[user]["Exact"]       += ex
        lb[user]["Outcome"]     += oc
        lb[user]["Points"]      += pts

    df = pd.DataFrame(lb.values())
    if df.empty:
        df = pd.DataFrame(columns=["User","Predictions","Exact","Outcome","Points"])
    else:
        df = df.sort_values(["Points","Exact","Outcome","Predictions"], ascending=[False,False,False,True])

    save_csv(df, LEADERBOARD_FILE)

# ─────────────────────────────
# Match time helpers
# ─────────────────────────────

def _kickoff_status(kickoff_iso: str, tz: ZoneInfo):
    dt = parse_iso_dt(kickoff_iso)
    if not dt:
        return ("closed", None)

    loc = to_tz(dt, tz)
    now = datetime.now(tz)
    open_at = loc - timedelta(hours=2)

    if now < open_at:
        return ("not_open", open_at - now)
    if now >= loc:
        return ("closed", now - loc)
    return ("open", loc - now)

def _gold_badge(lang: str) -> str:
    return "🔥 Golden Match 🔥" if lang=="en" else "🔥 المباراة الذهبية 🔥"

# ─────────────────────────────
# Sidebar & session state
# ─────────────────────────────

def init_state():
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("user_name", "")
    st.session_state.setdefault("lang", "en")
    st.session_state.setdefault("tz", "Asia/Riyadh")

def sidebar():
    lang = st.session_state["lang"]
    st.sidebar.header(tr(lang, "sidebar_time"))

    # language
    st.sidebar.selectbox(
        tr(lang,"sidebar_lang"),
        options=["en","ar"],
        format_func=lambda x: tr(x, "lang_en") if x=="en" else tr(x,"lang_ar"),
        key="lang",
    )

    # timezone
    tz_guess = _get_tz_from_query_params(st.session_state.get("tz","Asia/Riyadh"))
    st.session_state["tz"] = st.sidebar.text_input(tr(lang,"app_timezone"), tz_guess)

def top_tabs():
    lang = st.session_state["lang"]
    if st.session_state["role"] == "admin":
        return st.tabs([tr(lang,"tab_play"), tr(lang,"tab_leaderboard"), tr(lang,"tab_admin")])
    return st.tabs([tr(lang,"tab_play"), tr(lang,"tab_leaderboard")])

# ─────────────────────────────
# Login page
# ─────────────────────────────

def page_login():
    lang = st.session_state["lang"]
    apply_theme()
    st.title(tr(lang,"app_title"))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(tr(lang,"user_login"))
        name = st.text_input(tr(lang,"your_name"))
        if st.button(tr(lang,"login")):
            if not name.strip():
                st.warning(tr(lang,"need_name"))
            else:
                users = load_csv(USERS_FILE, ["Name","CreatedAt","IsBanned","PinHash"])
                if users[(users["Name"]==name)&(users["IsBanned"]==True)].any().any():
                    st.error("User is terminated")
                else:
                    if users[users["Name"]==name].empty:
                        users = pd.concat([users, pd.DataFrame([{
                            "Name": name,
                            "CreatedAt": datetime.utcnow().isoformat(),
                            "IsBanned": False,
                            "PinHash": None
                        }])], ignore_index=True)
                        save_csv(users, USERS_FILE)
                    st.session_state["role"] = "user"
                    st.session_state["user_name"] = name
                    st.success(tr(lang,"login_ok"))
                    st.rerun()

    with col2:
        st.subheader(tr(lang,"admin_login"))
        pw = st.text_input(tr(lang,"admin_pass"), type="password")
        if st.button(tr(lang,"login")+" (Admin)"):
            if pw == ADMIN_PASSWORD:
                st.session_state["role"] = "admin"
                st.session_state["user_name"] = "Admin"
                st.success(tr(lang,"admin_ok"))
                st.rerun()
            else:
                st.error(tr(lang,"admin_bad"))
# ─────────────────────────────
# Play page (User)
# ─────────────────────────────

def page_play(tz: ZoneInfo):
    lang = st.session_state["lang"]
    apply_theme()

    # season name
    season_name = ""
    if os.path.exists(SEASON_FILE):
        try:
            season_name = open(SEASON_FILE, "r", encoding="utf-8").read().strip()
        except Exception:
            season_name = ""

    title = tr(lang, "app_title")
    if season_name:
        title = f"{title} — {season_name}"
    st.title(title)
    show_welcome_top_right(st.session_state.get("user_name",""), lang)

    matches = load_csv(MATCHES_FILE, MATCH_COLS)
    preds = load_csv(PREDICTIONS_FILE, PRED_COLS)

    if matches.empty:
        st.info(tr(lang, "no_matches"))
        return

    # sort by kickoff
    matches = matches.copy()
    matches["_ko"] = matches["Kickoff"].apply(parse_iso_dt)
    matches = matches.sort_values("_ko").reset_index(drop=True)

    for i, row in matches.iterrows():
        match_id = str(row.get("MatchID") or "").strip()
        if not match_id:
            # should not happen; skip safely
            continue

        match_name = str(row.get("Match") or "")
        team_a, team_b = split_match_name(match_name)

        st.markdown("<div class='card'>", unsafe_allow_html=True)

        # Logos row
        cA, cO, cB = st.columns([1,1,1])
        with cA:
            show_logo_safe(row.get("HomeLogo"), width=56, caption=team_a or " ")
        with cO:
            show_logo_safe(row.get("OccasionLogo"), width=56, caption=str(row.get("Occasion") or " "))
        with cB:
            show_logo_safe(row.get("AwayLogo"), width=56, caption=team_b or " ")

        st.markdown(f"### {team_a} &nbsp;vs&nbsp; {team_b}")

        aux = []
        if str(row.get("Round") or "").strip():
            aux.append(f"**{tr(lang,'round')}**: {row.get('Round')}")
        if str(row.get("Occasion") or "").strip():
            aux.append(f"**{tr(lang,'occasion')}**: {row.get('Occasion')}")
        if aux:
            st.caption(" | ".join(aux))

        ko_dt = parse_iso_dt(row.get("Kickoff"))
        st.caption(f"{tr(lang,'kickoff')}: {format_dt_ampm(ko_dt, tz, lang)}")

        is_golden = bool(row.get("BigGame", False))
        if is_golden:
            st.markdown(f"<span class='badge-gold'>{_gold_badge(lang)}</span>", unsafe_allow_html=True)

        status, delta = _kickoff_status(row.get("Kickoff"), tz)

        # User must be logged in
        current_user = st.session_state.get("user_name","").strip()
        if not current_user:
            st.warning(tr(lang, "please_login_first"))
            st.markdown("</div>", unsafe_allow_html=True)
            continue

        # Has this user already submitted for this MATCHID?
        already = preds[(preds["User"] == current_user) & (preds["MatchID"].astype(str) == match_id)]
        already = already.sort_values("SubmittedAt") if not already.empty else already

        if status == "not_open":
            st.info(f"{tr(lang,'opens_in')}: {human_delta(delta, lang)}" if delta else tr(lang,'opens_in'))
        elif status == "closed":
            st.caption(f"🔒 {tr(lang,'closed')}")
        else:
            # open
            if not already.empty:
                st.info(tr(lang, "already_submitted"))
            else:
                # Two-box system:
                # 1) Score input (order-insensitive for exact scoring)
                # 2) Winner choice (disabled when draw is typed)
                short_hash = abs(hash(match_id)) % 1_000_000_000
                score_key = f"pred_score_{i}_{short_hash}"
                win_key   = f"pred_winner_{i}_{short_hash}"
                btn_key   = f"pred_btn_{i}_{short_hash}"

                raw_score = st.text_input(tr(lang,"score"), key=score_key)
                val = normalize_digits(raw_score or "")

                # Determine if typed as draw (a-b with a==b)
                is_draw_typed = False
                if re.fullmatch(r"\d{1,2}-\d{1,2}", val):
                    try:
                        a, b = map(int, val.split("-"))
                        is_draw_typed = (a == b)
                    except Exception:
                        is_draw_typed = False

                # Winner selectbox (blocked if draw)
                options = [team_a, team_b, tr(lang,"draw")]
                default_ix = 2 if is_draw_typed else 0
                winner = st.selectbox(
                    tr(lang,"winner"),
                    options=options,
                    index=default_ix,
                    key=win_key,
                    disabled=is_draw_typed
                )

                if st.button(tr(lang,"submit_btn"), key=btn_key):
                    if not re.fullmatch(r"\d{1,2}-\d{1,2}", val):
                        st.error(tr(lang,"fmt_error"))
                    else:
                        h1, h2 = map(int, val.split("-"))
                        if not (0 <= h1 <= 20 and 0 <= h2 <= 20):
                            st.error(tr(lang,"range_error"))
                        else:
                            if h1 == h2:
                                winner = tr(lang,"draw")

                            new_row = pd.DataFrame([{
                                "User": current_user,
                                "MatchID": match_id,          # ✅ unique per match
                                "Match": match_name,          # keep for display/backups
                                "Prediction": f"{h1}-{h2}",
                                "Winner": winner,
                                "SubmittedAt": datetime.utcnow().isoformat()
                            }])

                            preds2 = pd.concat([preds, new_row], ignore_index=True)
                            save_csv(preds2, PREDICTIONS_FILE)

                            # Recompute LB immediately
                            recompute_leaderboard(preds2)

                            st.success(tr(lang,"saved_ok"))
                            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────
# Leaderboard page
# ─────────────────────────────

def page_leaderboard():
    lang = st.session_state["lang"]
    apply_theme()

    st.subheader(tr(lang,"leaderboard"))

    preds = load_csv(PREDICTIONS_FILE, PRED_COLS)
    recompute_leaderboard(preds)  # ensure up-to-date

    lb = load_csv(LEADERBOARD_FILE, ["User","Predictions","Exact","Outcome","Points"])
    if lb.empty:
        st.info(tr(lang,"no_scores_yet"))
        return

    lb = lb.reset_index(drop=True)
    lb.insert(0, tr(lang,"lb_rank"), range(1, len(lb) + 1))

    # medals
    medals = []
    for r in lb[tr(lang,"lb_rank")].tolist():
        if int(r) == 1: medals.append("🥇")
        elif int(r) == 2: medals.append("🥈")
        elif int(r) == 3: medals.append("🥉")
        else: medals.append("")
    lb[tr(lang,"lb_rank")] = lb[tr(lang,"lb_rank")].astype(str) + " " + pd.Series(medals)

    col_map = {
        "User": tr(lang,"lb_user"),
        "Predictions": tr(lang,"lb_preds"),
        "Exact": tr(lang,"lb_exact"),
        "Outcome": tr(lang,"lb_outcome"),
        "Points": tr(lang,"lb_points"),
    }

    show = lb[[tr(lang,"lb_rank"), "User","Predictions","Exact","Outcome","Points"]].rename(columns=col_map)
    st.dataframe(show, use_container_width=True)
# ─────────────────────────────
# Admin page
# ─────────────────────────────

def page_admin(tz: ZoneInfo):
    lang = st.session_state["lang"]
    apply_theme()

    st.title(f"🔑 {tr(lang,'admin_panel')}")
    show_welcome_top_right(st.session_state.get("user_name","Admin"), lang)

    # Live LB preview
    preds_all = load_csv(PREDICTIONS_FILE, PRED_COLS)
    recompute_leaderboard(preds_all)
    lb = load_csv(LEADERBOARD_FILE, ["User","Predictions","Exact","Outcome","Points"])

    st.markdown("### " + tr(lang,"leaderboard"))
    if lb.empty:
        st.info(tr(lang,"no_scores_yet"))
    else:
        lb2 = lb.copy().reset_index(drop=True)
        lb2.insert(0, tr(lang,"lb_rank"), range(1, len(lb2) + 1))
        col_map = {
            "User": tr(lang,"lb_user"),
            "Predictions": tr(lang,"lb_preds"),
            "Exact": tr(lang,"lb_exact"),
            "Outcome": tr(lang,"lb_outcome"),
            "Points": tr(lang,"lb_points"),
        }
        view = lb2[[tr(lang,"lb_rank"),"User","Predictions","Exact","Outcome","Points"]].rename(columns=col_map)
        st.dataframe(view, use_container_width=True)

    st.markdown("---")

    # Season
    st.markdown(f"### {tr(lang,'season_settings')}")
    current_season = ""
    if os.path.exists(SEASON_FILE):
        try:
            current_season = open(SEASON_FILE, "r", encoding="utf-8").read().strip()
        except Exception:
            current_season = ""
    season_name = st.text_input(tr(lang,"season_name_label"), value=current_season, key="season_name_admin")

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button(tr(lang,"season_saved"), key="btn_save_season"):
            try:
                with open(SEASON_FILE, "w", encoding="utf-8") as f:
                    f.write((season_name or "").strip())
                st.success(tr(lang,"season_saved"))
            except Exception as e:
                st.error(str(e))

    with c2:
        if st.button(tr(lang,"reset_season"), key="btn_reset_season"):
            def _safe_rm(p):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            for f in [USERS_FILE, MATCHES_FILE, MATCH_HISTORY_FILE, PREDICTIONS_FILE, LEADERBOARD_FILE, SEASON_FILE]:
                _safe_rm(f)

            # keep team_logos.json + logo dir (as you wanted before)
            st.session_state.pop("role", None)
            st.session_state.pop("user_name", None)
            st.success(tr(lang,"reset_confirm"))
            st.rerun()

    with c3:
        if st.button(tr(lang,"test_data"), key="btn_test_data"):
            tz_local = ZoneInfo("Asia/Riyadh")
            now = datetime.now(tz_local)

            samples = [
                ("Real Madrid","Barcelona",
                 "https://upload.wikimedia.org/wikipedia/en/5/56/Real_Madrid_CF.svg",
                 "https://upload.wikimedia.org/wikipedia/en/4/47/FC_Barcelona_%28crest%29.svg",
                 now + timedelta(days=1), 9, 0, tr(lang,"ampm_pm"), True, "El Clásico",
                 "https://upload.wikimedia.org/wikipedia/commons/8/8f/Trophy_icon.png", "Round 1"),
                ("Al Hilal","Al Nassr",
                 "https://upload.wikimedia.org/wikipedia/en/f/f1/Al_Hilal_SFC_Logo.svg",
                 "https://upload.wikimedia.org/wikipedia/en/5/53/Al-Nassr_logo_2020.svg",
                 now + timedelta(days=3), 9, 0, tr(lang,"ampm_pm"), False, "Saudi Derby",
                 "https://upload.wikimedia.org/wikipedia/commons/8/8f/Trophy_icon.png", "Round 2"),
            ]

            m = load_csv(MATCHES_FILE, MATCH_COLS)

            for A,B,Au,Bu,dt_,hr,mi,ap,big,occ,occlogo,rnd in samples:
                is_pm = (ap in ["PM","مساء"])
                hr24 = (0 if hr == 12 else int(hr)) + (12 if is_pm else 0)
                ko = datetime(dt_.year, dt_.month, dt_.day, hr24, int(mi), tzinfo=tz_local)

                A_logo = cache_logo_from_url(Au) or Au
                B_logo = cache_logo_from_url(Bu) or Bu
                occ_logo = cache_logo_from_url(occlogo) or occlogo

                save_team_logo(A, A_logo)
                save_team_logo(B, B_logo)

                match_name = f"{A} vs {B}"
                row = pd.DataFrame([{
                    "MatchID": new_match_id(match_name, ko),
                    "Match": match_name,
                    "Kickoff": ko.isoformat(),
                    "Result": None,
                    "HomeLogo": A_logo,
                    "AwayLogo": B_logo,
                    "BigGame": bool(big),
                    "RealWinner": "",
                    "Occasion": occ,
                    "OccasionLogo": occ_logo,
                    "Round": rnd,
                }])
                m = pd.concat([m, row], ignore_index=True)

            save_csv(m, MATCHES_FILE)
            st.success(tr(lang,"test_done"))
            st.rerun()

    st.markdown("---")

    # Add match (same layout + adds MatchID automatically)
    st.markdown(f"### {tr(lang,'add_match')}")

    colA, colB = st.columns(2)
    with colA:
        teamA = st.text_input(tr(lang,"team_a"), key="add_team_a")
        urlA  = st.text_input(tr(lang,"home_logo_url"), value=get_saved_logo(teamA) or "", key="add_url_a")
        upA   = st.file_uploader(tr(lang,"home_logo_upload"), type=["png","jpg","jpeg","webp","gif","bmp"], key="add_up_a")
        st.caption("Preview")
        if upA is not None:
            st.image(upA, width=56)
        else:
            show_logo_safe(urlA or get_saved_logo(teamA), width=56, caption=teamA or " ")

    with colB:
        teamB = st.text_input(tr(lang,"team_b"), key="add_team_b")
        urlB  = st.text_input(tr(lang,"away_logo_url"), value=get_saved_logo(teamB) or "", key="add_url_b")
        upB   = st.file_uploader(tr(lang,"away_logo_upload"), type=["png","jpg","jpeg","webp","gif","bmp"], key="add_up_b")
        st.caption("Preview")
        if upB is not None:
            st.image(upB, width=56)
        else:
            show_logo_safe(urlB or get_saved_logo(teamB), width=56, caption=teamB or " ")

    colO1, colO2 = st.columns(2)
    with colO1:
        occ = st.text_input(tr(lang,"occasion"), key="add_occasion")
        occ_url = st.text_input(tr(lang,"occasion_logo_url"), key="add_occ_url")
        occ_up  = st.file_uploader(tr(lang,"occasion_logo_upload"), type=["png","jpg","jpeg","webp","gif","bmp"], key="add_occ_up")
        st.caption("Preview")
        if occ_up is not None:
            st.image(occ_up, width=56)
        else:
            show_logo_safe(occ_url, width=56, caption=occ or " ")
    with colO2:
        rnd = st.text_input(tr(lang,"round"), key="add_round")

    colD1, colD2, colD3, colD4, colD5 = st.columns([1,1,1,1,1])
    with colD1:
        tz_local = ZoneInfo("Asia/Riyadh")
        date_val = st.date_input(tr(lang,"date_label"), value=datetime.now(tz_local).date(), key="add_date")
    with colD2:
        hour = st.number_input(tr(lang,"hour"), min_value=1, max_value=12, value=9, key="add_hour")
    with colD3:
        minute = st.number_input(tr(lang,"minute"), min_value=0, max_value=59, value=0, key="add_minute")
    with colD4:
        ampm = st.selectbox(tr(lang,"ampm"), [tr(lang,"ampm_am"), tr(lang,"ampm_pm")], key="add_ampm")
    with colD5:
        big = st.checkbox(tr(lang,"big_game"), key="add_big")

    if st.button(tr(lang,"btn_add_match"), key="btn_add_match"):
        if not teamA or not teamB:
            st.error(tr(lang, "enter_both_teams"))
        else:
            is_pm = (ampm in ["PM","مساء"])
            hour24 = (0 if int(hour) == 12 else int(hour)) + (12 if is_pm else 0)
            ko = datetime.combine(date_val, dtime(hour24, int(minute))).replace(tzinfo=tz_local)

            home_logo = None
            away_logo = None
            occ_logo_final = None

            if upA is not None:
                home_logo = save_uploaded_logo(upA, f"{teamA}_home")
            elif str(urlA or "").strip():
                home_logo = cache_logo_from_url(str(urlA).strip()) or str(urlA).strip()
            elif get_saved_logo(teamA):
                home_logo = get_saved_logo(teamA)

            if upB is not None:
                away_logo = save_uploaded_logo(upB, f"{teamB}_away")
            elif str(urlB or "").strip():
                away_logo = cache_logo_from_url(str(urlB).strip()) or str(urlB).strip()
            elif get_saved_logo(teamB):
                away_logo = get_saved_logo(teamB)

            if occ_up is not None:
                occ_logo_final = save_uploaded_logo(occ_up, f"{occ}_occasion")
            elif str(occ_url or "").strip():
                occ_logo_final = cache_logo_from_url(str(occ_url).strip()) or str(occ_url).strip()

            if teamA and home_logo:
                save_team_logo(teamA, home_logo)
            if teamB and away_logo:
                save_team_logo(teamB, away_logo)

            match_name = f"{teamA} vs {teamB}"

            m = load_csv(MATCHES_FILE, MATCH_COLS)
            row = pd.DataFrame([{
                "MatchID": new_match_id(match_name, ko),  # ✅ unique per match
                "Match": match_name,
                "Kickoff": ko.isoformat(),
                "Result": None,
                "HomeLogo": home_logo,
                "AwayLogo": away_logo,
                "BigGame": bool(big),
                "RealWinner": "",
                "Occasion": occ or "",
                "OccasionLogo": occ_logo_final,
                "Round": rnd or "",
            }])

            m = pd.concat([m, row], ignore_index=True)
            save_csv(m, MATCHES_FILE)

            st.success(tr(lang,"match_added"))
            st.rerun()

    st.markdown("---")

    # Edit matches (open)
    st.markdown(f"### {tr(lang,'edit_matches')}")
    mdf = load_csv(MATCHES_FILE, MATCH_COLS)

    if mdf.empty:
        st.info(tr(lang,"no_matches"))
    else:
        mdf = mdf.copy()
        mdf["_ko"] = mdf["Kickoff"].apply(parse_iso_dt)
        mdf = mdf.sort_values("_ko").reset_index(drop=True)

        for idx, row in mdf.iterrows():
            st.markdown("---")

            match_id = str(row.get("MatchID") or "")
            match_name = str(row.get("Match") or "")
            team_a, team_b = split_match_name(match_name)

            st.markdown(f"**{match_name}**")
            st.caption(f"{tr(lang,'kickoff')}: {format_dt_ampm(parse_iso_dt(row.get('Kickoff')), tz, lang)}")

            c1, c2, c3 = st.columns(3)
            with c1:
                new_team_a = st.text_input(tr(lang,"team_a"), value=team_a, key=f"edit_team_a_{idx}")
                new_url_a  = st.text_input(tr(lang,"home_logo_url"), value=str(row.get("HomeLogo") or ""), key=f"edit_url_a_{idx}")
                st.caption("Preview")
                show_logo_safe(new_url_a or get_saved_logo(new_team_a), width=56, caption=new_team_a or " ")

            with c2:
                new_occ = st.text_input(tr(lang,"occasion"), value=str(row.get("Occasion") or ""), key=f"edit_occ_{idx}")
                new_occ_url  = st.text_input(tr(lang,"occasion_logo_url"), value=str(row.get("OccasionLogo") or ""), key=f"edit_occ_url_{idx}")
                st.caption("Preview")
                show_logo_safe(new_occ_url, width=56, caption=new_occ or " ")

            with c3:
                new_team_b = st.text_input(tr(lang,"team_b"), value=team_b, key=f"edit_team_b_{idx}")
                new_url_b  = st.text_input(tr(lang,"away_logo_url"), value=str(row.get("AwayLogo") or ""), key=f"edit_url_b_{idx}")
                st.caption("Preview")
                show_logo_safe(new_url_b or get_saved_logo(new_team_b), width=56, caption=new_team_b or " ")

            rcol = st.columns(3)
            with rcol[0]:
                new_round = st.text_input(tr(lang,"round"), value=str(row.get("Round") or ""), key=f"edit_round_{idx}")
            with rcol[1]:
                local_ko = parse_iso_dt(row.get("Kickoff"))
                local_ko = to_tz(local_ko, tz) if local_ko else None
                use_date = local_ko.date() if local_ko else datetime.now(tz).date()
                nd = st.date_input(tr(lang,"date_label"), value=use_date, key=f"edit_date_{idx}")
            with rcol[2]:
                local_ko = parse_iso_dt(row.get("Kickoff"))
                local_ko = to_tz(local_ko, tz) if local_ko else None
                hr12 = ((local_ko.hour % 12) or 12) if local_ko else 9
                mins = local_ko.minute if local_ko else 0
                ap = tr(lang,"ampm_pm") if (local_ko and local_ko.hour >= 12) else tr(lang,"ampm_am")

                nh = st.number_input(tr(lang,"hour"), min_value=1, max_value=12, value=int(hr12), key=f"edit_hour_{idx}")
                nm = st.number_input(tr(lang,"minute"), min_value=0, max_value=59, value=int(mins), key=f"edit_min_{idx}")
                nap = st.selectbox(tr(lang,"ampm"), [tr(lang,"ampm_am"), tr(lang,"ampm_pm")],
                                   index=0 if ap == tr(lang,"ampm_am") else 1, key=f"edit_ampm_{idx}")

            big_val = st.checkbox(tr(lang,"big_game"), value=bool(row.get("BigGame", False)), key=f"edit_big_{idx}")

            e1, e2 = st.columns([1,1])
            with e1:
                res = st.text_input(tr(lang,"final_score"), value=str(row.get("Result") or ""), key=f"edit_res_{idx}")
            with e2:
                opts = [new_team_a, new_team_b, tr(lang,"draw")]
                curw = str(row.get("RealWinner") or "").strip()

                # If result is set and is draw, force draw selection
                if isinstance(row.get("Result"), str) and "-" in str(row.get("Result")):
                    try:
                        ra, rb = map(int, normalize_digits(str(row.get("Result"))).split("-"))
                        curw = tr(lang,"draw") if ra == rb else (new_team_a if ra > rb else new_team_b)
                    except Exception:
                        pass

                if curw not in opts:
                    curw = opts[-1]

                realw = st.selectbox(tr(lang,"real_winner"), options=opts, index=opts.index(curw), key=f"edit_realw_{idx}")

            col_actions1, col_actions2, col_actions3 = st.columns([1,1,1])

            # ✅ Save DETAILS (keeps same MatchID, only changes display fields)
            with col_actions1:
                if st.button(tr(lang,"save") + " (Details)", key=f"btn_save_details_{idx}"):
                    ispm = (nap in ["PM","مساء"])
                    hr24 = (0 if int(nh) == 12 else int(nh)) + (12 if ispm else 0)
                    new_ko = datetime(nd.year, nd.month, nd.day, hr24, int(nm), tzinfo=tz)

                    final_logo_a = cache_logo_from_url(new_url_a) or (str(new_url_a).strip() if str(new_url_a).strip() else None)
                    final_logo_b = cache_logo_from_url(new_url_b) or (str(new_url_b).strip() if str(new_url_b).strip() else None)
                    final_occ_logo = cache_logo_from_url(new_occ_url) or (str(new_occ_url).strip() if str(new_occ_url).strip() else None)

                    if new_team_a and final_logo_a:
                        save_team_logo(new_team_a, final_logo_a)
                    if new_team_b and final_logo_b:
                        save_team_logo(new_team_b, final_logo_b)

                    new_match_name = f"{new_team_a} vs {new_team_b}"

                    # update by MatchID, not by Match name ✅
                    mdf.loc[mdf["MatchID"].astype(str) == match_id, ["Match","Kickoff","HomeLogo","AwayLogo","BigGame","Occasion","OccasionLogo","Round"]] = [
                        new_match_name,
                        new_ko.isoformat(),
                        final_logo_a,
                        final_logo_b,
                        bool(big_val),
                        new_occ or "",
                        final_occ_logo,
                        new_round or "",
                    ]
                    save_csv(mdf[MATCH_COLS], MATCHES_FILE)
                    st.success(tr(lang,"updated"))
                    st.rerun()

            # ✅ Save SCORE (and then move completed match to history using MatchID)
            with col_actions2:
                if st.button(tr(lang,"save") + " (Score)", key=f"btn_save_score_{idx}"):
                    val = normalize_digits(res or "").strip()
                    if val and not re.fullmatch(r"\d{1,2}-\d{1,2}", val):
                        st.error(tr(lang,"fmt_error"))
                    else:
                        # update score and real winner by MatchID ✅
                        mdf.loc[mdf["MatchID"].astype(str) == match_id, ["Result","RealWinner"]] = [
                            (val if val else None),
                            (realw or "")
                        ]
                        save_csv(mdf[MATCH_COLS], MATCHES_FILE)

                        # recompute LB
                        preds_now = load_csv(PREDICTIONS_FILE, PRED_COLS)
                        recompute_leaderboard(preds_now)

                        # If score set => move to history
                        if val:
                            hist = load_csv(MATCH_HISTORY_FILE, HIST_COLS)
                            hist = ensure_history_schema(hist)

                            cur = mdf[mdf["MatchID"].astype(str) == match_id].copy()
                            if not cur.empty:
                                cur = cur.iloc[[0]].copy()
                                cur["CompletedAt"] = datetime.utcnow().isoformat()
                                # ensure it has all history cols
                                for c in HIST_COLS:
                                    if c not in cur.columns:
                                        cur[c] = None
                                hist = pd.concat([hist, cur[HIST_COLS]], ignore_index=True)
                                save_csv(hist, MATCH_HISTORY_FILE)

                            # remove from open matches by MatchID ✅
                            mdf = mdf[mdf["MatchID"].astype(str) != match_id].copy()
                            save_csv(mdf[MATCH_COLS], MATCHES_FILE)

                        st.success(tr(lang,"updated"))
                        st.rerun()

            # ✅ Delete match (by MatchID, and delete predictions for that MatchID too)
            with col_actions3:
                if st.button(tr(lang,"delete"), key=f"btn_del_{idx}"):
                    mdf2 = mdf[mdf["MatchID"].astype(str) != match_id].copy()
                    save_csv(mdf2[MATCH_COLS], MATCHES_FILE)

                    p = load_csv(PREDICTIONS_FILE, PRED_COLS)
                    if not p.empty:
                        p = p[p["MatchID"].astype(str) != match_id]
                        save_csv(p, PREDICTIONS_FILE)

                    # recompute LB after deletion
                    recompute_leaderboard(load_csv(PREDICTIONS_FILE, PRED_COLS))

                    st.success(tr(lang,"deleted"))
                    st.rerun()

    st.markdown("---")

    # Match History (Admin only)
    st.markdown(f"### {tr(lang,'match_history')}")
    hist = load_csv(MATCH_HISTORY_FILE, HIST_COLS)
    hist = ensure_history_schema(hist)

    if hist.empty:
        st.info(tr(lang,"no_matches"))
    else:
        view = hist.copy()
        view["Kickoff"] = view["Kickoff"].apply(parse_iso_dt)
        view["CompletedAt"] = pd.to_datetime(view["CompletedAt"], errors="coerce")
        view = view.sort_values("CompletedAt", ascending=False)
        view["Kickoff"] = view["Kickoff"].apply(lambda x: format_dt_ampm(x, ZoneInfo("Asia/Riyadh"), lang))
        view["CompletedAt"] = view["CompletedAt"].dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(view[["Match","Kickoff","Result","RealWinner","Occasion","Round","CompletedAt"]], use_container_width=True)

    st.markdown("---")

    # Registered Users + Terminate + Delete (kept)
    st.markdown(f"### {tr(lang,'registered_users')}")
    users_df = load_users()

    if users_df.empty:
        st.info("No users yet." if lang=="en" else "لا يوجد مستخدمون بعد.")
        return

    show = users_df.copy().sort_values("CreatedAt").rename(columns={
        "Name": tr(lang,"lb_user"),
        "CreatedAt": "CreatedAt",
        "IsBanned": "Banned",
    })
    st.dataframe(show[[tr(lang,"lb_user"), "CreatedAt", "Banned"]], use_container_width=True)

    st.markdown(" ")
    colu1, colu2 = st.columns([2,1])
    with colu1:
        target_name = st.selectbox(
            "Select user to terminate" if lang=="en" else "اختر مستخدمًا لإيقافه",
            options=show[tr(lang,"lb_user")].tolist(),
            key="terminate_name"
        )
    with colu2:
        if st.button(tr(lang,"terminate"), key="btn_terminate"):
            users_df2 = load_users()
            hit = users_df2[users_df2["Name"].astype(str).str.strip().str.casefold() == str(target_name).strip().casefold()]
            if hit.empty:
                st.error("User not found." if lang=="en" else "المستخدم غير موجود.")
            else:
                users_df2.loc[users_df2["Name"].astype(str).str.strip().str.casefold() == str(target_name).strip().casefold(), "IsBanned"] = 1
                save_users(users_df2)
                st.success(tr(lang,"terminated"))
                st.rerun()

    # Hard delete user (keep as you said it works)
    st.markdown(" ")
    del_col1, del_col2 = st.columns([2,1])
    with del_col1:
        st.caption(" ")
    with del_col2:
        del_label = "Delete user" if lang == "en" else "حذف المستخدم"
        if st.button(del_label, key="btn_delete_user"):
            users_df2 = load_users()
            mask = users_df2["Name"].astype(str).str.strip().str.casefold() != str(target_name).strip().casefold()
            if mask.all():
                st.error("User not found." if lang=="en" else "المستخدم غير موجود.")
            else:
                users_df2 = users_df2[mask]
                save_users(users_df2)
                st.success("User deleted." if lang=="en" else "تم حذف المستخدم.")
                st.rerun()


# ─────────────────────────────
# Backup / Restore (fix: recompute leaderboard after restore)
# ─────────────────────────────

def _backup_payload() -> dict:
    """Create a simple JSON backup of current CSV/JSON data."""
    def _read_text(path):
        if not os.path.exists(path):
            return ""
        try:
            return open(path, "r", encoding="utf-8").read()
        except Exception:
            try:
                return open(path, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                return ""

    return {
        "version": 1,
        "created_at": datetime.utcnow().isoformat(),
        "files": {
            "users.csv": _read_text(USERS_FILE),
            "matches.csv": _read_text(MATCHES_FILE),
            "match_history.csv": _read_text(MATCH_HISTORY_FILE),
            "predictions.csv": _read_text(PREDICTIONS_FILE),
            "leaderboard.csv": _read_text(LEADERBOARD_FILE),
            "season.txt": _read_text(SEASON_FILE),
            "team_logos.json": _read_text(TEAM_LOGOS_FILE),
        }
    }

def _write_text(path, content: str):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")
    except Exception:
        pass

def backup_ui_block():
    """Call inside admin page if you want buttons. (No UI changes elsewhere.)"""
    lang = st.session_state["lang"]

    st.markdown("---")
    st.markdown("### " + ("Backup / Restore" if lang=="en" else "نسخ احتياطي / استعادة"))

    payload = _backup_payload()
    backup_json = json.dumps(payload, ensure_ascii=False, indent=2)

    st.download_button(
        "⬇️ Download Backup (.json)" if lang=="en" else "⬇️ تنزيل النسخة الاحتياطية (.json)",
        data=backup_json.encode("utf-8"),
        file_name=f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        key="btn_download_backup",
    )

    up = st.file_uploader(
        "⬆️ Restore from Backup (.json)" if lang=="en" else "⬆️ الاستعادة من نسخة (.json)",
        type=["json"],
        key="upload_backup",
    )
    if up is not None:
        try:
            raw = up.read().decode("utf-8", errors="ignore")
            data = json.loads(raw)
            files = (data or {}).get("files", {})

            _write_text(USERS_FILE, files.get("users.csv",""))
            _write_text(MATCHES_FILE, files.get("matches.csv",""))
            _write_text(MATCH_HISTORY_FILE, files.get("match_history.csv",""))
            _write_text(PREDICTIONS_FILE, files.get("predictions.csv",""))
            _write_text(SEASON_FILE, files.get("season.txt",""))
            _write_text(TEAM_LOGOS_FILE, files.get("team_logos.json",""))
            # leaderboard.csv is OPTIONAL because we will recompute anyway
            _write_text(LEADERBOARD_FILE, files.get("leaderboard.csv",""))

            # ✅ IMPORTANT FIX: after restore, recompute leaderboard from predictions
            preds = load_csv(PREDICTIONS_FILE, PRED_COLS)
            recompute_leaderboard(preds)

            st.success("Restore complete ✅" if lang=="en" else "تمت الاستعادة ✅")
            st.rerun()

        except Exception as e:
            st.error(("Restore failed: " if lang=="en" else "فشلت الاستعادة: ") + str(e))
    # ✅ Backup / Restore buttons (added without changing other logic)
    backup_ui_block()


# ─────────────────────────────
# Router & bootstrap
# ─────────────────────────────

def run_app():
    # Sidebar language
    st.sidebar.subheader(tr('en','sidebar_lang') + " / " + tr('ar','sidebar_lang'))
    lang_choice = st.sidebar.radio("", [tr('en','lang_en'), tr('ar','lang_ar')], index=0, horizontal=True)
    lang = 'ar' if lang_choice == tr('ar','lang_ar') else 'en'
    st.session_state["lang"] = lang

    st.sidebar.subheader(tr(lang,'sidebar_time'))

    # Auto-detect browser TZ + allow override (persist to URL)
    _setup_browser_timezone_param()
    detected_tz = _get_tz_from_query_params(default_tz="Asia/Riyadh") or "Asia/Riyadh"

    common_tz = [
        "UTC",
        "Europe/London", "Europe/Madrid", "Europe/Paris", "Europe/Berlin", "Europe/Rome",
        "Africa/Cairo",
        "Asia/Riyadh", "Asia/Dubai", "Asia/Kolkata", "Asia/Singapore", "Asia/Tokyo", "Asia/Shanghai", "Asia/Hong_Kong",
        "Australia/Sydney",
        "America/Sao_Paulo",
        "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"
    ]
    if detected_tz and detected_tz not in common_tz:
        common_tz.insert(0, detected_tz)

    label_auto = f"🧭 Use browser time zone ({detected_tz})"
    tz_choice = st.sidebar.selectbox(
        tr(lang,'app_timezone'),
        [label_auto] + common_tz,
        index=0
    )
    tz_str = detected_tz if tz_choice == label_auto else tz_choice

    # Save choice back to URL (new API)
    try:
        st.query_params["tz"] = tz_str
    except Exception:
        try:
            st.query_params = {"tz": tz_str}
        except Exception:
            pass

    tz = ZoneInfo(tz_str)

    # Logout
    if st.sidebar.button("Logout" if lang=="en" else "تسجيل الخروج"):
        st.session_state.pop("role", None)
        st.session_state.pop("user_name", None)
        st.rerun()

    role = st.session_state.get("role", None)

    if role == "user":
        page_play_and_leaderboard(tz)
    elif role == "admin":
        page_admin(tz)
    else:
        page_login()


# Run
if __name__ == "__main__":
    try:
        run_app()
    except Exception as e:
        st.error("App crashed")
        st.exception(e)
