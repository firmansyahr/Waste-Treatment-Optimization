import streamlit as st

def main():
    st.title("Waste Treatment Optimization System")
    st.write("Masukkan data limbah dan treatment yang tersedia.")

    # Bagian input data limbah secara dinamis
    st.header("Input Data Limbah")
    waste_options = [
        "Paper",
        "Cardboard",
        "Plastic",
        "Glass",
        "Metal Scrap",
        "Household Waste"
    ]
    
    # Inisialisasi session_state untuk waste_entries jika belum ada
    if "waste_entries" not in st.session_state:
        st.session_state["waste_entries"] = []
    
    col1, col2 = st.columns(2)
    with col1:
        selected_waste_type = st.selectbox("Pilih Tipe Limbah", waste_options)
    with col2:
        waste_weight = st.number_input("Berat Limbah (kg)", min_value=0.0, step=1.0)
    
    if st.button("Add Waste"):
        st.session_state["waste_entries"].append({
            "waste_type": selected_waste_type, 
            "weight": waste_weight
        })
        st.success(f"Added {selected_waste_type} dengan berat {waste_weight} kg")
    
    if st.session_state["waste_entries"]:
        st.subheader("Data Limbah yang Ditambahkan:")
        for entry in st.session_state["waste_entries"]:
            st.write(f"{entry['waste_type']} : {entry['weight']} kg")
    else:
        st.write("Belum ada data limbah yang ditambahkan.")

    # Input treatment
    st.header("Input Treatment")
    treatment_options = [
        "Sanitary Landfill",
        "Incineration",
        "Unsanitary Landfill",
        "Open Burning",
        "Open Dump",
        "Recycle",
        "Reuse"
    ]
    selected_treatments = st.multiselect("Pilih Treatment yang Dimiliki", treatment_options)

    # Optional input untuk data transportasi
    st.write("Jika limbah akan diangkut menggunakan transportasi menuju fasilitas pengolahan limbah, silakan tambahkan data transportasi di bawah ini.")
    if st.checkbox("Tambahkan data transportasi"):
        transport_options = [
            "Heavy-duty truck",
            "Medium-duty Truck",
            "Tossa Motor",
            "Pickup"
        ]
        transport_type = st.selectbox("Pilih Jenis Transportasi", transport_options)
        travel_distance = st.number_input("Travel Distance (Km)", min_value=0.0, step=1.0)
    else:
        transport_type = None
        travel_distance = None

    # Input Total Budget Yang Dimiliki dengan penjelasan Rupiah
    total_budget = st.number_input("Total Budget Yang Dimiliki (dalam Rupiah)", min_value=0.0, step=1.0)
    st.caption("Masukkan total budget perusahaan dalam satuan Rupiah.")

    if st.button("Submit"):
        st.subheader("Data yang Dimasukkan:")
        if st.session_state["waste_entries"]:
            st.write("Data Limbah:")
            for entry in st.session_state["waste_entries"]:
                st.write(f"{entry['waste_type']} : {entry['weight']} kg")
        else:
            st.write("Tidak ada data limbah yang ditambahkan.")
        
        st.write("Treatment yang Dipilih:", selected_treatments)
        
        if transport_type and travel_distance is not None:
            st.write("Jenis Transportasi:", transport_type)
            st.write("Travel Distance (Km):", travel_distance)
        else:
            st.write("Data Transportasi: Tidak ditambahkan")
        
        st.write("Total Budget Yang Dimiliki (Rupiah):", total_budget)

if __name__ == "__main__":
    main()
