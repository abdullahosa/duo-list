import streamlit as st
import pandas as pd
import requests
import json

# --- CONFIGURATION ---
JSONBIN_KEY = st.secrets["JSONBIN_KEY"]
BIN_ID = st.secrets["BIN_ID"]
BASE_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
SHEET_WEBHOOK_URL = st.secrets["SHEET_WEBHOOK_URL"] 

def create_google_sheet_tab(tab_name):
    """Sends a signal to the Google Sheet to create a tab itself."""
    try:
        payload = {"tabName": tab_name}
        
        response = requests.post(SHEET_WEBHOOK_URL, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            new_link = data.get("url", "")
            st.toast(f"Tab created! {tab_name}", icon="✅")
            return new_link
        else:
            st.error(f"Sheet Error: {response.text}")
            return ""
            
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return ""

# --- FUNCTIONS ---
def load_data():
    headers = {
        "X-Master-Key": JSONBIN_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(f"{BASE_URL}/latest", headers=headers)
        data = response.json()
        
        records = data.get("record", [])
        
        if isinstance(records, dict):
            records = [] 

        df = pd.DataFrame(records)
        
        # --- THE FIX: MIGRATION LOGIC ---
        # If the data has old column names, rename them to the new ones
        if "Filter_1" in df.columns:
            df = df.rename(columns={"Filter_1": "Type"})
        if "Filter_2" in df.columns:
            df = df.rename(columns={"Filter_2": "Vibe"})
        # -------------------------------
        
        # FORCE columns to exist
        expected_cols = ["Category", "Activity", "Type", "Vibe", "Status", "Link"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = "" 
        
        if "Category" in df.columns:
            df = df[df["Category"].astype(bool)] 
        
        return df

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=["Category", "Activity", "Type", "Vibe", "Status", "Link"])

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
st.set_page_config(page_title="A&A Activity Board", page_icon="🎯", layout="wide")
st.title("🎯 What should we do today?")

# Sidebar: Add New Items
with st.sidebar:
    st.header("Add New Activity")
    new_cat = st.selectbox("Category", ["Vacation", "Gaming", "Date Night", "Challenge", "Movies", "Projects"])
    new_act = st.text_input("Activity Name")
    
    if new_cat == "Vacation":
        f1_label, f2_label = "Season", "Vibe"
        f1_opts = ["Summer", "Winter", "Spring", "Fall", "Any"]
        f2_opts = ["Relaxing", "Adventure", "City", "Nature"]
    elif new_cat == "Movies":
        f1_label, f2_label = "Genre", "Type"
        f1_opts = ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Fantasy", "Animation", "Anime"]
        f2_opts = ["Movies", "Shorts", "Shows"]
    elif new_cat == "Gaming":
        f1_label, f2_label = "Genre", "Mode"
        f1_opts = ["RPG", "Story", "Puzzle", "Sim"]
        f2_opts = ["Co-op", "Single", "Versus"]
    elif new_cat == "Date Night":
        f1_label, f2_label = "Type", "Vibe"
        f1_opts = ["Stay In", "Going Out"]
        f2_opts = ["Lazy", "Bougie", "Active", "Foodie", "Explorer"]
    else: 
        f1_label, f2_label = "Effort", "Cost"
        f1_opts = ["Low", "Medium", "High"]
        f2_opts = ["Free", "$", "$$", "$$$"]

    new_f1 = st.selectbox(f1_label, f1_opts)
    new_f2 = st.selectbox(f2_label, f2_opts)
    
    if st.button("Add to List"):
        if new_act:
            df = load_data()
            new_link = ""
            
            # TRIGGER: Create Google Sheet if Vacation
            if new_cat == "Vacation":
                with st.spinner("Creating Google Sheet Tab..."):
                    new_link = create_google_sheet_tab(new_act)

            new_row = {
                "Category": new_cat, 
                "Activity": new_act, 
                "Type": new_f1, 
                "Vibe": new_f2, 
                "Status": "To Do",
                "Link": new_link 
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            if save_data(df):
                st.success(f"Added {new_act}!")
                st.rerun()

# --- MAIN DISPLAY ---
df = load_data()

# 1. VIEW TOGGLE
view_option = st.radio("View:", ["Active List", "In Progress", "Completed History"], horizontal=True)

if view_option == "Active List":
    target_status = "To Do"
elif view_option == "In Progress":
    target_status = "In Progress"
else:
    target_status = "Completed"

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["✈️ Vacations", "🎮 Gaming", "✨ Date Nights", "🏆 Challenges", "🎬 Movies", "🛠️ Projects"])

def render_tab(category_name, filter1_name, filter2_name):
    # Filter by Category AND by Status
    subset = df[(df["Category"] == category_name) & (df["Status"] == target_status)]
    
    if subset.empty:
        if target_status == "To Do":
            st.info(f"No active {category_name} plans.")
        elif target_status == "In Progress":
            st.write("Nothing currently in progress.")
        else:
            st.write("Nothing completed yet.")
        return

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        f1_val = st.multiselect(
            f"Filter by {filter1_name}", 
            options=subset["Type"].unique(),
            key=f"filter1_{category_name}_{target_status}" 
        )
    with col2:
        f2_val = st.multiselect(
            f"Filter by {filter2_name}", 
            options=subset["Vibe"].unique(),
            key=f"filter2_{category_name}_{target_status}"
        )

    if f1_val:
        subset = subset[subset["Type"].isin(f1_val)]
    if f2_val:
        subset = subset[subset["Vibe"].isin(f2_val)]

    # Configure Columns
    column_config = {
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=["To Do", "In Progress", "Completed"],
            required=True,
        ),
        "Link": st.column_config.LinkColumn("Sheet"),
        "Type": st.column_config.TextColumn(filter1_name),
        "Vibe": st.column_config.TextColumn(filter2_name)
    }

    # Editable Table
    edited_df = st.data_editor(
        subset,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key=f"editor_{category_name}_{target_status}" 
    )

    if not subset.equals(edited_df):
        df.update(edited_df)
        if save_data(df):
            st.toast("Saved!", icon="✅")
            st.rerun()

    # Random Picker
    if target_status == "To Do":
        if st.button(f"Pick a Random {category_name}", key=f"btn_{category_name}"):
            if not subset.empty:
                choice = subset.sample(1).iloc[0]
                st.balloons()
                msg = f"**You should do:** {choice['Activity']} ({choice['Type']})"
                if choice['Link']:
                    msg += f"\n\n[Open Planning Sheet]({choice['Link']})"
                st.success(msg)

with tab1:
    render_tab("Vacation", "Season", "Vibe")
with tab2:
    render_tab("Gaming", "Genre", "Mode")
with tab3:
    render_tab("Date Night", "Type", "Vibe")
with tab4:
    render_tab("Challenge", "Effort", "Cost")
with tab5:
    render_tab("Movies", "Genre", "Type")
with tab6:
    render_tab("Projects", "Effort", "Cost")


