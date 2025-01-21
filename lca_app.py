import streamlit as st
import pandas as pd
import uuid
from pymongo import MongoClient
from streamlit import secrets
# MongoDB connection (keep your credentials secure)
connection_string = st.secrets['mongo']['uri']
client = MongoClient(connection_string)
db = client['LCA']
collection = db['test']

# Session ID Management
if 'session_id' not in st.query_params:
    session_id = str(uuid.uuid4())
    st.query_params['session_id'] = session_id
else:
    session_id = st.query_params['session_id']

def get_user_data():
    user_data = collection.find_one({"session_id": session_id})
    if user_data is None:
        user_data = {
            "session_id": session_id,
            "lca_data": {
                "stages": [],
                "variables": {"inputs": [], "outputs": []},
                "data": {}
            }
        }
        collection.insert_one(user_data)
    return user_data

# Example usage within Streamlit app
user_data = get_user_data()

# Session State Initialization
if 'current_stage' not in st.session_state:
    st.session_state.current_stage = {"life_cycle_stage": "", "inputs": [], "outputs": []}

def update_mongo_data(data):
    collection.update_one(
        {"session_id": session_id}, 
        {"$set": {"lca_data.data": data}}, 
        upsert=True
    )

# UI Styling
st.markdown("""
<style>
    .sidebar .sidebar-content {
        background-color: #f0f2f6;
    }
    .stButton>button {
        background-color: #4CAF50;
        border: none;
        color: white;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        transition-duration: 0.4s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 12px 16px 0 rgba(0,0,0,0.24), 0 17px 50px 0 rgba(0,0,0,0.19);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar for Input
with st.sidebar:
    st.subheader("Add LCA Data")
    st.session_state.current_stage["life_cycle_stage"] = st.text_input("Life Cycle Stage", st.session_state.current_stage["life_cycle_stage"])

    st.write("### Inputs")
    for i, input in enumerate(st.session_state.current_stage["inputs"]):
        input["Y1"] = st.text_input(f"Input Name {i+1}", input.get("Y1", ""))
        input["functional_unit"] = st.text_input(f"Functional Unit {i+1}", input.get("functional_unit", ""))
        input["quantity"] = st.number_input(f"Quantity {i+1}", value=input.get("quantity", 0.0))
        if st.button(f"Delete Input {i+1}", key=f"delete_input_{i}"):
            st.session_state.current_stage["inputs"].pop(i)
            st.rerun()
    if st.button("Add New Input"):
        st.session_state.current_stage["inputs"].append({"Y1": "", "functional_unit": "", "quantity": 0.0})

    st.write("### Outputs")
    for i, output in enumerate(st.session_state.current_stage["outputs"]):
        output["name"] = st.text_input(f"Output Name {i+1}", output.get("name", ""))
        output["functional_unit"] = st.text_input(f"Functional Unit {i+1}", output.get("functional_unit", ""))
        output["quantity"] = st.number_input(f"Quantity {i+1}", value=output.get("quantity", 0.0))
        if st.button(f"Delete Output {i+1}", key=f"delete_output_{i}"):
            st.session_state.current_stage["outputs"].pop(i)
            st.rerun()
    if st.button("Add New Output"):
        st.session_state.current_stage["outputs"].append({"name": "", "functional_unit": "", "quantity": 0.0})

    if st.button("Save Stage"):
        if st.session_state.current_stage["life_cycle_stage"]:
            stage_name = st.session_state.current_stage["life_cycle_stage"]
            user_data['lca_data']['data'][stage_name] = st.session_state.current_stage
            update_mongo_data(user_data['lca_data']['data'])
            st.session_state.current_stage = {"life_cycle_stage": "", "inputs": [], "outputs": []}
            st.success("Stage saved to LCA")
            st.rerun()

# Main Content - Display Data from MongoDB
if user_data['lca_data']['data']:
    for stage_name, stage_data in list(user_data['lca_data']['data'].items()):  # Use list() to avoid runtime error during iteration
        st.subheader(f"Life Cycle Stage: {stage_name}")
        st.write("**Inputs:**")
        for input in stage_data['inputs']:
            st.write(f"- **{input['Y1']}:** Functional Unit: {input['functional_unit']}, Quantity: {input['quantity']}")
        st.write("**Outputs:**")
        for output in stage_data['outputs']:
            st.write(f"- **{output['name']}:** Functional Unit: {output['functional_unit']}, Quantity: {output['quantity']}")
        
        col1, col2 = st.columns(2)
        if col1.button(f"Edit {stage_name}", key=f"edit_{stage_name}"):
            st.session_state.current_stage = stage_data
            st.session_state.current_stage["life_cycle_stage"] = stage_name
            st.rerun()
        
        if col2.button(f"Delete {stage_name}", key=f"delete_{stage_name}"):
            del user_data['lca_data']['data'][stage_name]
            update_mongo_data(user_data['lca_data']['data'])
            st.success(f"Stage '{stage_name}' deleted")
            st.rerun()

# Display MongoDB Data for Verification in a Table
st.subheader("Current MongoDB Data")

# Prepare data for the table
table_data = []
for stage_name, stage_data in user_data['lca_data']['data'].items():
    for input in stage_data['inputs']:
        table_data.append({
            'Stage': stage_name,
            'Type': 'Input',
            'Name': input['Y1'],
            'Functional Unit': input['functional_unit'],
            'Quantity': input['quantity']
        })
    for output in stage_data['outputs']:
        table_data.append({
            'Stage': stage_name,
            'Type': 'Output',
            'Name': output['name'],
            'Functional Unit': output['functional_unit'],
            'Quantity': output['quantity']
        })

# Convert the list of dictionaries to a DataFrame
df = pd.DataFrame(table_data)

# Display the DataFrame as a table
st.table(df)