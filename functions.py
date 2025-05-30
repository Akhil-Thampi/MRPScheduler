import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
import streamlit as st
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import pandas as pd

# --- Constants ---
SHEET_NAME = "MyRoti"
WORKSHEET_NAME = "Sheet1"
DEFAULT_TASK_FOR_NEW_EMPLOYEE = "Off" # Default task for new employees for all days

# --- Helper function to get gspread client and sheet ---
def get_gspread_client():
    """Initializes and returns the gspread client."""
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

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

# Function to calculate week range
def get_week_range(offset=0):
    today = datetime.today() + timedelta(weeks=offset)
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start.date(), end.date()

# Function to create Week Selection button
def display_week_selector():
    week_offset = st.session_state.get("week_offset", 0)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous Week"):
            st.session_state["week_offset"] = week_offset - 1
            st.rerun() # Rerun to reflect week change
    with col3:
        if st.button("Next Week ➡️"):
            st.session_state["week_offset"] = week_offset + 1
            st.rerun() # Rerun to reflect week change

    start_date, end_date = get_week_range(st.session_state.get("week_offset", 0))
    with col2:
        st.markdown(f"### 📅 {start_date} to {end_date}")
    
    return f"{start_date} to {end_date}"


# Function to create tabular column from fetched Google Sheet
def display_editable_table(data, dropdown_values):
    if not data or len(data) < 1: # Check if data is empty or only has a header
        st.warning("No data to display in the table. Add employees or check sheet.")
        return pd.DataFrame() 

    # Assuming the first row in 'data' is headers
    df = pd.DataFrame(data[1:], columns=data[0])
    if df.empty and len(data) == 1: # Only headers, no data rows
        st.info("Sheet contains headers but no employee data.")
        return pd.DataFrame(columns=data[0]) # Return empty DF with columns

    gb = GridOptionsBuilder.from_dataframe(df)

    for col in df.columns:
        gb.configure_column(col, editable=True, cellEditor='agSelectCellEditor',
                            cellEditorParams={'values': dropdown_values})
    gb.configure_default_column(width=110) 
    grid_options = gb.build()
    grid_response = AgGrid(df, gridOptions=grid_options,
                        update_mode=GridUpdateMode.VALUE_CHANGED,
                        fit_columns_on_grid_load=True, 
                        editable=True,
                        height=300, 
                        allow_unsafe_jscode=True, 
                        key='schedule_grid' 
                        )

    return pd.DataFrame(grid_response['data'])


# Function to update changes to Google Sheet
def confirm_and_update_workflow(df_updated, sheet_object):
    if sheet_object is None:
        st.error("Cannot update: Google Sheet object is not available.")
        return

    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = True 

    if st.session_state.edit_mode:
        if st.button("Update Schedule to Google Sheet"):
            if df_updated.empty and list(df_updated.columns) == ['Employee']: # Handle case of empty df after all employees removed
                st.warning("No data to update. Add employees to the schedule.")
                # Optionally, clear the sheet if that's the desired behavior for an empty df
                # sheet_object.clear()
                # sheet_object.update([df_updated.columns.values.tolist()]) # Keep header
                return

            try:
                sheet_object.update([df_updated.columns.values.tolist()] + df_updated.values.tolist())
                st.success("✅ Schedule updated successfully in Google Sheet!")
                st.session_state.sheet_updated = True 
                st.rerun() 
            except Exception as e:
                st.error(f"Failed to update Google Sheet: {e}")


# --- NEW FUNCTIONS FOR ADDING/REMOVING EMPLOYEES ---
def add_employee_to_sheet(sheet_object, employee_name):
    """Adds a new employee to the Google Sheet with default schedule."""
    if not sheet_object:
        st.error("Cannot add employee: Google Sheet object not available.")
        return False
    try:
        header = sheet_object.row_values(1)
        if not header:
            # If sheet is completely empty, create a header first
            # This depends on what your expected columns are. For example:
            # default_headers = ["Employee", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            # sheet_object.append_row(default_headers)
            # header = default_headers
            # st.info("Sheet was empty. Created default headers. Please try adding employee again if needed.")
            # For now, assume header should exist if we are adding rows like this.
            st.error("Cannot add employee: Sheet header not found or sheet is empty. Please ensure 'Sheet1' has a header row.")
            return False

        existing_employees_data = sheet_object.col_values(1) # Get all values in the first column
        existing_employees = [emp.strip().lower() for emp in existing_employees_data[1:]] # Skip header, normalize

        if employee_name.strip().lower() in existing_employees:
            st.warning(f"Employee '{employee_name}' already exists.")
            return False

        new_row = [employee_name.strip()] + [DEFAULT_TASK_FOR_NEW_EMPLOYEE] * (len(header) - 1)
        sheet_object.append_row(new_row)
        st.success(f"Employee '{employee_name}' added successfully.")
        return True
    except Exception as e:
        st.error(f"Failed to add employee '{employee_name}': {e}")
        return False

def remove_employee_from_sheet(sheet_object, employee_name):
    """Removes an employee from the Google Sheet."""
    if not sheet_object:
        st.error("Cannot remove employee: Google Sheet object not available.")
        return False
    try:
        # Find all occurrences of the employee name in the first column (case-insensitive)
        employee_cells = sheet_object.findall(employee_name, in_column=1)
        
        # gspread's findall might not be strictly case-insensitive depending on backend.
        # A more robust way if many employees or strict matching needed:
        all_values = sheet_object.get_all_values()
        rows_to_delete_indices = []
        if all_values: # Ensure sheet is not empty
            for i, row in enumerate(all_values):
                if row and row[0].strip().lower() == employee_name.strip().lower(): # Check first cell, case-insensitive
                    rows_to_delete_indices.append(i + 1) # gspread rows are 1-indexed

        if not rows_to_delete_indices:
            st.warning(f"Employee '{employee_name}' not found.")
            return False

        # Delete rows in reverse order to avoid index shifting issues
        for row_index in sorted(rows_to_delete_indices, reverse=True):
            sheet_object.delete_rows(row_index)
        
        st.success(f"Employee '{employee_name}' removed successfully.")
        return True
        
    except Exception as e:
        st.error(f"Failed to remove employee '{employee_name}': {e}")
        return False

