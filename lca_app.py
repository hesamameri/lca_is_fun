import streamlit as st
import pandas as pd

# LCA Calculation Functions
def calculate_emissions(row):
    # Simple emission factors (hypothetical for educational purposes)
    emission_factors = {'steel': 2.0, 'plastic': 3.5, 'aluminum': 1.5}  # kg CO2e per kg
    return row['Quantity'] * emission_factors.get(row['Material'], 0)

def calculate_water_use(row):
    # Hypothetical water use factors
    water_factors = {'steel': 10.0, 'plastic': 5.0, 'aluminum': 8.0}  # liters per kg
    return row['Quantity'] * water_factors.get(row['Material'], 0)

# Streamlit App Setup
st.title("Life Cycle Assessment Calculator with Table Input")

# Initialize session state for table data
if 'table_data' not in st.session_state:
    st.session_state.table_data = pd.DataFrame(columns=['Material', 'Quantity', 'Emissions', 'Water Use'])

# Input Table
st.write("### Enter Material Data")
edited_df = st.data_editor(
    st.session_state.table_data,
    column_config={
        "Material": st.column_config.SelectboxColumn(
            "Material",
            options=["steel", "plastic", "aluminum"],
            help="Select the material type",
            width="small"
        ),
        "Quantity": st.column_config.NumberColumn(
            "Quantity (kg)",
            min_value=0.0,
            format="%.2f",
            help="Enter the quantity in kilograms"
        )
    },
    num_rows="dynamic",
    key="table_input"
)

# Button to Calculate
if st.button("Calculate LCA"):
    # Perform calculations
    edited_df['Emissions'] = edited_df.apply(calculate_emissions, axis=1)
    edited_df['Water Use'] = edited_df.apply(calculate_water_use, axis=1)
    
    # Display results
    st.write("### LCA Results")
    st.dataframe(edited_df, use_container_width=True)

    # Summarize total impacts
    st.write("### Total Impact")
    st.write(f"- **Total Emissions:** {edited_df['Emissions'].sum():.2f} kg CO2e")
    st.write(f"- **Total Water Use:** {edited_df['Water Use'].sum():.2f} liters")

    # Save back to session state for persistence
    st.session_state.table_data = edited_df

# Explanation of calculations
st.write("#### Calculation Details:")
st.write("- **Emission Factors:** {'steel': 2.0, 'plastic': 3.5, 'aluminum': 1.5} kg CO2e/kg")
st.write("- **Water Use Factors:** {'steel': 10.0, 'plastic': 5.0, 'aluminum': 8.0} liters/kg")
st.write("These factors are simplified for educational purposes.")