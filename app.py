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

# For security, consider: ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "madness")
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

# --- Browser time zone detection + query param bridge (NEW) ---
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
        params = st.experimental_get_query_params()
        return (params.get("tz", [default_tz]) or [default_tz])[0]
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
        # Normalize draw Arabic/English
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
    """(points, exact_flag, outcome_flag) — exact is order-insensitive; outcome uses admin 'RealWinner' or draw."""
    real = match_row.get("Result")
    if not isinstance(real, str) or not isinstance(pred, str):
        return (0,0,0)
    real_pair = normalize_score_pair(real)
    pred_pair = normalize_score_pair(pred)
    if real_pair is None or pred_pair is None:
        return (0,0,0)

    # exact
    if real_pair == pred_pair:
        return (5 if big_game else 3, 1, 0)

    # outcome (winner/draw)
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
    cols = ["User","Points","Predictions","Exact","Outcome"]
    lb = pd.DataFrame(columns=cols)
    if predictions_df.empty:
        save_csv(lb, LEADERBOARD_FILE); return lb

    matches_full = _load_all_matches_for_scoring()
    if matches_full.empty:
        save_csv(lb, LEADERBOARD_FILE); return lb

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
        save_csv(lb, LEADERBOARD_FILE); return lb

    per = pd.DataFrame(rows)
    lb = (per.groupby("User", as_index=False)
            .agg(Points=("Points","sum"), Predictions=("Points","count"),
                 Exact=("Exact","sum"), Outcome=("Outcome","sum")))
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
        pin_in  = st.text_input("PIN (4 digits)" if LANG_CODE=="en" else "الرقم السري (4 أرقام)",
                                type="password", key="login_pin")
        name_norm = (name_in or "").strip()

        if st.button(tr(LANG_CODE, "login"), key="btn_user_login"):
            if not name_norm or not re.fullmatch(r"\d{4}", normalize_digits(pin_in or "")):
                st.error(tr(LANG_CODE, "please_login_first"))
            else:
                candidates = users_df[users_df["Name"].astype(str).str.strip().str.casefold() == name_norm.casefold()]
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
        reg_pin  = st.text_input("Choose a 4-digit PIN" if LANG_CODE=="en" else "اختر رقماً سرياً من 4 أرقام",
                                 type="password", key="reg_pin")

        if st.button(tr(LANG_CODE, "register"), key="btn_register"):
            if not reg_name or not reg_name.strip():
                st.error(tr(LANG_CODE, "need_name"))
            elif not re.fullmatch(r"\d{4}", normalize_digits(reg_pin or "")):
                st.error("PIN must be 4 digits." if LANG_CODE=="en" else "الرقم السري يجب أن يكون 4 أرقام.")
            else:
                users_df = load_users()
                exists = users_df["Name"].astype(str).str.strip().str.casefold().eq(reg_name.strip().casefold()).any()
                if exists:
                    st.error("Name already exists. Please choose a different name." if LANG_CODE=="en" else "الاسم موجود مسبقًا. الرجاء اختيار اسم مختلف.")
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
                            if LANG_CODE == "ar":
                                st.info(f"{tr(LANG_CODE,'opens_in')} : {human_delta(remain, LANG_CODE)}")
                            else:
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
                                    is_draw_typed = bool(re.fullmatch(r"\s*(\d{1,2})-(\d{1,2})\s*", val) and val.split("-")[0] == val.split("-")[1])
                                    default_ix = 2 if is_draw_typed else 0
                                    winner = st.selectbox(tr(LANG_CODE,"winner"), options=options, index=default_ix, key=sel_key, disabled=is_draw_typed)

                                    if st.button(tr(LANG_CODE,"submit_btn"), key=btn_key):
                                        if not re.fullmatch(r"\d{1,2}-\d{1,2}", val):
                                            st.error(tr(LANG_CODE,"fmt_error"))
                                        else:
                                            h1, h2 = map(int, val.split("-"))
                                            if not (0 <= h1 <= 20 and 0 <= h2 <= 20):
                                                st.error(tr(LANG_CODE,"range_error"))
                                            else:
                                                if h1 == h2: winner = tr(LANG_CODE,"draw")
                                                new_pred = pd.DataFrame([{
                                                    "User": current_name,
                                                    "Match": match,
                                                    "Prediction": f"{h1}-{h2}",
                                                    "Winner": winner,
                                                    "SubmittedAt": datetime.now(ZoneInfo("UTC")).isoformat()
                                                }])
                                                predictions_df = pd.concat([predictions_df, new_pred], ignore_index=True)
                                                save_csv(predictions_df, PREDICTIONS_FILE)
                                                recompute_leaderboard(predictions_df)
                                                st.success(tr(LANG_CODE, "saved_ok"))
                        else:
                            st.caption(f"🔒 {tr(LANG_CODE,'closed')}")

    # ------------- Leaderboard -------------
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
                r = lb.loc[i, tr(LANG_CODE, "lb_rank")]
                r_int = int(str(r).split()[0])
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

