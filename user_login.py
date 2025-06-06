import streamlit as st

# --- Credentials (from `st.secrets`) ---
USER_CREDENTIALS = st.secrets["login"]

def login():
    st.sidebar.title("🔐 Login")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.sidebar.success(f"Welcome, {username}!")
            else:
                st.sidebar.error("Invalid username or password.")
    else:
        st.sidebar.success(f"✅ Logged in as: {st.session_state.username}")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""