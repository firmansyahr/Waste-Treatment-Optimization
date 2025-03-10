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

    if st.button("Submit"):
        st.subheader("Data yang Dimasukkan:")
        st.write("Tipe Limbah:", waste_type)
        st.write("Treatment yang Dipilih:", selected_treatments)
        st.write("Jumlah Limbah (kg):", waste_amount)

if __name__ == "__main__":
    main()
