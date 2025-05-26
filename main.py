import streamlit as st
from functions import *
from user_login import *
from test import emp_ind, schedule_summary

# --- App Title ---
st.title("MRPScheduler")

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
