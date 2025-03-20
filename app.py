import streamlit as st
import pandas as pd

# Dictionary aturan treatment berdasarkan kategori dan tipe limbah
allowed_treatments = {
    "Non-Hazardous Waste": {
        "Paper": ["Sanitary Landfill", "Incineration", "Recycle", "Open Burning", "Open Dump", "Unsanitary Landfill"],
        "Cardboard": ["Sanitary Landfill", "Incineration", "Unsanitary Landfill", "Open Dump", "Open Burning", "Recycle"],
        "Plastic": ["Incineration", "Sanitary Landfill", "Open Burning", "Open Dump", "Unsanitary Landfill", "Recycle"],
        "Glass": ["Incineration", "Sanitary Landfill", "Open Burning", "Open Dump", "Unsanitary Landfill", "Recycle"],
        "Metal Scrap": ["Sanitary Landfill", "Incineration", "Recycle"],
        "Household Waste": ["Incineration", "Sanitary Landfill", "Unsanitary Landfill", "Open Burning", "Open Dump"],
        "Wood": ["Sanitary Landfill", "Incineration", "Open Burning", "Open Dump", "Unsanitary Landfill", "Energy Recovery", "Recycle"],
        "Cement": ["Sanitary Landfill", "Recycle", "Incineration"],
        "Concrete": ["Sanitary Landfill", "Recycle"],
        "Wool": ["Sanitary Landfill", "Recycle"],
        "Biowaste": ["Open Dump", "Industrial Composting", "Anaerobic Digestion", "Incineration"],
        "Textile": ["Incineration", "Unsanitary Landfill"]
    },
    "Hazardous Waste": {
        "Gypsump Plasterboard": ["Recycle", "Sanitary Landfill"],
        "Sludge": ["Sanitary Landfill", "Incineration", "Energy Recovery"],
        "Paint": ["Sanitary Landfill", "Incineration", "Energy Recovery"],
        "Electronic Waste": ["Open Burning", "Sanitary Landfill", "Unsanitary Landfill", "Recycle"],
        "Other Hazardous Waste": ["Incineration", "Energy Recovery", "Sanitary Landfill"]
    }
}

# Fungsi dummy optimisasi yang mengembalikan data hasil optimisasi
def run_optimization(waste_data, metrics, third_party_options=None):
    # Data dummy alokasi (decision variables)
    dummy_allocation = [
        {
            "Treatment": "Recycle",
            "Allocated (kg)": 25,
            "Allocation (%)": "25%",
            "Cost Treatment (Rp/kg)": -200,
            "Distance (km)": 30,
            "Emissions (kg CO2 eq)": -5000
        },
        {
            "Treatment": "Sanitary Landfill",
            "Allocated (kg)": 50,
            "Allocation (%)": "50%",
            "Cost Treatment (Rp/kg)": 500,
            "Distance (km)": 10,
            "Emissions (kg CO2 eq)": 25000
        },
        {
            "Treatment": "Incineration",
            "Allocated (kg)": 15,
            "Allocation (%)": "15%",
            "Cost Treatment (Rp/kg)": 1000,
            "Distance (km)": 20,
            "Emissions (kg CO2 eq)": 15000
        },
        {
            "Treatment": "Open Dump",
            "Allocated (kg)": 10,
            "Allocation (%)": "10%",
            "Cost Treatment (Rp/kg)": 300,
            "Distance (km)": 25,
            "Emissions (kg CO2 eq)": 3000
        }
    ]
    # Dummy total values
    dummy_result = {
        "Status": "Optimal",
        "Total Cost (Rp)": 12345.67,
        "Total Emissions (kg CO2 eq)": 12345.67,
        "Allocation": dummy_allocation
    }
    return dummy_result