# ─────────────────────────────
# Admin Page (split: Save Details / Save Score) + logo previews in Add Match
# ─────────────────────────────
def page_admin(LANG_CODE: str, tz: ZoneInfo):
    apply_theme()
    st.title(f"🔑 {tr(LANG_CODE,'admin_panel')}")
    show_welcome_top_right(st.session_state.get("current_name") or "Admin", LANG_CODE)

    # Quick LB view
    preds_all = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
    lb = recompute_leaderboard(preds_all)
    st.markdown("### " + tr(LANG_CODE,"leaderboard"))
    if lb.empty:
        st.info(tr(LANG_CODE,"no_scores_yet"))
    else:
        lb = lb.reset_index(drop=True)
        lb.insert(0, tr(LANG_CODE, "lb_rank"), range(1, len(lb) + 1))
        col_map = {
            "User": tr(LANG_CODE,"lb_user"),
            "Predictions": tr(LANG_CODE,"lb_preds"),
            "Exact": tr(LANG_CODE,"lb_exact"),
            "Outcome": tr(LANG_CODE,"lb_outcome"),
            "Points": tr(LANG_CODE,"lb_points")
        }
        view = lb[[tr(LANG_CODE,"lb_rank"),"User","Predictions","Exact","Outcome","Points"]].rename(columns=col_map)
        st.dataframe(view, use_container_width=True)

    st.markdown("---")
    # Season settings
    st.markdown(f"### {tr(LANG_CODE,'season_settings')}")
    current_season = ""
    if os.path.exists(SEASON_FILE):
        try:
            with open(SEASON_FILE,"r",encoding="utf-8") as f:
                current_season = f.read().strip()
        except Exception:
            pass
    season_name = st.text_input(tr(LANG_CODE,"season_name_label"), value=current_season, key="season_name")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button(tr(LANG_CODE,"season_saved"), key="btn_save_season"):
            try:
                with open(SEASON_FILE,"w",encoding="utf-8") as f:
                    f.write((season_name or "").strip())
                st.success(tr(LANG_CODE,"season_saved"))
            except Exception as e:
                st.error(str(e))
    with c2:
        if st.button(tr(LANG_CODE,"reset_season"), key="btn_reset_season"):
            def _safe_remove(p):
                try:
                    if os.path.exists(p): os.remove(p)
                except Exception:
                    pass
            for f in [USERS_FILE, MATCHES_FILE, MATCH_HISTORY_FILE, PREDICTIONS_FILE, LEADERBOARD_FILE, SEASON_FILE]:
                _safe_remove(f)
            st.session_state.pop("role", None)
            st.session_state.pop("current_name", None)
            st.success(tr(LANG_CODE,"reset_confirm"))
            st.rerun()
    with c3:
        if st.button(tr(LANG_CODE,"test_data"), key="btn_test_data"):
            tz_local = ZoneInfo("Asia/Riyadh")
            now = datetime.now(tz_local)
            samples = [
                ("Real Madrid","Barcelona",
                 "https://upload.wikimedia.org/wikipedia/en/5/56/Real_Madrid_CF.svg",
                 "https://upload.wikimedia.org/wikipedia/en/4/47/FC_Barcelona_%28crest%29.svg",
                 now + timedelta(days=1), 9, 0, tr(LANG_CODE,"ampm_pm"), True, "El Clásico",
                 "https://upload.wikimedia.org/wikipedia/commons/8/8f/Trophy_icon.png", "Round 1"),
                ("Al Hilal","Al Nassr",
                 "https://upload.wikimedia.org/wikipedia/en/f/f1/Al_Hilal_SFC_Logo.svg",
                 "https://upload.wikimedia.org/wikipedia/en/5/53/Al-Nassr_logo_2020.svg",
                 now + timedelta(days=3), 9, 0, tr(LANG_CODE,"ampm_pm"), False, "Saudi Derby",
                 "https://upload.wikimedia.org/wikipedia/commons/8/8f/Trophy_icon.png", "Round 2"),
            ]
            cols = ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"]
            m = load_csv(MATCHES_FILE, cols)
            for A,B,Au,Bu,dt_,hr,mi,ap,big,occ,occlogo,rnd in samples:
                is_pm = (ap in ["PM","مساء"])
                hr24 = (0 if hr==12 else int(hr)) + (12 if is_pm else 0)
                ko = datetime(dt_.year, dt_.month, dt_.day, hr24, int(mi), tzinfo=tz_local)
                A_logo = cache_logo_from_url(Au) or Au
                B_logo = cache_logo_from_url(Bu) or Bu
                occ_logo = cache_logo_from_url(occlogo) or occlogo
                save_team_logo(A, A_logo); save_team_logo(B, B_logo)
                row = pd.DataFrame([{
                    "Match": f"{A} vs {B}",
                    "Kickoff": ko.isoformat(),
                    "Result": None,
                    "HomeLogo": A_logo,
                    "AwayLogo": B_logo,
                    "BigGame": big,
                    "RealWinner": "",
                    "Occasion": occ,
                    "OccasionLogo": occ_logo,
                    "Round": rnd,
                }])
                m = pd.concat([m, row], ignore_index=True)
            save_csv(m, MATCHES_FILE)
            st.success(tr(LANG_CODE,"test_done"))

    st.markdown("---")
    # Add match (with live logo previews)
    st.markdown(f"### {tr(LANG_CODE,'add_match')}")
    colA, colB = st.columns(2)
    with colA:
        teamA = st.text_input(tr(LANG_CODE,"team_a"), key="add_team_a")
        urlA  = st.text_input(tr(LANG_CODE,"home_logo_url"), value=get_saved_logo(teamA) or "", key="add_url_a")
        upA   = st.file_uploader(tr(LANG_CODE,"home_logo_upload"), type=["png","jpg","jpeg","webp","gif","bmp"], key="add_up_a")
        st.caption("Preview")
        if upA is not None:
            st.image(upA, width=56)
        else:
            show_logo_safe(urlA or get_saved_logo(teamA), width=56, caption=teamA or " ")

    with colB:
        teamB = st.text_input(tr(LANG_CODE,"team_b"), key="add_team_b")
        urlB  = st.text_input(tr(LANG_CODE,"away_logo_url"), value=get_saved_logo(teamB) or "", key="add_url_b")
        upB   = st.file_uploader(tr(LANG_CODE,"away_logo_upload"), type=["png","jpg","jpeg","webp","gif","bmp"], key="add_up_b")
        st.caption("Preview")
        if upB is not None:
            st.image(upB, width=56)
        else:
            show_logo_safe(urlB or get_saved_logo(teamB), width=56, caption=teamB or " ")

    colO1, colO2 = st.columns(2)
    with colO1:
        occ = st.text_input(tr(LANG_CODE,"occasion"), key="add_occasion")
        occ_url = st.text_input(tr(LANG_CODE,"occasion_logo_url"), key="add_occ_url")
        occ_up  = st.file_uploader(tr(LANG_CODE,"occasion_logo_upload"), type=["png","jpg","jpeg","webp","gif","bmp"], key="add_occ_up")
        st.caption("Preview")
        if occ_up is not None:
            st.image(occ_up, width=56)
        else:
            show_logo_safe(occ_url, width=56, caption=occ or " ")
    with colO2:
        rnd = st.text_input(tr(LANG_CODE,"round"), key="add_round")

    colD1, colD2, colD3, colD4, colD5 = st.columns([1,1,1,1,1])
    with colD1:
        tz_local = ZoneInfo("Asia/Riyadh")
        date_val = st.date_input(tr(LANG_CODE,"date_label"), value=datetime.now(tz_local).date(), key="add_date")
    with colD2:
        hour = st.number_input(tr(LANG_CODE,"hour"), min_value=1, max_value=12, value=9, key="add_hour")
    with colD3:
        minute = st.number_input(tr(LANG_CODE,"minute"), min_value=0, max_value=59, value=0, key="add_minute")
    with colD4:
        am_label = tr(LANG_CODE,"ampm_am"); pm_label = tr(LANG_CODE,"ampm_pm")
        ampm = st.selectbox(tr(LANG_CODE,"ampm"), [am_label, pm_label], key="add_ampm")
    with colD5:
        big = st.checkbox(tr(LANG_CODE,"big_game"), key="add_big")

    if st.button(tr(LANG_CODE,"btn_add_match"), key="btn_add_match"):
        if not teamA or not teamB:
            st.error(tr(LANG_CODE, "enter_both_teams"))
        else:
            is_pm = (ampm in ["PM","مساء"])
            hour24 = (0 if hour == 12 else int(hour)) + (12 if is_pm else 0)
            ko = datetime.combine(date_val, dtime(hour24, int(minute))).replace(tzinfo=tz_local)

            home_logo = None; away_logo = None; occ_logo_final = None
            if upA is not None: home_logo = save_uploaded_logo(upA, f"{teamA}_home")
            elif str(urlA).strip():  home_logo = cache_logo_from_url(str(urlA).strip()) or str(urlA).strip()
            elif get_saved_logo(teamA): home_logo = get_saved_logo(teamA)

            if upB is not None: away_logo = save_uploaded_logo(upB, f"{teamB}_away")
            elif str(urlB).strip():  away_logo = cache_logo_from_url(str(urlB).strip()) or str(urlB).strip()
            elif get_saved_logo(teamB): away_logo = get_saved_logo(teamB)

            if occ_up is not None: occ_logo_final = save_uploaded_logo(occ_up, f"{occ}_occasion")
            elif str(occ_url or "").strip(): occ_logo_final = cache_logo_from_url(str(occ_url).strip()) or str(occ_url).strip()

            if teamA and home_logo: save_team_logo(teamA, home_logo)
            if teamB and away_logo: save_team_logo(teamB, away_logo)

            m = load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
            row = pd.DataFrame([{
                "Match": f"{teamA} vs {teamB}",
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
            st.success(tr(LANG_CODE,"match_added"))

    st.markdown("---")
    # Edit matches (open)
    st.markdown(f"### {tr(LANG_CODE,'edit_matches')}")
    mdf = load_csv(MATCHES_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round"])
    if mdf.empty:
        st.info(tr(LANG_CODE,"no_matches"))
    else:
        mdf["KO"] = mdf["Kickoff"].apply(parse_iso_dt)
        mdf = mdf.sort_values("KO").reset_index(drop=True)
        for idx, row in mdf.iterrows():
            st.markdown("---")
            team_a, team_b = split_match_name(row["Match"])
            st.markdown(f"**{row['Match']}**  \n{tr(LANG_CODE,'kickoff')}: {format_dt_ampm(row['KO'], tz, LANG_CODE)}")

            c1, c2, c3 = st.columns(3)
            with c1:
                new_team_a = st.text_input(tr(LANG_CODE,"team_a"), value=team_a, key=f"edit_team_a_{idx}")
                new_url_a  = st.text_input(tr(LANG_CODE,"home_logo_url"), value=str(row.get("HomeLogo") or ""), key=f"edit_url_a_{idx}")
                st.caption("Preview")
                show_logo_safe(new_url_a or get_saved_logo(new_team_a), width=56, caption=new_team_a or " ")
            with c2:
                new_occ = st.text_input(tr(LANG_CODE,"occasion"), value=str(row.get("Occasion") or ""), key=f"edit_occ_{idx}")
                new_occ_url  = st.text_input(tr(LANG_CODE,"occasion_logo_url"), value=str(row.get("OccasionLogo") or ""), key=f"edit_occ_url_{idx}")
                st.caption("Preview")
                show_logo_safe(new_occ_url, width=56, caption=new_occ or " ")
            with c3:
                new_team_b = st.text_input(tr(LANG_CODE,"team_b"), value=team_b, key=f"edit_team_b_{idx}")
                new_url_b  = st.text_input(tr(LANG_CODE,"away_logo_url"), value=str(row.get("AwayLogo") or ""), key=f"edit_url_b_{idx}")
                st.caption("Preview")
                show_logo_safe(new_url_b or get_saved_logo(new_team_b), width=56, caption=new_team_b or " ")

            rcol = st.columns(3)
            with rcol[0]:
                new_round = st.text_input(tr(LANG_CODE,"round"), value=str(row.get("Round") or ""), key=f"edit_round_{idx}")
            with rcol[1]:
                local_ko = to_tz(row["KO"], tz) if row["KO"] else None
                use_date = local_ko.date() if local_ko else datetime.now(tz).date()
                nd = st.date_input(tr(LANG_CODE,"date_label"), value=use_date, key=f"edit_date_{idx}")
            with rcol[2]:
                local_ko = to_tz(row["KO"], tz) if row["KO"] else None
                hr12 = (local_ko.hour % 12) or 12 if local_ko else 9
                minutes = local_ko.minute if local_ko else 0
                ap = tr(LANG_CODE,"ampm_pm") if (local_ko and local_ko.hour>=12) else tr(LANG_CODE,"ampm_am")
                nh = st.number_input(tr(LANG_CODE,"hour"), min_value=1, max_value=12, value=hr12, key=f"edit_hour_{idx}")
                nm = st.number_input(tr(LANG_CODE,"minute"), min_value=0, max_value=59, value=minutes, key=f"edit_min_{idx}")
                nap = st.selectbox(tr(LANG_CODE,"ampm"), [tr(LANG_CODE,"ampm_am"), tr(LANG_CODE,"ampm_pm")], index=0 if ap==tr(LANG_CODE,"ampm_am") else 1, key=f"edit_ampm_{idx}")

            big_val = st.checkbox(tr(LANG_CODE,"big_game"), value=bool(row.get("BigGame", False)), key=f"edit_big_{idx}")

            e1, e2 = st.columns([1,1])
            with e1:
                res = st.text_input(tr(LANG_CODE,"final_score"), value=str(row.get("Result") or ""), key=f"edit_res_{idx}")
            with e2:
                opts = [new_team_a, new_team_b, tr(LANG_CODE,"draw")]
                curw = row.get("RealWinner") or tr(LANG_CODE,"draw")
                if isinstance(row.get("Result"), str) and "-" in str(row.get("Result")):
                    ra, rb = map(int, str(row.get("Result")).split("-"))
                    curw = tr(LANG_CODE,"draw") if ra == rb else (new_team_a if ra > rb else new_team_b)
                realw = st.selectbox(tr(LANG_CODE,"real_winner"),
                                     options=opts, index=opts.index(curw) if curw in opts else len(opts)-1,
                                     key=f"edit_realw_{idx}")

            col_actions1, col_actions2, col_actions3 = st.columns([1,1,1])

            with col_actions1:
                if st.button(tr(LANG_CODE,"save") + " (Details)", key=f"btn_save_details_{idx}"):
                    ispm = (nap in ["PM","مساء"])
                    hr24 = (0 if int(nh)==12 else int(nh)) + (12 if ispm else 0)
                    new_ko = datetime(nd.year, nd.month, nd.day, hr24, int(nm), tzinfo=tz)

                    final_logo_a = cache_logo_from_url(new_url_a) or (str(new_url_a).strip() if str(new_url_a).strip() else None)
                    final_logo_b = cache_logo_from_url(new_url_b) or (str(new_url_b).strip() if str(new_url_b).strip() else None)
                    final_occ_logo = cache_logo_from_url(new_occ_url) or (str(new_occ_url).strip() if str(new_occ_url).strip() else None)

                    if new_team_a and final_logo_a: save_team_logo(new_team_a, final_logo_a)
                    if new_team_b and final_logo_b: save_team_logo(new_team_b, final_logo_b)

                    new_match_name = f"{new_team_a} vs {new_team_b}"
                    mdf.loc[mdf["Match"] == row["Match"], ["Match","Kickoff","HomeLogo","AwayLogo","BigGame","Occasion","OccasionLogo","Round"]] = [
                        new_match_name, new_ko.isoformat(), final_logo_a, final_logo_b, bool(big_val),
                        new_occ or "", final_occ_logo, new_round or ""
                    ]
                    save_csv(mdf, MATCHES_FILE)
                    st.success(tr(LANG_CODE,"updated"))
                    st.rerun()

            with col_actions2:
                if st.button(tr(LANG_CODE,"save") + " (Score)", key=f"btn_save_score_{idx}"):
                    val = normalize_digits(res or "")
                    if val and not re.fullmatch(r"\d{1,2}-\d{1,2}", val):
                        st.error(tr(LANG_CODE,"fmt_error"))
                    else:
                        mdf.loc[mdf["Match"] == row["Match"], ["Result","RealWinner"]] = [(val if val else None), (realw or "")]
                        save_csv(mdf, MATCHES_FILE)
                        preds_now = load_csv(PREDICTIONS_FILE, ["User","Match","Prediction","Winner","SubmittedAt"])
                        recompute_leaderboard(preds_now)
                        if val:
                            hist = load_csv(MATCH_HISTORY_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"])
                            hist = ensure_history_schema(hist)
                            current_row = mdf[mdf["Match"] == row["Match"]].copy()
                            current_row["CompletedAt"] = datetime.now(ZoneInfo("UTC")).isoformat()
                            hist = pd.concat([hist, current_row], ignore_index=True)
                            save_csv(hist, MATCH_HISTORY_FILE)
                            mdf = mdf[mdf["Match"] != row["Match"]]
                            save_csv(mdf, MATCHES_FILE)

                        st.success(tr(LANG_CODE,"updated"))
                        st.rerun()

            with col_actions3:
                if st.button(tr(LANG_CODE,"delete"), key=f"btn_del_{idx}"):
                    mdf = mdf[mdf["Match"] != row["Match"]]
                    save_csv(mdf, MATCHES_FILE)
                    if os.path.exists(PREDICTIONS_FILE):
                        p = pd.read_csv(PREDICTIONS_FILE)
                        p = p[p["Match"] != row["Match"]]
                        save_csv(p, PREDICTIONS_FILE)
                    st.success(tr(LANG_CODE,"deleted"))
                    st.rerun()

    st.markdown("---")
    # Match History (Admin only)
    st.markdown(f"### {tr(LANG_CODE,'match_history')}")
    hist = load_csv(MATCH_HISTORY_FILE, ["Match","Kickoff","Result","HomeLogo","AwayLogo","BigGame","RealWinner","Occasion","OccasionLogo","Round","CompletedAt"])
    hist = ensure_history_schema(hist)
    if hist.empty:
        st.info(tr(LANG_CODE,"no_matches"))
    else:
        tz_local = ZoneInfo("Asia/Riyadh")
        view = hist.copy()
        view["Kickoff"] = view["Kickoff"].apply(parse_iso_dt)
        view["CompletedAt"] = pd.to_datetime(view["CompletedAt"], errors="coerce")
        view = view.sort_values("CompletedAt", ascending=False)
        view["Kickoff"] = view["Kickoff"].apply(lambda x: format_dt_ampm(x, tz_local, LANG_CODE))
        view["CompletedAt"] = view["CompletedAt"].dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(view[["Match","Kickoff","Result","RealWinner","Occasion","Round","CompletedAt"]], use_container_width=True)

    st.markdown("---")
    # Registered Users + Terminate + Delete
    st.markdown(f"### {tr(LANG_CODE,'registered_users')}")
    users_df = load_users()
    if users_df.empty:
        st.info("No users yet." if LANG_CODE=="en" else "لا يوجد مستخدمون بعد.")
    else:
        show = users_df.copy().sort_values("CreatedAt")
        show = show.rename(columns={
            "Name": tr(LANG_CODE,"lb_user"),
            "CreatedAt": "CreatedAt",
            "IsBanned": "Banned"
        })
        st.dataframe(show[[tr(LANG_CODE,"lb_user"), "CreatedAt", "Banned"]], use_container_width=True)

        st.markdown(" ")
        colu1, colu2 = st.columns([2,1])
        with colu1:
            target_name = st.selectbox(
                "Select user to terminate" if LANG_CODE=="en" else "اختر مستخدمًا لإيقافه",
                options=show[tr(LANG_CODE,"lb_user")].tolist(),
                key="terminate_name"
            )
        with colu2:
            if st.button(tr(LANG_CODE,"terminate"), key="btn_terminate"):
                users_df = load_users()
                hit = users_df[users_df["Name"].astype(str).str.strip().str.casefold() == str(target_name).strip().casefold()]
                if hit.empty:
                    st.error("User not found." if LANG_CODE=="en" else "المستخدم غير موجود.")
                else:
                    users_df.loc[users_df["Name"].astype(str).str.strip().str.casefold() == str(target_name).strip().casefold(), "IsBanned"] = 1
                    save_users(users_df)
                    st.success(tr(LANG_CODE,"terminated"))

        # Hard delete user (kept)
        st.markdown(" ")
        del_col1, del_col2 = st.columns([2,1])
        with del_col1:
            st.caption(" ")
        with del_col2:
            del_label = "Delete user" if LANG_CODE == "en" else "حذف المستخدم"
            if st.button(del_label, key="btn_delete_user"):
                users_df = load_users()
                mask = users_df["Name"].astype(str).str.strip().str.casefold() != str(target_name).strip().casefold()
                if mask.all():
                    st.error("User not found." if LANG_CODE=="en" else "المستخدم غير موجود.")
                else:
                    users_df = users_df[mask]
                    save_users(users_df)
                    st.success("User deleted." if LANG_CODE=="en" else "تم حذف المستخدم.")
                    st.rerun()
# ─────────────────────────────
# Router & bootstrap
# ─────────────────────────────
def run_app():
    st.sidebar.subheader(tr('en','sidebar_lang') + " / " + tr('ar','sidebar_lang'))
    lang_choice = st.sidebar.radio("", [tr('en','lang_en'), tr('ar','lang_ar')], index=0, horizontal=True)
    LANG_CODE = 'ar' if lang_choice == tr('ar','lang_ar') else 'en'

    st.sidebar.subheader(tr(LANG_CODE,'sidebar_time'))

    # (NEW) Auto-detect browser TZ + allow override, persist in URL
    _setup_browser_timezone_param()
    detected_tz = _get_tz_from_query_params(default_tz="Asia/Riyadh")

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
        tr(LANG_CODE,'app_timezone'),
        [label_auto] + common_tz,
        index=0
    )
    tz_str = detected_tz if tz_choice == label_auto else tz_choice

    try:
        st.experimental_set_query_params(tz=tz_str)
    except Exception:
        pass

    tz = ZoneInfo(tz_str)

    if st.sidebar.button("Logout" if LANG_CODE=="en" else "تسجيل الخروج"):
        st.session_state.pop("role", None)
        st.session_state.pop("current_name", None)
        st.rerun()

    role = st.session_state.get("role")
    if role == "user":
        page_play_and_leaderboard(LANG_CODE, tz)
    elif role == "admin":
        page_admin(LANG_CODE, tz)
    else:
        page_login(LANG_CODE)

# Run
try:
    run_app()
except Exception as e:
    st.error("App crashed")
    st.exception(e)