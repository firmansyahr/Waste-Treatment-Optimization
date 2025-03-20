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

# Fungsi dummy optimisasi (silakan ganti dengan model optimisasi yang diinginkan)
def run_optimization(waste_data, metrics):
    result = {
        "status": "Optimal",
        "total_cost": 12345.67,
        "details": "Hasil optimisasi dummy berdasarkan input yang diberikan."
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
    
    # Menggunakan st.form untuk mengelompokkan input dalam satu form
    with st.form(key="waste_form"):
        # Membuat 5 kolom: Category, Type of Waste, Treatment, Amount of Waste, Unit
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])

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

        with col3:
            selected_treatment = st.selectbox("Treatment", treatments)

        with col4:
            amount = st.number_input("Amount of Waste", min_value=0.0, step=0.1, format="%.2f")

        with col5:
            selected_unit = st.selectbox("Unit", ["g", "Kg", "Ton"])

        # Tombol untuk menambahkan waste ke dalam session state
        add_waste = st.form_submit_button("Add Waste")

    # Jika tombol "Add Waste" ditekan
    if add_waste:
        new_waste = {
            "Category": waste_category,
            "Type of Waste": selected_waste_type,
            "Treatment": selected_treatment,
            "Amount": amount,
            "Unit": selected_unit
        }
        st.session_state.waste_data.append(new_waste)
        st.success("Data limbah berhasil ditambahkan!")

    # Tampilkan tabel data limbah yang telah diinput
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
    
    # Tampilkan data metrik jika sudah ada
    if st.session_state.metrics:
        st.subheader("Metrik")
        st.write(st.session_state.metrics)
    
    # --- Tombol Optimization ---
    if st.button("Optimization"):
        st.subheader("Input yang Diterima")
        st.write("**Waste Data:**")
        st.write(st.session_state.get("waste_data", "Tidak ada data limbah"))
        st.write("**Metrik:**")
        st.write(st.session_state.get("metrics", "Tidak ada data metrik"))
        
        # Panggil fungsi optimisasi
        result = run_optimization(
            st.session_state.get("waste_data", []),
            st.session_state.get("metrics", {})
        )
        
        st.subheader("Hasil Optimisasi")
        st.write(result)

if __name__ == '__main__':
    main()
