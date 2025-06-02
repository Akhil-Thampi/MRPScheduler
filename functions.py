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
    # Initialize week_offset if not present
    if "week_offset" not in st.session_state:
        st.session_state["week_offset"] = 0

    week_offset = st.session_state["week_offset"]

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous Week", key="prev_week_selector_btn"): # Added unique key
            st.session_state["week_offset"] = week_offset - 1
            st.rerun()
    with col3:
        if st.button("Next Week ➡️", key="next_week_selector_btn"): # Added unique key
            st.session_state["week_offset"] = week_offset + 1
            st.rerun()

    start_date, end_date = get_week_range(st.session_state["week_offset"])
    # This current_display_range is what the user opens the scheduler
    current_display_range = f"{start_date} to {end_date}"
    with col2:
        st.markdown(f"### Current schedule for 📅 {current_display_range}")
    return current_display_range # Return the range currently being displayed in the selector

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
        height=300,
        key="weekly_schedule_grid" # Added unique key
    )
    return pd.DataFrame(grid_response['data'])

# --- Google Sheet Updates ---
# MODIFIED: Accepts current_displayed_week_range to store it
def confirm_and_update_workflow(df_updated, sheet_object, current_displayed_week_range):
    if sheet_object is None:
        st.error("Cannot update: Google Sheet object is not available.")
        return
    if st.button("Update Schedule to Google Sheet", key="update_schedule_btn"): # Added unique key
        try:
            if "DateRange" in df_updated.columns:
                df_updated["DateRange"] = current_displayed_week_range
            sheet_object.update([df_updated.columns.values.tolist()] + df_updated.values.tolist())
            st.success("✅ Schedule updated successfully in Google Sheet!")
            st.session_state.reload_needed = True
            # CRITICAL: Store the week range that was JUST updated
            st.session_state["last_updated_week_range"] = current_displayed_week_range
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

# --- Schedule Page---
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
        if st.button("Add Employee", key="add_employee_btn"): # Added unique key
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
            if st.button("Remove Selected Employee", type="primary", key="remove_employee_btn"): # Added unique key
                if employee_to_remove:
                    if remove_employee_from_sheet(sheet, employee_to_remove):
                        st.session_state.reload_needed = True
                        st.rerun()
        else:
            st.info("No employees to remove.")

    st.divider()

    # --- Weekly Scheduler ---
    st.subheader("Weekly Schedule")
    # Get the week range currently displayed by the selector
    current_displayed_week_range = display_week_selector()
    if data:
        dropdown_options = ["List", "Drive", "List/Drive", "Off"]
        df_updated = display_editable_table(data, dropdown_options)
        if not df_updated.empty:
            # Pass the current_displayed_week_range to the update function
            confirm_and_update_workflow(df_updated, sheet, current_displayed_week_range)

def get_last_updated_week_range(sheet):
    try:
        values = sheet.col_values(sheet.row_values(1).index("DateRange") + 1)
        if len(values) <= 1:
            return "No schedule updated yet."
        # Use the most recent non-header value (last non-empty)
        last_value = next((v for v in reversed(values[1:]) if v.strip()), "No schedule updated yet.")
        return last_value
    except Exception as e:
        st.error(f"Error fetching last week range: {e}")
        return "No schedule updated yet."

def schedule_summary():
    # Initialize last_updated_week_range to a default message if not present
    if "last_updated_week_range" not in st.session_state:
        try:
            client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
            sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
            st.session_state["last_updated_week_range"] = get_last_updated_week_range(sheet)
        except Exception as e:
            st.session_state["last_updated_week_range"] = "No schedule updated yet."
            st.error(f"Error initializing week range: {e}")


    # CRITICAL: Use the stored last_updated_week_range from session state for the title
    st.markdown(f"### Current Week Schedule ({st.session_state['last_updated_week_range']})")

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
    AgGrid(df, gridOptions=grid_options, height=300, key="summary_grid") # Added unique key

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
    AgGrid(week_df, height=300, key=f"individual_grid_{name}") # Added unique key


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
        individual_schedule(selected_name, df)