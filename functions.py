import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from datetime import datetime, timedelta
from gspread_dataframe import get_as_dataframe
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import pandas as pd

def get_google_sheet(sheet_name, worksheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("./credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).worksheet(worksheet_name)
    data = sheet.get_all_values()
    return sheet, data



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
    with col3:
        if st.button("Next Week ➡️"):
            st.session_state["week_offset"] = week_offset + 1

    start_date, end_date = get_week_range(st.session_state.get("week_offset", 0))
    with col2:
        st.markdown(f"### 📅 {start_date} to {end_date}")
    
    return f"{start_date} to {end_date}"  # Can be used as a key or label



def display_editable_table(data, dropdown_values):
    df = pd.DataFrame(data[1:], columns=data[0])  # Skip header row
    gb = GridOptionsBuilder.from_dataframe(df)

    # Add dropdown to each column
    for col in df.columns:
        gb.configure_column(col, editable=True, cellEditor='agSelectCellEditor',
                            cellEditorParams={'values': dropdown_values})

    grid_options = gb.build()
    grid_response = AgGrid(df, gridOptions=grid_options,
                           update_mode=GridUpdateMode.VALUE_CHANGED,
                           editable=True,
                           height=300)

    return pd.DataFrame(grid_response['data'])




def confirm_and_update_workflow(df_updated, sheet):
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = True

    if st.session_state.edit_mode:
        st.write("### 🔍 Preview Updated Table")
        st.dataframe(df_updated)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update to Google Sheet"):
                sheet.update([df_updated.columns.values.tolist()] + df_updated.values.tolist())
                st.success("✅ Sheet updated successfully!")
                st.session_state.edit_mode = True

                # Rerun the app to reflect latest changes

#Login function

USER_CREDENTIALS = {
    "Adwaith": "password123",
    "user": "testpass"
}



#Schedule only if Login
def schedule_page():
    st.title("📆 Weekly Scheduler")
    week_range_label = display_week_selector()
    sheet, data = get_google_sheet("MyRoti", "Sheet1")
    dropdown_options = ["List", "Drive", "List/Drive", "Off"]
    df_updated = display_editable_table(data, dropdown_options)
    confirm_and_update_workflow(df_updated, sheet)          



#To display individual schedule

def individual_schedule(name,df):
    # Filter the employee row
    gc = gspread.service_account(filename='./credentials.json')
    sheet = gc.open('MyRoti').worksheet('Sheet1')  
    df = get_as_dataframe(sheet)
    employee_row = df[df['Employee'] == name]

    # Drop the 'Employee' column to get only weekdays
    week_data = employee_row.drop(columns='Employee').squeeze()

    # Display title and the week's data as a table
    st.title(f"Weekly Schedule for {name}")

    # Convert series to DataFrame for AgGrid
    week_df = pd.DataFrame(week_data).reset_index()
    week_df.columns = ['Weekday', 'Task']

    # Show using AgGrid
    gb = GridOptionsBuilder.from_dataframe(week_df)
    gb.configure_column("Task", editable=True, cellEditor='agSelectCellEditor', cellEditorParams={'values': ['Off', 'List', 'Drive', 'List/Drive']})  # sample values
    grid_options = gb.build()

    grid_response = AgGrid(week_df,
                           gridOptions=grid_options,
                           update_mode=GridUpdateMode.VALUE_CHANGED,
                           editable=True,
                           height=300)

    # Return the updated DataFrame
    return grid_response['data']
