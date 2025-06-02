# ---------------------------------------------BoyzOnSync-------------------------------------------------------------------------------- #
# ----------------------------------------Created by: Akhil Thampi-----------------------------------------------------------------------------#

import streamlit as st
from functions import schedule_page,emp_ind, schedule_summary
from user_login import login

# --- App Title ---
st.title("BoyzOnSync")

# --- Initialize week_offset if not present (for the scheduler) ---
# last_updated_week_range will be set by schedule_summary function or confirm_and_update_workflow
if "week_offset" not in st.session_state:
    st.session_state["week_offset"] = 0

# --- Always visible: Public pages ---
schedule_summary()
emp_ind()


if "reload_needed" in st.session_state:
    del st.session_state.reload_needed

# --- Sidebar login ---
login()

# --- Only show Weekly Scheduler after login ---
if st.session_state.get("logged_in", False):
    schedule_page()
else:
    st.warning("🔒 Please log in to access the Weekly Scheduler.")

# --- Footer ---
st.markdown(
    """
    <style>
    .footer {
        position: sticky;
        bottom: 0;
        right: 0;
        padding: 10px 20px;
        font-size: 14px;
        color: #555;
        background-color: rgba(255, 255, 255, 0.9);
        border-top-left-radius: 10px;
        z-index: 9999;
    }
    </style>
    <div class="footer">
        Engineered for MyRotiBoyz: Created by: AK96 💥
    </div>
    """,
    unsafe_allow_html=True
)