def main():
    st.title("Waste Treatment Optimization")

    # Inisialisasi session state untuk menyimpan data
    if "waste_data" not in st.session_state:
        st.session_state.waste_data = []
    if "metrics" not in st.session_state:
        st.session_state.metrics = {}

    # --- STEP 1: Input Data Limbah ---
    st.header("Input Data Limbah")
    with st.form(key="waste_form"):
        # Membuat 4 kolom: Category, Type of Waste, Amount, Unit
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            waste_category = st.selectbox("Category", ["Non-Hazardous Waste", "Hazardous Waste"])
        if waste_category == "Non-Hazardous Waste":
            waste_types = ["Paper", "Cardboard", "Plastic", "Glass", "Metal Scrap", 
                           "Household Waste", "Wood", "Cement", "Concrete", "Wool", 
                           "Biowaste", "Textile"]
        else:
            waste_types = ["Gypsump Plasterboard", "Sludge", "Paint", "Electronic Waste", "Other Hazardous Waste"]
        with col2:
            selected_waste_type = st.selectbox("Type of Waste", waste_types)
        with col3:
            amount = st.number_input("Amount of Waste", min_value=0.0, step=0.1, format="%.2f")
        with col4:
            selected_unit = st.selectbox("Unit", ["Kg", "g", "Ton"], index=0)
        add_waste = st.form_submit_button("Add Waste")

    if add_waste:
        new_waste = {
            "Category": waste_category,
            "Type of Waste": selected_waste_type,
            "Amount": amount,
            "Unit": selected_unit,
            "Allowed Treatments": ", ".join(allowed_treatments.get(waste_category, {}).get(selected_waste_type, [])) \
                                    if allowed_treatments.get(waste_category, {}).get(selected_waste_type, []) else "-"
        }
        st.session_state.waste_data.append(new_waste)
        st.success("Data limbah berhasil ditambahkan!")

    if st.session_state.waste_data:
        st.subheader("Daftar Limbah yang Telah Ditambahkan")
        df = pd.DataFrame(st.session_state.waste_data)
        # Pastikan kolom "Allowed Treatments" selalu berupa string
        if "Allowed Treatments" in df.columns:
            df["Allowed Treatments"] = df["Allowed Treatments"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        df_style = df.style.set_properties(subset=["Allowed Treatments"], **{"width": "30%"})
        st.dataframe(df_style, use_container_width=True)

    # --- STEP 2: Input Metrik Lainnya ---
    st.header("Input Metrik Perusahaan")
    with st.form(key='metrics_form'):
        company_cost = st.number_input("Biaya Maksimal Perusahaan (Rp)", min_value=0.0, format="%.2f")
        location_lat = st.number_input("Lokasi Tempat - Lat", format="%.6f")
        location_long = st.number_input("Lokasi Tempat - Long", format="%.6f")
        add_metrics = st.form_submit_button("Add Metrix")
    if add_metrics:
        st.session_state.metrics = {
            "Biaya Maksimal Perusahaan": company_cost,
            "Lokasi": {"Lat": location_lat, "Long": location_long}
        }
        st.success("Data metrik berhasil ditambahkan!")
    if st.session_state.metrics:
        st.subheader("Metrik")
        st.write(st.session_state.metrics)

    # --- STEP 3: Third Party Pengelola Limbah (Optional) ---
    st.header("Third Party Pengelola Limbah (Optional)")
    include_third_party = st.checkbox("Memiliki Third Party Pengelola Limbah")
    third_party_options = None
    if include_third_party:
        st.subheader("Input Lokasi Third Party")
        col_tp = st.columns(3)
        tp_name = col_tp[0].text_input("Third Party Name", key="tp_name")
        third_party_lat = col_tp[1].number_input("Latitude", format="%.6f", key="tp_lat")
        third_party_long = col_tp[2].number_input("Longitude", format="%.6f", key="tp_long")
        st.subheader("Non-Hazardous Waste Options")
        non_hazardous_options = ["Sanitary Landfill", "Incineration", "Recycle", "Open Burning", "Open Dump", 
                                 "Unsanitary Landfill", "Energy Recovery", "Industrial Composting", "Anaerobic Digestion"]
        third_party_non_hazardous = {}
        for i in range(0, len(non_hazardous_options), 2):
            cols = st.columns(2)
            for j, option in enumerate(non_hazardous_options[i:i+2]):
                third_party_non_hazardous[option] = cols[j].number_input(f"{option} (%)", min_value=0.0, 
                                                                         max_value=100.0, step=1.0, value=0.0, key=f"np_{option}")
        st.subheader("Hazardous Waste Options")
        hazardous_options = ["Sanitary Landfill", "Incineration", "Recycle", "Open Burning", "Open Dump", 
                             "Unsanitary Landfill", "Energy Recovery"]
        third_party_hazardous = {}
        for i in range(0, len(hazardous_options), 2):
            cols = st.columns(2)
            for j, option in enumerate(hazardous_options[i:i+2]):
                third_party_hazardous[option] = cols[j].number_input(f"{option} (%)", min_value=0.0, 
                                                                      max_value=100.0, step=1.0, value=0.0, key=f"hp_{option}")
        third_party_options = {
            "Name": tp_name,
            "Lokasi": {"Latitude": third_party_lat, "Longitude": third_party_long},
            "Non-Hazardous Waste": third_party_non_hazardous,
            "Hazardous Waste": third_party_hazardous
        }

    # --- Tombol Optimization ---
    if st.button("Optimization"):
        st.subheader("Input yang Diterima")
        st.write("**Waste Data:**", st.session_state.get("waste_data", "Tidak ada data limbah"))
        st.write("**Metrik:**", st.session_state.get("metrics", "Tidak ada data metrik"))
        if include_third_party:
            st.write("**Third Party Options:**", third_party_options)
        else:
            st.write("**Third Party Options:** Tidak ada")
        
        # DUMMY RESULT: Optimisasi menampilkan decision variables (alokasi), cost treatment, jarak treatment, dan total emisi
        dummy_allocation = [
            {
                "Treatment": "Recycle",
                "Allocated (kg)": 25,
                "Allocation (%)": "25%",
                "Cost Treatment (Rp/kg)": -200,
                "Distance (km)": 30,
                "Emissions (kg CO2 eq)": -5000
            },
            {
                "Treatment": "Sanitary Landfill",
                "Allocated (kg)": 50,
                "Allocation (%)": "50%",
                "Cost Treatment (Rp/kg)": 500,
                "Distance (km)": 10,
                "Emissions (kg CO2 eq)": 25000
            },
            {
                "Treatment": "Incineration",
                "Allocated (kg)": 15,
                "Allocation (%)": "15%",
                "Cost Treatment (Rp/kg)": 1000,
                "Distance (km)": 20,
                "Emissions (kg CO2 eq)": 15000
            },
            {
                "Treatment": "Open Dump",
                "Allocated (kg)": 10,
                "Allocation (%)": "10%",
                "Cost Treatment (Rp/kg)": 300,
                "Distance (km)": 25,
                "Emissions (kg CO2 eq)": 3000
            }
        ]
        dummy_result = {
            "Status": "Optimal",
            "Total Cost (Rp)": 12345.67,
            "Total Emissions (kg CO2 eq)": 12345.67,
            "Allocation": dummy_allocation
        }
        
        st.subheader("Hasil Optimisasi")
        st.write("Status:", dummy_result["Status"])
        st.write("Total Cost (Rp):", dummy_result["Total Cost (Rp)"])
        st.write("Total Emissions (kg CO2 eq):", dummy_result["Total Emissions (kg CO2 eq)"])
        allocation_df = pd.DataFrame(dummy_result["Allocation"])
        st.dataframe(allocation_df)

if __name__ == '__main__':
    main()