# --- Login function ---
USER_CREDENTIALS = st.secrets["login"] 

# Function to make Schedule page appear only after login
def schedule_page():
    st.title("📆 Weekly Scheduler & Employee Management")
    
    client = get_gspread_client()
    if not client:
        st.error("Failed to connect to Google Sheets. Please check credentials.")
        return

    # Fetch sheet object and current data at the beginning of each run (including reruns)
    sheet_object_for_ops, current_sheet_data = get_google_sheet_object_and_data(client, SHEET_NAME, WORKSHEET_NAME)

    if not sheet_object_for_ops:
        # Error already shown by get_google_sheet_object_and_data
        return

    # --- Employee Management Section ---
    st.subheader("Manage Employees")
    
    employee_names = []
    if current_sheet_data and len(current_sheet_data) > 1: # Data exists and has more than just a header
        employee_names = [row[0] for row in current_sheet_data[1:] if row] # Ensure row is not empty
    elif current_sheet_data and len(current_sheet_data) == 1 and current_sheet_data[0]: # Only header exists
        pass # employee_names remains empty
    elif not current_sheet_data: # Sheet is completely empty or couldn't be read
        st.warning("Could not read employee data from the sheet.")


    col_add, col_remove = st.columns(2)

    with col_add:
        st.markdown("#### Add New Employee")
        new_employee_name = st.text_input("Enter New Employee Name", key="new_emp_name").strip()
        if st.button("Add Employee"):
            if new_employee_name:
                if add_employee_to_sheet(sheet_object_for_ops, new_employee_name):
                    st.session_state.sheet_updated = True 
                    st.rerun() 
            else:
                st.warning("Please enter an employee name.")

    with col_remove:
        st.markdown("#### Remove Employee")
        if employee_names:
            employee_to_remove = st.selectbox("Select Employee to Remove", options=sorted(list(set(employee_names))), key="remove_emp_select")
            if st.button("Remove Selected Employee", type="primary"): 
                if employee_to_remove:
                    if remove_employee_from_sheet(sheet_object_for_ops, employee_to_remove):
                        st.session_state.sheet_updated = True 
                        st.rerun()
                else:
                    st.warning("No employee selected to remove.")
        else:
            st.info("No employees to remove or sheet is empty/header-only.")
            
    st.divider() 

    # --- Existing Weekly Scheduler ---
    st.subheader("Weekly Schedule")
    week_range_label = display_week_selector() 

    # Use the 'current_sheet_data' fetched at the start of this function call
    if current_sheet_data:
        dropdown_options = ["List", "Drive", "List/Drive", "Off"] 
        df_updated = display_editable_table(current_sheet_data, dropdown_options)
        if not df_updated.empty or (df_updated.empty and list(df_updated.columns) == ['Employee']): # Allow update if df is empty but was meant to clear employees
            confirm_and_update_workflow(df_updated, sheet_object_for_ops)
    elif current_sheet_data == []: # Sheet was empty or unreadable
        st.warning("No schedule data to display. The sheet might be empty or unreadable.")
    # If current_sheet_data has only a header, display_editable_table will show a warning.


# To display individual schedule (assuming this is used elsewhere, keeping it)
def individual_schedule(name, df_full_schedule): 
    if df_full_schedule.empty:
        st.warning(f"Full schedule data is empty. Cannot display schedule for {name}.")
        return pd.DataFrame()

    # Ensure 'Employee' column exists
    if 'Employee' not in df_full_schedule.columns:
        st.error("The schedule data is missing the 'Employee' column.")
        return pd.DataFrame()
        
    employee_row = df_full_schedule[df_full_schedule['Employee'].astype(str).str.strip().str.lower() == name.strip().lower()]

    if employee_row.empty:
        st.warning(f"No schedule data found for employee: {name}")
        return pd.DataFrame() 

    week_data = employee_row.drop(columns='Employee').squeeze()

    st.title(f"Weekly Schedule for {name}")

    if isinstance(week_data, pd.Series):
        week_df = pd.DataFrame(week_data).reset_index()
        week_df.columns = ['Weekday', 'Task'] 
    elif isinstance(week_data, pd.DataFrame): # Should not happen if squeeze() works on single row
        st.warning("Unexpected data format for employee's weekly schedule.")
        return pd.DataFrame()
    else: # If week_data is not a Series (e.g. if multiple employees have the same name, though unlikely with prior checks)
        st.warning(f"Could not properly extract schedule for {name}. Data format issue.")
        return pd.DataFrame()


    gb = GridOptionsBuilder.from_dataframe(week_df)
    grid_options = gb.build()
    gb.configure_default_column(width=110) 

    grid_response = AgGrid(week_df,
                        gridOptions=grid_options,
                        update_mode=GridUpdateMode.VALUE_CHANGED, 
                        fit_columns_on_grid_load=True,
                        editable=True, 
                        height=300, 
                        key=f"individual_schedule_{name.replace(' ','_')}" 
                        )
    return pd.DataFrame(grid_response['data'])

