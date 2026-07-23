import html
from datetime import datetime

import requests
import streamlit as st

try:
    from streamlit_qrcode_scanner import qrcode_scanner
except ModuleNotFoundError:
    st.set_page_config(page_title="GX Sports Marshal Scanner", page_icon="✅")
    st.error(
        "The QR scanner component is not installed. Confirm that requirements.txt "
        "is in the same repository folder as app.py, then reboot the Streamlit app."
    )
    st.stop()


st.set_page_config(
    page_title="GX Sports Marshal Scanner",
    page_icon="✅",
    layout="centered",
)

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background:
          linear-gradient(130deg, rgba(181,18,27,.96), rgba(86,7,19,.94) 44%, rgba(7,31,66,.98)),
          repeating-linear-gradient(110deg, transparent 0 46px, rgba(255,255,255,.08) 47px 49px);
        background-attachment: fixed;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMainBlockContainer"] {
        max-width: 620px;
        margin: 18px auto;
        padding: 24px !important;
        border: 1px solid rgba(255,255,255,.45);
        border-radius: 22px;
        background: rgba(255,255,255,.98);
        box-shadow: 0 25px 65px rgba(7,31,66,.30);
    }
    .gx-header {
        margin: -24px -24px 22px;
        padding: 22px 24px;
        border-radius: 22px 22px 0 0;
        color: white;
        background: linear-gradient(110deg, #071f42, #0a3970);
    }
    .gx-brand { font-size: 15px; font-weight: 900; letter-spacing: .12em; }
    .gx-title { margin-top: 7px; font-size: 31px; font-weight: 1000; letter-spacing: -.04em; text-transform: uppercase; }
    .gx-subtitle { margin-top: 5px; color: rgba(255,255,255,.70); font-size: 13px; }
    .online-pill {
        display: inline-block;
        margin-top: 13px;
        padding: 6px 10px;
        border: 1px solid rgba(255,255,255,.34);
        border-radius: 999px;
        font-size: 11px;
        font-weight: 900;
    }
    .online-pill.online::before, .online-pill.offline::before {
        content: "";
        display: inline-block;
        width: 8px;
        height: 8px;
        margin-right: 7px;
        border-radius: 50%;
        vertical-align: 0;
    }
    .online-pill.online::before { background: #31d17c; }
    .online-pill.offline::before { background: #ff6b6b; }
    .scan-instruction { margin: 0 0 12px; color: #667085; text-align: center; }
    .result-title {
        padding: 16px;
        border-radius: 13px;
        color: white;
        font-size: 26px;
        font-weight: 1000;
        text-align: center;
        text-transform: uppercase;
    }
    .result-title.approved { background: #16824f; }
    .result-title.duplicate { background: #a66508; }
    .result-title.invalid, .result-title.error { background: #b5121b; }
    .participant-name { margin: 14px 0 4px; color: #071f42; font-size: 24px; font-weight: 900; text-align: center; }
    .participant-id { margin-bottom: 16px; color: #667085; font-weight: 800; text-align: center; overflow-wrap: anywhere; }
    .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px 16px;
        margin: 16px 0;
        padding: 16px;
        border: 1px solid #d8dde6;
        border-radius: 13px;
        background: #f7f8fb;
    }
    .detail-grid span { color: #667085; font-size: 12px; }
    .detail-grid strong { display: block; margin-top: 2px; color: #101828; font-size: 13px; overflow-wrap: anywhere; }
    .history {
        margin-top: 20px;
        border-top: 1px solid #e4e7ec;
        padding-top: 14px;
    }
    .history-row {
        display: grid;
        grid-template-columns: 72px 1fr auto;
        gap: 8px;
        padding: 9px 0;
        border-bottom: 1px solid #edf0f4;
        font-size: 12px;
        align-items: center;
    }
    .history-result { font-weight: 900; color: #071f42; }
    #MainMenu, footer { visibility: hidden; }
    @media (max-width: 480px) {
        [data-testid="stMainBlockContainer"] { margin: 8px; padding: 18px !important; }
        .gx-header { margin: -18px -18px 18px; }
        .detail-grid { grid-template-columns: 1fr; }
        .history-row { grid-template-columns: 62px 1fr; }
        .history-result { grid-column: 2; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_secret(name):
    try:
        value = str(st.secrets[name]).strip()
    except (KeyError, FileNotFoundError):
        return ""
    return value


GAS_URL = load_secret("GAS_URL")
SCANNER_API_KEY = load_secret("SCANNER_API_KEY")

if not GAS_URL or not SCANNER_API_KEY:
    st.markdown(
        """
        <div class="gx-header">
          <div class="gx-brand">GX SPORTS PREVIEW GAMES</div>
          <div class="gx-title">Marshal Scanner</div>
          <div class="gx-subtitle">Configuration required</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.error(
        "Scanner configuration is incomplete. Add GAS_URL and "
        "SCANNER_API_KEY to Streamlit Secrets."
    )
    st.stop()


if "view" not in st.session_state:
    st.session_state.view = "READY"
if "result" not in st.session_state:
    st.session_state.result = {}
if "history" not in st.session_state:
    st.session_state.history = []
if "scan_cycle" not in st.session_state:
    st.session_state.scan_cycle = 0
if "last_request" not in st.session_state:
    st.session_state.last_request = None


def scanner_request(action, **values):
    payload = {
        "action": action,
        "apiKey": SCANNER_API_KEY,
    }
    payload.update(values)
    response = requests.post(GAS_URL, data=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def health_is_online():
    try:
        response = scanner_request("GX_SCANNER_HEALTH")
        return response.get("status") == "ONLINE"
    except (requests.RequestException, ValueError):
        return False


def submit_checkin(code, lookup_type):
    st.session_state.last_request = {
        "code": code,
        "lookupType": lookup_type,
    }
    try:
        response = scanner_request(
            "GX_SCANNER_CHECKIN",
            code=code,
            lookupType=lookup_type,
        )
    except (requests.RequestException, ValueError):
        response = {
            "status": "CONNECTION_ERROR",
            "message": (
                "Unable to connect to the registration database. "
                "No check-in was recorded."
            ),
        }

    st.session_state.result = response
    st.session_state.view = "RESULT"
    if response.get("status") in {
        "CHECKED_IN",
        "ALREADY_CHECKED_IN",
        "INVALID_QR",
    }:
        add_history(response)


def add_history(response):
    status = response.get("status", "")
    labels = {
        "CHECKED_IN": "CHECKED IN",
        "ALREADY_CHECKED_IN": "ALREADY CHECKED IN",
        "INVALID_QR": "INVALID",
    }
    st.session_state.history.insert(
        0,
        {
            "time": datetime.now().strftime("%I:%M %p"),
            "name": response.get("fullName") or "Unknown participant",
            "result": labels.get(status, status),
        },
    )
    st.session_state.history = st.session_state.history[:6]


def reset_scanner():
    st.session_state.view = "READY"
    st.session_state.result = {}
    st.session_state.last_request = None
    st.session_state.scan_cycle += 1
    st.rerun()


def render_header(online):
    status_class = "online" if online else "offline"
    status_label = "ONLINE" if online else "OFFLINE"
    st.markdown(
        f"""
        <div class="gx-header">
          <div class="gx-brand">GX SPORTS PREVIEW GAMES</div>
          <div class="gx-title">Marshal Scanner</div>
          <div class="gx-subtitle">Main Entrance participant check-in</div>
          <div class="online-pill {status_class}">{status_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_history():
    if not st.session_state.history:
        return
    rows = []
    for item in st.session_state.history:
        rows.append(
            '<div class="history-row">'
            f"<span>{html.escape(item['time'])}</span>"
            f"<strong>{html.escape(item['name'])}</strong>"
            f"<span class=\"history-result\">{html.escape(item['result'])}</span>"
            "</div>"
        )
    st.markdown(
        '<div class="history"><strong>RECENT SCANS</strong>'
        + "".join(rows)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_participant_result(response, duplicate=False):
    css_class = "duplicate" if duplicate else "approved"
    title = "ALREADY CHECKED IN" if duplicate else "CHECK-IN APPROVED"
    st.markdown(
        f'<div class="result-title {css_class}">{title}</div>',
        unsafe_allow_html=True,
    )
    selfie = response.get("selfieDataUri")
    if selfie:
        left, center, right = st.columns([1, 1.15, 1])
        with center:
            st.image(selfie, use_container_width=True)
    st.markdown(
        f'<div class="participant-name">{html.escape(response.get("fullName", ""))}</div>'
        f'<div class="participant-id">{html.escape(response.get("registrationId", ""))}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="detail-grid">
          <div><span>Division</span><strong>{division}</strong></div>
          <div><span>Category</span><strong>{category}</strong></div>
          <div><span>Assigned Event Date</span><strong>{event_date}</strong></div>
          <div><span>Check-In Time</span><strong>{checkin_time}</strong></div>
        </div>
        """.format(
            division=html.escape(response.get("division", "")),
            category=html.escape(response.get("category", "")),
            event_date=html.escape(response.get("assignedEventDate", "")),
            checkin_time=html.escape(response.get("checkedInAt", "")),
        ),
        unsafe_allow_html=True,
    )
    if duplicate:
        st.warning(
            "Confirm the participant’s identity before taking further action."
        )
    if st.button("SCAN NEXT PARTICIPANT", type="primary", use_container_width=True):
        reset_scanner()


online = health_is_online()
render_header(online)

if st.session_state.view == "READY":
    if not online:
        st.markdown(
            '<div class="result-title error">CONNECTION ERROR</div>',
            unsafe_allow_html=True,
        )
        st.error(
            "Unable to connect to the registration database. "
            "No check-in was recorded."
        )
        if st.button("RETRY", type="primary", use_container_width=True):
            st.rerun()
        render_history()
        st.stop()

    st.markdown(
        '<p class="scan-instruction">Align the participant QR code inside the frame.</p>',
        unsafe_allow_html=True,
    )
    scanned_code = qrcode_scanner(
        key=f"gx_main_entrance_scanner_{st.session_state.scan_cycle}"
    )
    if scanned_code:
        with st.spinner("Verifying registration and recording check-in…"):
            submit_checkin(str(scanned_code).strip(), "QR")
        st.rerun()

    with st.expander("Manual Registration ID fallback"):
        with st.form("manual_registration_lookup", clear_on_submit=True):
            registration_id = st.text_input(
                "Registration ID",
                placeholder="GXPG2026-...",
                max_chars=80,
            )
            manual_submit = st.form_submit_button(
                "CHECK IN BY REGISTRATION ID",
                use_container_width=True,
            )
        if manual_submit:
            if not registration_id.strip():
                st.error("Enter the complete Registration ID.")
            else:
                with st.spinner("Verifying registration and recording check-in…"):
                    submit_checkin(
                        registration_id.strip(),
                        "REGISTRATION_ID",
                    )
                st.rerun()
    render_history()

else:
    response = st.session_state.result
    status = response.get("status")

    if status == "CHECKED_IN":
        render_participant_result(response)
    elif status == "ALREADY_CHECKED_IN":
        render_participant_result(response, duplicate=True)
    elif status == "INVALID_QR":
        st.markdown(
            '<div class="result-title invalid">INVALID QR CODE</div>',
            unsafe_allow_html=True,
        )
        st.error("The QR code is invalid or the registration could not be found.")
        if st.button("TRY AGAIN", type="primary", use_container_width=True):
            reset_scanner()
        if st.button(
            "MANUAL REGISTRATION ID SEARCH",
            use_container_width=True,
        ):
            reset_scanner()
    else:
        st.markdown(
            '<div class="result-title error">CONNECTION ERROR</div>',
            unsafe_allow_html=True,
        )
        st.error(
            response.get("message")
            or "Unable to connect to the registration database. "
            "No check-in was recorded."
        )
        if st.button("RETRY", type="primary", use_container_width=True):
            last_request = st.session_state.last_request
            if last_request:
                with st.spinner("Retrying check-in…"):
                    submit_checkin(
                        last_request["code"],
                        last_request["lookupType"],
                    )
                st.rerun()
            else:
                reset_scanner()
    render_history()
