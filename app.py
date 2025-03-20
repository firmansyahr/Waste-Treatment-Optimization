import streamlit as st

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

# Fungsi dummy optimisasi (tambahkan parameter third_party_options)
def run_optimization(waste_data, metrics, third_party_options=None):
    result = {
        "status": "Optimal",
        "total_cost": 12345.67,
        "details": "Hasil optimisasi dummy berdasarkan input yang diberikan.",
        "waste_data": waste_data,
        "metrics": metrics,
        "third_party": third_party_options
    }
    return result

def main():
    st.title("Waste Treatment Optimization")
    
    # Inisialisasi session state untuk menyimpan data
    if "waste_data" not in st.session_state:
        st.session_state.waste_data = []
    if "metrics" not in st.session_state:
        st.session_state.metrics = {}

    # --- STEP 1: Input Data Limbah ---
    st.header("Step 1: Input Data Limbah")

    with st.form(key="waste_form"):
        # Membuat 4 kolom: Category, Type of Waste, Amount, Unit
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

        with col1:
            waste_category = st.selectbox("Category", ["Non-Hazardous Waste", "Hazardous Waste"])

        # Tentukan daftar type of waste berdasarkan kategori
        if waste_category == "Non-Hazardous Waste":
            waste_types = [
                "Paper", "Cardboard", "Plastic", "Glass", "Metal Scrap",
                "Household Waste", "Wood", "Cement", "Concrete", "Wool",
                "Biowaste", "Textile"
            ]
        else:
            waste_types = [
                "Gypsump Plasterboard", "Sludge", "Paint",
                "Electronic Waste", "Other Hazardous Waste"
            ]

        with col2:
            selected_waste_type = st.selectbox("Type of Waste", waste_types)

        # Dapatkan daftar treatment yang diizinkan untuk kategori + tipe terpilih
        treatments = allowed_treatments.get(waste_category, {}).get(selected_waste_type, [])
        # Tampilkan info Allowed Treatments pada form (sebagai informasi saja)
        st.info(f"Allowed Treatments: {', '.join(treatments) if treatments else 'Tidak ada aturan'}")

        with col3:
            amount = st.number_input("Amount of Waste", min_value=0.0, step=0.1, format="%.2f")

        with col4:
            # Menjadikan "Kg" sebagai pilihan utama (default)
            selected_unit = st.selectbox("Unit", ["Kg", "g", "Ton"], index=0)

        add_waste = st.form_submit_button("Add Waste")

    if add_waste:
        new_waste = {
            "Category": waste_category,
            "Type of Waste": selected_waste_type,
            "Amount": amount,
            "Unit": selected_unit,
            "Allowed Treatments": ", ".join(treatments) if treatments else "-"
        }
        st.session_state.waste_data.append(new_waste)
        st.success("Data limbah berhasil ditambahkan!")

    if st.session_state.waste_data:
        st.subheader("Daftar Limbah yang Telah Ditambahkan")
        st.table(st.session_state.waste_data)

    # --- STEP 2: Input Metrik Lainnya ---
    st.header("Step 2: Input Metrik Lainnya")
    with st.form(key='metrics_form'):
        company_cost = st.number_input("Biaya Maksimal Perusahaan", min_value=0.0, format="%.2f")
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
    st.header("Step 3: Third Party Pengelola Limbah (Optional)")
    include_third_party = st.checkbox("Include Third Party Pengelola Limbah")
    
    third_party_options = None
    if include_third_party:
        st.subheader("Input Lokasi Third Party")
        third_party_lat = st.number_input("Third Party Latitude", format="%.6f", key="tp_lat")
        third_party_long = st.number_input("Third Party Longitude", format="%.6f", key="tp_long")
        
        st.subheader("Non-Hazardous Waste Options")
        non_hazardous_options = [
            "Sanitary Landfill", "Incineration", "Recycle", "Open Burning",
            "Open Dump", "Unsanitary Landfill", "Energy Recovery",
            "Industrial Composting", "Anaerobic Digestion"
        ]
        third_party_non_hazardous = {}
        for option in non_hazardous_options:
            third_party_non_hazardous[option] = st.number_input(
                f"{option} (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0, key=f"np_{option}"
            )
        
        st.subheader("Hazardous Waste Options")
        hazardous_options = [
            "Sanitary Landfill", "Incineration", "Recycle", "Open Burning",
            "Open Dump", "Unsanitary Landfill", "Energy Recovery"
        ]
        third_party_hazardous = {}
        for option in hazardous_options:
            third_party_hazardous[option] = st.number_input(
                f"{option} (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0, key=f"hp_{option}"
            )
        
        third_party_options = {
            "Lokasi": {"Latitude": third_party_lat, "Longitude": third_party_long},
            "Non-Hazardous Waste": third_party_non_hazardous,
            "Hazardous Waste": third_party_hazardous
        }
    
    # --- Tombol Optimization ---
    if st.button("Optimization"):
        st.subheader("Input yang Diterima")
        st.write("**Waste Data:**")
        st.write(st.session_state.get("waste_data", "Tidak ada data limbah"))
        st.write("**Metrik:**")
        st.write(st.session_state.get("metrics", "Tidak ada data metrik"))
        if include_third_party:
            st.write("**Third Party Options:**")
            st.write(third_party_options)
        else:
            st.write("**Third Party Options:** Tidak ada")
        
        result = run_optimization(
            st.session_state.get("waste_data", []),
            st.session_state.get("metrics", {}),
            third_party_options
        )
        
        st.subheader("Hasil Optimisasi")
        st.write(result)

if __name__ == '__main__':
    main()
