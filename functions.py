import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# --- Constants ---
SHEET_NAME = "MyRoti"
WORKSHEET_NAME = "Sheet1"
DEFAULT_TASK_FOR_NEW_EMPLOYEE = "Off"

# --- Helper Functions ---
def get_gspread_client():
    """Initializes and returns the gspread client."""
    scopes = ['https://www.googleapis.com/auth/spreadsheets',  'https://www.googleapis.com/auth/drive'] 
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_google_sheet_object_and_data(client, sheet_name, worksheet_name):
    """Opens a specific worksheet and returns its object and all its data."""
    try:
        sheet = client.open(sheet_name).worksheet(worksheet_name)
        data = sheet.get_all_values()
        return sheet, data
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet '{sheet_name}' not found.")
        return None, []
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet_name}' in '{sheet_name}' not found.")
        return None, []
    except Exception as e:
        st.error(f"An error occurred while accessing Google Sheet: {e}")
        return None, []

# --- Week Logic ---
def get_week_range(offset=0):
    today = datetime.today() + timedelta(weeks=offset)
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start.date(), end.date()

def display_week_selector():
    week_offset = st.session_state.get("week_offset", 0)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous Week"):
            st.session_state["week_offset"] = week_offset - 1
            st.rerun()
    with col3:
        if st.button("Next Week ➡️"):
            st.session_state["week_offset"] = week_offset + 1
            st.rerun()
    start_date, end_date = get_week_range(st.session_state.get("week_offset", 0))
    with col2:
        st.markdown(f"### 📅 {start_date} to {end_date}")
    return f"{start_date} to {end_date}"

# --- Table Display ---
def display_editable_table(data, dropdown_values):
    if not data or len(data) < 1:
        st.warning("No data to display in the table. Add employees or check sheet.")
        return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    gb = GridOptionsBuilder.from_dataframe(df)
    for col in df.columns:
        gb.configure_column(col, editable=True, cellEditor='agSelectCellEditor',width = 80,
                            cellEditorParams={'values': dropdown_values})
    grid_options = gb.build()
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        editable=True,
        width = 80,
        height=300
    )
    return pd.DataFrame(grid_response['data'])

# --- Google Sheet Updates ---
def confirm_and_update_workflow(df_updated, sheet_object):
    if sheet_object is None:
        st.error("Cannot update: Google Sheet object is not available.")
        return
    if st.button("Update Schedule to Google Sheet"):
        try:
            sheet_object.update([df_updated.columns.values.tolist()] + df_updated.values.tolist())
            st.success("✅ Schedule updated successfully in Google Sheet!")
            st.session_state.reload_needed = True
            st.rerun()
        except Exception as e:
            st.error(f"Failed to update Google Sheet: {e}")

# --- Employee Management ---
def add_employee_to_sheet(sheet_object, employee_name):
    try:
        header = sheet_object.row_values(1)
        existing_employees = [row[0].strip().lower() for row in sheet_object.get_all_values()[1:]]
        if employee_name.strip().lower() in existing_employees:
            st.warning(f"Employee '{employee_name}' already exists.")
            return False
        new_row = [employee_name.strip()] + [DEFAULT_TASK_FOR_NEW_EMPLOYEE] * (len(header) - 1)
        sheet_object.append_row(new_row)
        st.success(f"Employee '{employee_name}' added successfully.")
        return True
    except Exception as e:
        st.error(f"Failed to add employee: {e}")
        return False

def remove_employee_from_sheet(sheet_object, employee_name):
    try:
        rows_to_delete = [i + 1 for i, row in enumerate(sheet_object.get_all_values()) 
                          if row and row[0].strip().lower() == employee_name.strip().lower()]
        if not rows_to_delete:
            st.warning(f"Employee '{employee_name}' not found.")
            return False
        for row_index in sorted(rows_to_delete, reverse=True):
            sheet_object.delete_rows(row_index)
        st.success(f"Employee '{employee_name}' removed successfully.")
        return True
    except Exception as e:
        st.error(f"Failed to remove employee: {e}")
        return False

# --- Schedule Page Logic ---
def schedule_page():
    st.title("📆 Weekly Scheduler & Employee Management")
    client = get_gspread_client()
    if not client:
        st.error("Failed to connect to Google Sheets. Please check credentials.")
        return

    sheet, data = get_google_sheet_object_and_data(client, SHEET_NAME, WORKSHEET_NAME)
    if not sheet:
        return

    # --- Employee Management Section ---
    st.subheader("Manage Employees")
    employee_names = [row[0] for row in data[1:]] if data and len(data) > 1 else []
    
    col_add, col_remove = st.columns(2)
    with col_add:
        st.markdown("#### Add New Employee")
        new_employee_name = st.text_input("Enter New Employee Name", key="new_emp_name").strip()
        if st.button("Add Employee"):
            if new_employee_name:
                if add_employee_to_sheet(sheet, new_employee_name):
                    st.session_state.reload_needed = True
                    st.rerun()
            else:
                st.warning("Please enter an employee name.")

    with col_remove:
        st.markdown("#### Remove Employee")
        if employee_names:
            employee_to_remove = st.selectbox(
                "Select Employee to Remove", options=sorted(set(employee_names)), key="remove_emp_select"
            )
            if st.button("Remove Selected Employee", type="primary"):
                if employee_to_remove:
                    if remove_employee_from_sheet(sheet, employee_to_remove):
                        st.session_state.reload_needed = True
                        st.rerun()
        else:
            st.info("No employees to remove.")

    st.divider()

    # --- Weekly Scheduler ---
    st.subheader("Weekly Schedule")
    display_week_selector()
    if data:
        dropdown_options = ["List", "Drive", "List/Drive", "Off"]
        df_updated = display_editable_table(data, dropdown_options)
        if not df_updated.empty:
            confirm_and_update_workflow(df_updated, sheet)