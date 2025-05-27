
# ---------------------------------------------BoyzOnSync-------------------------------------------------------------------------------- #
# ----------------------------------------Created by: Akhil Thampi-----------------------------------------------------------------------------#

import streamlit as st
from functions import *
from user_login import *
from test import emp_ind, schedule_summary


# --- App Title ---
st.title("BoyzOnSync")

# --- Always visible: Public pages ---
schedule_summary()
emp_ind()

# --- Sidebar login ---
login()

# --- Only show Weekly Scheduler after login ---
if st.session_state.get("logged_in", False):
    schedule_page()
else:
    st.warning("🔒 Please log in to access the Weekly Scheduler.")

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
        Engineered for MyRotiPlace: Created by: AK96 💥
    </div>
    """,
    unsafe_allow_html=True
)
