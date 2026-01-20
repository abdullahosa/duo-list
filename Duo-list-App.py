import streamlit as st
import pandas as pd
import requests
import json

# --- CONFIGURATION ---
JSONBIN_KEY = st.secrets["JSONBIN_KEY"]
BIN_ID = st.secrets["BIN_ID"]
BASE_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"

# --- FUNCTIONS ---
def load_data():
    headers = {
        "X-Master-Key": JSONBIN_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(f"{BASE_URL}/latest", headers=headers)
        data = response.json()
        
        # JSONBin v3 puts the actual data inside 'record'
        records = data.get("record", [])
        
        if isinstance(records, dict):
            records = [] 

        # Create DataFrame
        df = pd.DataFrame(records)
        
        # FORCE columns to exist
        expected_cols = ["Category", "Activity", "Filter_1", "Filter_2", "Status"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = "" 
        
        # Clean empty rows
        if "Category" in df.columns:
            df = df[df["Category"].astype(bool)] 
        
        return df

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=["Category", "Activity", "Filter_1", "Filter_2", "Status"])

def save_data(df):
    headers = {
        "X-Master-Key": JSONBIN_KEY,
        "Content-Type": "application/json"
    }
    json_data = df.to_dict(orient="records")
    
    try:
        response = requests.put(BASE_URL, headers=headers, json=json_data)
        if response.status_code == 200:
            return True
        else:
            st.error(f"Error saving data: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

# --- APP LAYOUT ---
st.set_page_config(page_title="Our Activity Board", page_icon="🎯", layout="wide")
st.title("🎯 What should we do today?")

# Sidebar: Add New Items
with st.sidebar:
    st.header("Add New Activity")
    new_cat = st.selectbox("Category", ["Vacation", "Gaming", "Date Night", "Challenge", "Movies"])
    new_act = st.text_input("Activity Name")
    
    if new_cat == "Vacation":
        f1_label, f2_label = "Season", "Vibe"
        f1_opts = ["Summer", "Winter", "Spring", "Fall", "Any"]
        f2_opts = ["Relaxing", "Adventure", "City", "Nature"]
    elif new_cat == "Movies":
        f1_label, f2_label = "Genre", "Length"
        f1_opts = ["Action", "Comedy", "Drama", "Horror", "Sci-Fi"]
        f2_opts = ["Short", "Feature", "Series"]
    elif new_cat == "Gaming":
        f1_label, f2_label = "Genre", "Mode"
        f1_opts = ["RPG", "FPS", "Puzzle", "Sim"]
        f2_opts = ["Co-op", "Single", "Versus"]
    else: 
        f1_label, f2_label = "Effort", "Cost"
        f1_opts = ["Low", "Medium", "High"]
        f2_opts = ["Free", "$", "$$", "$$$"]

    new_f1 = st.selectbox(f1_label, f1_opts)
    new_f2 = st.selectbox(f2_label, f2_opts)
    
    if st.button("Add to List"):
        if new_act:
            df = load_data()
            new_row = {"Category": new_cat, "Activity": new_act, "Filter_1": new_f1, "Filter_2": new_f2, "Status": "To Do"}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            if save_data(df):
                st.success(f"Added {new_act}!")
                st.rerun()

# --- MAIN DISPLAY ---
df = load_data()

# 1. VIEW TOGGLE
view_option = st.radio("View:", ["Active List", "Completed History"], horizontal=True)
target_status = "To Do" if view_option == "Active List" else "Completed"

tab1, tab2, tab3, tab4, tab5 = st.tabs(["✈️ Vacations", "🎮 Gaming", "🍷 Date Nights", "🏆 Challenges", "🎬 Movies"])

def render_tab(category_name, filter1_name, filter2_name):
    # Filter by Category AND by Status (To Do vs Completed)
    subset = df[(df["Category"] == category_name) & (df["Status"] == target_status)]
    
    if subset.empty:
        if target_status == "To Do":
            st.info(f"No active {category_name} plans. Add one in the sidebar!")
        else:
            st.write("Nothing completed yet.")
        return

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        f1_val = st.multiselect(f"Filter by {filter1_name}", options=subset["Filter_1"].unique())
    with col2:
        f2_val = st.multiselect(f"Filter by {filter2_name}", options=subset["Filter_2"].unique())

    if f1_val:
        subset = subset[subset["Filter_1"].isin(f1_val)]
    if f2_val:
        subset = subset[subset["Filter_2"].isin(f2_val)]

    # 2. EDITABLE DATA FRAME
    # This allows you to change "Status" directly in the table
    edited_df = st.data_editor(
        subset,
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["To Do", "Completed"],
                required=True,
            )
        },
        disabled=["Category", "Activity", "Filter_1", "Filter_2"], # Prevent editing these, only Status
        hide_index=True,
        use_container_width=True,
        key=f"editor_{category_name}_{target_status}" # Unique key for each tab
    )

    # 3. SAVE LOGIC
    # If the user changed something in the editor, edited_df will differ from subset
    if not subset.equals(edited_df):
        # Update the master dataframe 'df' with the changes from 'edited_df'
        # We use the index to map the changes back to the original rows
        df.update(edited_df)
        
        # Save to Cloud
        if save_data(df):
            st.toast("Updated!", icon="✅")
            st.rerun()

    # Random Picker (Only show on Active list)
    if target_status == "To Do":
        if st.button(f"Pick a Random {category_name}", key=f"btn_{category_name}"):
            if not subset.empty:
                choice = subset.sample(1).iloc[0]
                st.balloons()
                st.success(f"**You should do:** {choice['Activity']} ({choice['Filter_1']})")

with tab1:
    render_tab("Vacation", "Season", "Vibe")
with tab2:
    render_tab("Gaming", "Genre", "Mode")
with tab3:
    render_tab("Date Night", "Effort", "Cost")
with tab4:
    render_tab("Challenge", "Effort", "Cost")
with tab5:
    render_tab("Movies", "Genre", "Length")
