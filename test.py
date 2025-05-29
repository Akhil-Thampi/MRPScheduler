import gspread
from gspread_dataframe import get_as_dataframe
import pandas as pd
import streamlit as st
from functions import *
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
sheet = gc.open('MyRoti').worksheet('Sheet1')  
df = get_as_dataframe(sheet)

#Function to display Individual Schedule Summary 
def emp_ind():
    name = "Adwaith"
    employee_row = df[df['Employee']==name]
    week_data = employee_row.drop(columns='Employee').squeeze()

    selected_name = st.selectbox("Select Employee",df["Employee"])
    updated_schedule = individual_schedule(selected_name,week_data)


# Function to display the Current Week Schedule as per last updated Google Sheet
def schedule_summary():
    st.title("Current Week Schedule")
    

    # Force re-fetch if sheet_updated flag is set
    if "sheet_updated" in st.session_state and st.session_state.sheet_updated:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
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
        gb.configure_column(col, editable=True)

    grid_options = gb.build()
    gb.configure_default_column(width=150)
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        editable=True,
        height=300
    )

    return pd.DataFrame(grid_response['data'])
