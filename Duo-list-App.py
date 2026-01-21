def load_data():
    headers = {
        "X-Master-Key": JSONBIN_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(f"{BASE_URL}/latest", headers=headers)
        data = response.json()
        
        # 1. Try to get the data from the standard 'record' key
        records = data.get("record", [])
        
        # 2. THE FIX: Handle "Double Wrapping"
        # If the user pasted {"record": [...]} inside the bin manually, 
        # 'records' is currently a dict, not a list. We need to go one level deeper.
        if isinstance(records, dict):
            if "record" in records:
                records = records["record"] # Unwrap it!
            elif "Category" not in records: 
                # If it's a dict but doesn't look like our data, reset it
                records = []
            else:
                # It might be a single entry not in a list
                records = [records]

        df = pd.DataFrame(records)
        
        # 3. Handle Legacy Columns (Rename old data if it exists)
        if "Filter_1" in df.columns:
            df = df.rename(columns={"Filter_1": "Type"})
        if "Filter_2" in df.columns:
            df = df.rename(columns={"Filter_2": "Vibe"})
        
        # 4. Ensure all required columns exist
        expected_cols = ["Category", "Activity", "Type", "Vibe", "Status", "Link"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = "" 
        
        # 5. Filter out empty rows
        if "Category" in df.columns:
            df = df[df["Category"].astype(bool)] 
        
        return df

    except Exception as e:
        st.error(f"Error loading data: {e}")
        # Debug helper: Uncomment the line below if it still fails to see the raw data
        # st.write(data) 
        return pd.DataFrame(columns=["Category", "Activity", "Type", "Vibe", "Status", "Link"])
