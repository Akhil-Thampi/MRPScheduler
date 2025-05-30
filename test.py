import gspread
from gspread_dataframe import get_as_dataframe
import pandas as pd
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials
import streamlit as st
from functions import *
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

creds_dict = st.secrets["gcp_service_account"]
scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(creds)

sheet = gc.open('MyRoti').worksheet('Sheet1') 
df = get_as_dataframe(sheet)

#Function to display Individual Schedule Summary 
def emp_ind():
    st.subheader("Individual Employee Schedule") # Added a subheader for clarity

    # Get fresh data if updates have occurred or if no data is loaded yet
    if "sheet_updated" in st.session_state and st.session_state.sheet_updated or "current_test_df" not in st.session_state:
        try:
            sheet = gc.open(SHEET_NAME).worksheet(WORKSHEET_NAME) # Use constants if defined
            st.session_state.current_test_df = get_as_dataframe(sheet, evaluate_formulas=True) # evaluate_formulas might be useful
            if "sheet_updated" in st.session_state:
                st.session_state.sheet_updated = False  # Reset flag
        except Exception as e:
            st.error(f"Failed to load data for individual schedule in test.py: {e}")
            st.session_state.current_test_df = pd.DataFrame() # Ensure it's an empty df on error

    # Use the DataFrame from session state
    df_for_individual_view = st.session_state.get("current_test_df", pd.DataFrame())

    if df_for_individual_view.empty:
        st.warning("No data available to display individual schedules.")
        return

    if 'Employee' not in df_for_individual_view.columns:
        st.error("Employee column missing in the sheet data.")
        return

    # Ensure employee names are strings and handle potential NaN values before creating selectbox options
    employee_options = sorted(list(set(df_for_individual_view["Employee"].astype(str).dropna().unique())))
    if not employee_options:
        st.info("No employees found in the data.")
        return

    selected_name = st.selectbox("Select Employee", employee_options, key="emp_ind_select")

    if selected_name:
        # Call the individual_schedule function (from functions.py)
        # It expects the full DataFrame
        individual_schedule(selected_name, df_for_individual_view.copy()) # Pass a copy
    else:
        st.info("Select an employee to see their schedule.")


# Function to display the Current Week Schedule as per last updated Google Sheet
def schedule_summary():
    st.title("Current Week Schedule")
    

    # Force re-fetch if sheet_updated flag is set
    if "sheet_updated" in st.session_state and st.session_state.sheet_updated:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)

        sheet = gc.open('MyRoti').worksheet('Sheet1')
        df = get_as_dataframe(sheet)
        st.session_state.sheet_updated = False  # reset flag
    else:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        sheet = gc.open('MyRoti').worksheet('Sheet1')
        df = get_as_dataframe(sheet)

    # Show schedule summary as tabular column
    gb = GridOptionsBuilder.from_dataframe(df)
    for col in df.columns:
        gb.configure_column(col, editable=False)

    grid_options = gb.build()
    gb.configure_default_column(width=110)
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        editable=True,
        height=300
    )

    return pd.DataFrame(grid_response['data'])
