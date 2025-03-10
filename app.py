import streamlit as st
import pulp

def optimize_treatment(total_waste, total_budget, selected_treatments, treatment_data):
    # Buat model optimasi (minimize total emisi)
    prob = pulp.LpProblem("Minimize_CO2_Emissions", pulp.LpMinimize)
    
    # Variabel keputusan: jumlah limbah yang dialokasikan untuk tiap treatment
    x = {}
    for t in selected_treatments:
        # Batas atas adalah kapasitas pengolahan untuk treatment tersebut
        x[t] = pulp.LpVariable(f"x_{t}", lowBound=0, upBound=treatment_data[t]['capacity'])
    
    # Constraint: Jumlah alokasi harus sama dengan total limbah
    prob += pulp.lpSum([x[t] for t in selected_treatments]) == total_waste, "TotalWaste"
    
    # Constraint: Total biaya tidak boleh melebihi total budget
    prob += pulp.lpSum([treatment_data[t]['cost'] * x[t] for t in selected_treatments]) <= total_budget, "BudgetConstraint"
    
    # Fungsi objektif: minimalkan total emisi CO2
    prob += pulp.lpSum([treatment_data[t]['emission'] * x[t] for t in selected_treatments]), "TotalEmissions"
    
    # Lakukan optimasi
    prob.solve()
    
    status = pulp.LpStatus[prob.status]
    allocation = {t: x[t].varValue for t in selected_treatments}
    total_emissions = pulp.value(prob.objective)
    total_cost = sum(treatment_data[t]['cost'] * allocation[t] for t in selected_treatments)
    
    return status, allocation, total_emissions, total_cost

def main():
    st.title("Waste Treatment Optimization System")
    st.write("Masukkan data limbah, treatment, dan informasi lainnya.")

    # --- Bagian Input Data Limbah ---
    st.header("Input Data Limbah")
    waste_options = [
        "Paper",
        "Cardboard",
        "Plastic",
        "Glass",
        "Metal Scrap",
        "Household Waste"
    ]
    
    # Inisialisasi session_state untuk menyimpan entri limbah
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
    
    # Hitung total berat limbah
    total_waste = sum([entry['weight'] for entry in st.session_state["waste_entries"]])
    
    # --- Bagian Input Treatment ---
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
    
    # Data contoh untuk tiap treatment
    treatment_data = {
        "Sanitary Landfill": {"emission": 0.3, "cost": 1000, "capacity": 1000},
        "Incineration": {"emission": 1.0, "cost": 2000, "capacity": 800},
        "Unsanitary Landfill": {"emission": 0.5, "cost": 500, "capacity": 1500},
        "Open Burning": {"emission": 2.0, "cost": 300, "capacity": 700},
        "Open Dump": {"emission": 0.4, "cost": 200, "capacity": 2000},
        "Recycle": {"emission": 0.1, "cost": 1500, "capacity": 500},
        "Reuse": {"emission": 0.05, "cost": 1200, "capacity": 600}
    }
    
    # --- Input Data Transportasi ---
    st.header("Input Data Transportasi (Opsional)")
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
    
    # --- Input Total Budget ---
    st.header("Input Total Budget")
    total_budget = st.number_input("Total Budget Yang Dimiliki (dalam Rupiah)", min_value=0.0, step=1.0)
    st.caption("Masukkan total budget perusahaan dalam satuan Rupiah.")
    
    # --- Tombol Submit dan Optimasi ---
    if st.button("Submit dan Optimasi"):
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
        
        st.write("Total Budget (Rupiah):", total_budget)
        st.write("Total Limbah (kg):", total_waste)
        
        # Validasi input untuk optimasi
        if total_waste <= 0:
            st.error("Total berat limbah harus lebih dari 0.")
        elif not selected_treatments:
            st.error("Pilih minimal 1 treatment untuk optimasi.")
        elif total_budget <= 0:
            st.error("Total budget harus lebih dari 0.")
        else:
            # Lakukan optimasi hanya untuk treatment yang dipilih
            # Filter treatment_data sesuai treatment yang dipilih
            selected_treatment_data = {t: treatment_data[t] for t in selected_treatments}
            
            status, allocation, total_emissions, total_cost = optimize_treatment(total_waste, total_budget, selected_treatments, treatment_data)
            
            st.subheader("Hasil Optimasi")
            st.write("Status Solusi:", status)
            if status == "Optimal":
                st.write("Alokasi Limbah per Treatment:")
                for t, value in allocation.items():
                    st.write(f"{t} : {value:.2f} kg")
                st.write("Total Emisi CO₂:", total_emissions, "satuan")
                st.write("Total Biaya:", total_cost, "Rupiah")
            else:
                st.error("Solusi optimal tidak ditemukan. Periksa kembali input dan constraint yang diberikan.")

if __name__ == "__main__":
    main()
