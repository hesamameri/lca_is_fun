import streamlit as st
import pandas as pd
import uuid
from pymongo import MongoClient
from streamlit import secrets
import io

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

# Function to calculate LCA impacts with linked inputs and outputs
def calculate_lca_impacts(data):
    # Dictionary to store total impacts by impact name
    total_impacts = {}

    for stage_name, stage_data in data.items():
        for input_item in stage_data.get('inputs', []):
            for impact in input_item.get('impacts', []):
                impact_name = impact['name']
                impact_factor = impact['quantity']  # impact factor per unit of input
                input_quantity = input_item['quantity']
                
                impact_contribution = input_quantity * impact_factor
                
                if impact_name not in total_impacts:
                    total_impacts[impact_name] = {
                        'total': impact_contribution,
                        'unit': impact['functional_unit']
                    }
                else:
                    if total_impacts[impact_name]['unit'] == impact['functional_unit']:
                        total_impacts[impact_name]['total'] += impact_contribution
                    else:
                        st.error(f"Unit mismatch for impact '{impact_name}'. Expected {total_impacts[impact_name]['unit']}, got {impact['functional_unit']}.")

    return total_impacts

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
        input["Y1"] = st.text_input(f"Input Name {i+1}", input.get("Y1", ""), key=f"input_name_{i}")
        input["functional_unit"] = st.text_input(f"Functional Unit {i+1}", input.get("functional_unit", ""), key=f"input_unit_{i}")
        input["quantity"] = st.number_input(f"Quantity {i+1}", value=input.get("quantity", 0.0), key=f"input_quantity_{i}")
        
        # Use an expander to group impacts for each input
        with st.expander(f"Impacts for {input['Y1']}"):
            if 'impacts' not in input:
                input['impacts'] = []
            
            for j, impact in enumerate(input['impacts']):
                # Use session state to store and update impact data
                impact['name'] = st.text_input(f"Impact Name {j+1}", impact.get('name', ""), key=f"impact_name_{i}_{j}")
                impact['quantity'] = st.number_input(f"Impact Factor {j+1}", value=impact.get('quantity', 0.0), key=f"impact_factor_{i}_{j}")
                impact['functional_unit'] = st.text_input(f"Impact Unit {j+1}", impact.get('functional_unit', ""), key=f"impact_unit_{i}_{j}")
                
                if st.button(f"Delete Impact {j+1}", key=f"delete_impact_{i}_{j}"):
                    input['impacts'].pop(j)
                    # Clear this impact from session_state to avoid key conflicts
                    for key in st.session_state.keys():
                        if key.startswith(f"impact_{i}_{j}"):
                            del st.session_state[key]
                    st.rerun()  # Only rerun to update UI after deletion
                    break  # Break to avoid index shifting issues

            # Add new impact without causing rerun
            if st.button(f"Add New Impact", key=f"add_new_impact_{i}"):
                input['impacts'].append({
                    'name': "",
                    'quantity': 0.0,
                    'functional_unit': ""
                })
                st.rerun()  # Only rerun to update UI after adding new impact
        
        if st.button(f"Delete Input {i+1}", key=f"delete_input_{i}"):
            st.session_state.current_stage["inputs"].pop(i)
            st.rerun()  # Only rerun after deletion

    if st.button("Add New Input"):
        st.session_state.current_stage["inputs"].append({"Y1": "", "functional_unit": "", "quantity": 0.0, "impacts": []})
        st.rerun()  # Only rerun after adding new input

    if st.button("Save Stage"):
        if st.session_state.current_stage["life_cycle_stage"]:
            stage_name = st.session_state.current_stage["life_cycle_stage"]
            clean_inputs = [inp for inp in st.session_state.current_stage["inputs"] if all(inp.values()) and inp['impacts']]
            
            if clean_inputs:  # Only save if there's at least one valid input with impacts
                user_data['lca_data']['data'][stage_name] = {
                    "life_cycle_stage": stage_name,
                    "inputs": clean_inputs,
                }
                update_mongo_data(user_data['lca_data']['data'])
                st.session_state.current_stage = {"life_cycle_stage": "", "inputs": [], "outputs": []}
                st.success("Stage saved to LCA")
            else:
                st.error("No valid inputs with impacts to save. Please fill in all fields including impacts.")
            st.rerun()  # Rerun to update UI after saving

if not user_data['lca_data']['data']:
    st.title("Welcome to LCA Fun!")
    st.write("Get started by adding your life cycle stages, inputs, and impacts.")
else:
    # Main Content - Display Data from MongoDB
    if user_data['lca_data']['data']:
        for stage_name, stage_data in list(user_data['lca_data']['data'].items()):  
            st.subheader(f"Life Cycle Stage: {stage_name}")
            st.write("**Inputs:**")
            for input in stage_data['inputs']:
                st.write(f"- **{input['Y1']}:** Functional Unit: {input['functional_unit']}, Quantity: {input['quantity']}")
                for impact in input.get('impacts', []):
                    st.write(f"    - Impact: {impact['name']}, Factor: {impact['quantity']} per {input['functional_unit']}, Unit: {impact['functional_unit']}")

    # Display MongoDB Data for Verification in a Table
    st.subheader("Your Data")

    # Prepare data for the table
    table_data = []
    for stage_name, stage_data in user_data['lca_data']['data'].items():
        for input in stage_data['inputs']:
            for impact in input.get('impacts', []):
                table_data.append({
                    'Stage': stage_name,
                    'Input': input['Y1'],
                    'Impact': impact['name'],
                    'Functional Unit': input['functional_unit'],
                    'Quantity': input['quantity'],
                    'Impact Factor': impact['quantity'],
                    'Impact Unit': impact['functional_unit']
                })

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(table_data)

    # Display the DataFrame as a table
    st.table(df)

    # Download Button for Excel
    if not df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='LCA Data')
        output.seek(0)

        st.download_button(
            label="Download LCA Data as Excel",
            data=output,
            file_name='lca_data.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # Button to trigger LCA calculation
    if st.button("Calculate Life Cycle Assessment"):
        impacts = calculate_lca_impacts(user_data['lca_data']['data'])
        
        st.subheader("Life Cycle Assessment Results")
        for impact_name, impact_data in impacts.items():
            st.write(f"**{impact_name}:** {impact_data['total']:.2f} {impact_data['unit']}")
        
        # Create a DataFrame for visualization
        impacts_df = pd.DataFrame.from_dict(impacts, orient='index', columns=['Total Impact', 'Unit'])
        st.table(impacts_df)