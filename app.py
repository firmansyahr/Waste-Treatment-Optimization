import streamlit as st

def run_optimization(waste_data, metrics, third_party_options):
    """
    Fungsi dummy untuk optimisasi.
    Di sini Anda bisa mengintegrasikan model optimisasi, misalnya menggunakan library PuLP atau lainnya.
    """
    # Contoh: menampilkan input yang diterima dan menghasilkan hasil dummy
    result = {
        "status": "Optimal",
        "total_cost": 12345.67,
        "details": "Hasil optimisasi dummy berdasarkan input yang diberikan."
    }
    return result

def main():
    st.title("Waste Treatment Optimization")
    
    # --- STEP 1: Input Data Limbah ---
    st.header("Step 1: Input Data Limbah")
    with st.form(key='waste_form'):
        waste_name = st.text_input("Nama Limbah")
        waste_type = st.selectbox("Tipe Limbah", ["Non-Hazardous Waste", "Hazardous Waste"])
        waste_weight = st.number_input("Berat", min_value=0.0, format="%.2f")
        waste_uom = st.text_input("UoM")
        add_waste = st.form_submit_button("Add Waste")
    
    if "waste_data" not in st.session_state:
        st.session_state.waste_data = []

    if add_waste:
        new_waste = {
            "Nama Limbah": waste_name,
            "Tipe Limbah": waste_type,
            "Berat": waste_weight,
            "UoM": waste_uom
        }
        st.session_state.waste_data.append(new_waste)
        st.success("Data limbah berhasil ditambahkan!")
    
    if st.session_state.waste_data:
        st.subheader("Daftar Limbah")
        st.write(st.session_state.waste_data)
    
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
    
    if "metrics" in st.session_state:
        st.subheader("Metrik")
        st.write(st.session_state.metrics)
    
    # --- STEP 3: Optional Third Party Pengelola Limbah ---
    st.header("Step 3: Third Party Pengelola Limbah (Opsional)")
    include_third_party = st.checkbox("Include Third Party Waste Treatment Options")
    
    third_party_options = {}
    if include_third_party:
        st.subheader("Non-Hazardous Waste Options")
        third_party_options["Non-Hazardous Waste"] = {}
        non_hazardous_options = [
            "Sanitary Landfill", "Incineration", "Recycle", "Open Burning", 
            "Open Dump", "Unsanitary Landfill", "Energy Recovery", 
            "Industrial Composting", "Anaerobic Digestion"
        ]
        for option in non_hazardous_options:
            capacity = st.number_input(f"{option} (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key=f"nh_{option}")
            third_party_options["Non-Hazardous Waste"][option] = capacity
        
        st.subheader("Hazardous Waste Options")
        third_party_options["Hazardous Waste"] = {}
        hazardous_options = [
            "Sanitary Landfill", "Incineration", "Recycle", "Open Burning", 
            "Open Dump", "Unsanitary Landfill", "Energy Recovery"
        ]
        for option in hazardous_options:
            capacity = st.number_input(f"{option} (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key=f"h_{option}")
            third_party_options["Hazardous Waste"][option] = capacity

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
            st.write("Tidak ada opsi third party yang dipilih.")
        
        # Panggil fungsi optimisasi
        result = run_optimization(
            st.session_state.get("waste_data", []),
            st.session_state.get("metrics", {}),
            third_party_options if include_third_party else None
        )
        
        st.subheader("Hasil Optimisasi")
        st.write(result)

if __name__ == '__main__':
    main()
