import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

# --- Constants ---
SHEET_NAME = "MyRoti"
WORKSHEET_NAME = "Sheet1"



def schedule_summary():
    st.title("Current Week Schedule")

    if "reload_needed" in st.session_state and st.session_state.reload_needed or "current_summary_df" not in st.session_state:
        try:
            client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
            sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
            df = get_as_dataframe(sheet)
            st.session_state.current_summary_df = df
        except Exception as e:
            st.error(f"Failed to load data: {e}")
        st.session_state.reload_needed = False

    df = st.session_state.get("current_summary_df", pd.DataFrame())
    if df.empty:
        st.warning("No schedule data available.")
        return

    gb = GridOptionsBuilder.from_dataframe(df)
    for col in df.columns:
        gb.configure_column(col, width = 80,editable=False)
    grid_options = gb.build()
    AgGrid(df, gridOptions=grid_options, height=300)

def individual_schedule(name, df_full_schedule):
    if df_full_schedule.empty:
        st.warning(f"Full schedule data is empty. Cannot display schedule for {name}.")
        return
    employee_row = df_full_schedule[df_full_schedule['Employee'] == name]
    if employee_row.empty:
        st.warning(f"No schedule data found for {name}")
        return
    week_data = employee_row.drop(columns='Employee').squeeze()
    week_df = pd.DataFrame(week_data).reset_index()
    week_df.columns = ['Weekday', 'Task']
    AgGrid(week_df, height=300)
    
    
def emp_ind():
    st.subheader("Individual Employee Schedule")
    
    if "reload_needed" in st.session_state and st.session_state.reload_needed or "current_test_df" not in st.session_state:
        try:
            client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
            sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
            df = get_as_dataframe(sheet)
            st.session_state.current_test_df = df
        except Exception as e:
            st.error(f"Failed to load data: {e}")
        st.session_state.reload_needed = False

    df = st.session_state.get("current_test_df", pd.DataFrame())
    if df.empty:
        st.warning("No data available for individual schedules.")
        return

    employee_options = sorted(df["Employee"].astype(str).dropna().unique())
    if not employee_options:
        st.info("No employees found in the data.")
        return

    selected_name = st.selectbox("Select Employee", employee_options, key="emp_ind_select")
    if selected_name:
        individual_schedule(selected_name, df.copy())