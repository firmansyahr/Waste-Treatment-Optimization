import streamlit as st

def main():
    st.title("Waste Treatment Optimization System")
    st.write("Masukkan data limbah dan treatment yang tersedia.")

    # Pilihan tipe limbah
    waste_options = [
        "Paper",
        "Cardboard",
        "Plastic",
        "Glass",
        "Metal Scrap",
        "Household Waste"
    ]
    waste_type = st.multiselect("Pilih Tipe Limbah", waste_options)

    # Pilihan treatment
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

    # Input jumlah limbah (kg)
    waste_amount = st.number_input("Jumlah Limbah (kg)", min_value=0.0, step=1.0)

    # Optional input untuk data transportasi
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

    # Input Total Budget Yang Dimiliki
    total_budget = st.number_input("Total Budget Yang Dimiliki", min_value=0.0, step=1.0)

    if st.button("Submit"):
        st.subheader("Data yang Dimasukkan:")
        st.write("Tipe Limbah:", waste_type)
        st.write("Treatment yang Dipilih:", selected_treatments)
        st.write("Jumlah Limbah (kg):", waste_amount)
        
        if transport_type and travel_distance is not None:
            st.write("Jenis Transportasi:", transport_type)
            st.write("Travel Distance (Km):", travel_distance)
        else:
            st.write("Data Transportasi: Tidak ditambahkan")
        
        st.write("Total Budget Yang Dimiliki:", total_budget)

if __name__ == "__main__":
    main()
