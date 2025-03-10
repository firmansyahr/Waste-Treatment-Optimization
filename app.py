import streamlit as st
import pulp

def optimize_treatment(total_waste, total_budget, selected_treatments, treatment_data):
    """
    Model optimasi MILP:
    - x[t]: jumlah limbah yang dialokasikan untuk treatment t, dengan batas atas kapasitas.
    - x_overflow: jumlah limbah yang dialihkan ke treatment alternatif dengan penalti.
    """
    prob = pulp.LpProblem("Minimize_CO2_Emissions", pulp.LpMinimize)
    
    # Variabel keputusan untuk tiap treatment
    x = {}
    for t in selected_treatments:
        x[t] = pulp.LpVariable(f"x_{t}", lowBound=0, upBound=treatment_data[t]['capacity'])
    
    # Variabel overflow: tidak ada batas atas
    x_overflow = pulp.LpVariable("x_overflow", lowBound=0)
    
    # Constraint: total limbah harus dialokasikan antara treatment yang dipilih dan overflow
    prob += (pulp.lpSum([x[t] for t in selected_treatments]) + x_overflow == total_waste), "TotalWaste"
    
    # Parameter penalti (asumsi, sesuaikan dengan data aktual)
    penalty_cost = 5000     # Biaya per kg untuk overflow (treatment alternatif)
    penalty_emission = 5.0  # Emisi per kg untuk overflow
    
    # Constraint: Total biaya tidak boleh melebihi budget
    prob += (pulp.lpSum([treatment_data[t]['cost'] * x[t] for t in selected_treatments]) + penalty_cost * x_overflow 
             <= total_budget), "BudgetConstraint"
    
    # Fungsi objektif: minimisasi total emisi
    prob += (pulp.lpSum([treatment_data[t]['emission'] * x[t] for t in selected_treatments]) 
             + penalty_emission * x_overflow), "TotalEmissions"
    
    prob.solve()
    
    status = pulp.LpStatus[prob.status]
    allocation = {t: x[t].varValue for t in selected_treatments}
    overflow_value = x_overflow.varValue
    total_emissions = pulp.value(prob.objective)
    total_cost = sum(treatment_data[t]['cost'] * allocation[t] for t in selected_treatments) + penalty_cost * overflow_value
    
    return status, allocation, overflow_value, total_emissions, total_cost

def main():
    st.title("Waste Treatment Optimization System")
    st.write("Masukkan data limbah, treatment, transportasi, dan informasi lainnya.")
    
    # --- Input Data Limbah ---
    st.header("Input Data Limbah")
    waste_options = [
        "Paper",
        "Cardboard",
        "Plastic",
        "Glass",
        "Metal Scrap",
        "Household Waste"
    ]
    
    if "waste_entries" not in st.session_state:
        st.session_state["waste_entries"] = []
    
    col1, col2 = st.columns(2)
    with col1:
        selected_waste_type = st.selectbox("Pilih Tipe Limbah", waste_options)
    with col2:
        waste_weight = st.number_input("Berat Limbah (kg)", min_value=0.0, step=1.0, key="waste_weight")
    
    if st.button("Add Waste"):
        st.session_state["waste_entries"].append({
            "waste_type": selected_waste_type, 
            "weight": waste_weight
        })
        st.success(f"Added {selected_waste_type} dengan berat {waste_weight} kg")
    
    st.subheader("Data Limbah yang Ditambahkan:")
    if st.session_state["waste_entries"]:
        for idx, entry in enumerate(st.session_state["waste_entries"]):
            colA, colB, colC = st.columns([3, 2, 1])
            with colA:
                st.write(f"{entry['waste_type']} : {entry['weight']} kg")
            with colC:
                if st.button("Remove", key=f"remove_waste_{idx}"):
                    st.session_state["waste_entries"].pop(idx)
                    if hasattr(st, "experimental_rerun"):
                        st.experimental_rerun()
    else:
        st.write("Belum ada data limbah yang ditambahkan.")
    
    total_waste = sum([entry['weight'] for entry in st.session_state["waste_entries"]])
    
    # --- Input Treatment ---
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
    
    # Data contoh untuk tiap treatment (sesuaikan dengan data aktual)
    treatment_data = {
        "Sanitary Landfill": {"emission": 0.3, "cost": 1000, "capacity": 1000},
        "Incineration": {"emission": 1.0, "cost": 2000, "capacity": 800},
        "Unsanitary Landfill": {"emission": 0.5, "cost": 500, "capacity": 1500},
        "Open Burning": {"emission": 2.0, "cost": 300, "capacity": 700},
        "Open Dump": {"emission": 0.4, "cost": 200, "capacity": 2000},
        "Recycle": {"emission": 0.1, "cost": 1500, "capacity": 500},
        "Reuse": {"emission": 0.05, "cost": 1200, "capacity": 600}
    }
    
    # --- Input Data Transportasi (Opsional) ---
    st.header("Input Data Transportasi (Opsional)")
    st.write("Jika limbah akan diangkut menggunakan transportasi menuju fasilitas pengolahan limbah, tambahkan data transportasi di bawah ini.")
    
    if "transport_entries" not in st.session_state:
        st.session_state["transport_entries"] = []
    
    transport_options = [
        "Heavy-duty truck",
        "Medium-duty Truck",
        "Tossa Motor",
        "Pickup"
    ]
    
    col3, col4 = st.columns(2)
    with col3:
        selected_transport_type = st.selectbox("Pilih Jenis Transportasi", transport_options, key="transport_type")
    with col4:
        travel_distance = st.number_input("Travel Distance (Km)", min_value=0.0, step=1.0, key="travel_distance")
    
    if st.button("Add Transportation"):
        st.session_state["transport_entries"].append({
            "transport_type": selected_transport_type,
            "travel_distance": travel_distance
        })
        st.success(f"Added {selected_transport_type} dengan jarak {travel_distance} Km")
    
    st.subheader("Data Transportasi yang Ditambahkan:")
    if st.session_state["transport_entries"]:
        for idx, entry in enumerate(st.session_state["transport_entries"]):
            colX, colY, colZ = st.columns([3, 2, 1])
            with colX:
                st.write(f"{entry['transport_type']} : {entry['travel_distance']} Km")
            with colZ:
                if st.button("Remove", key=f"remove_transport_{idx}"):
                    st.session_state["transport_entries"].pop(idx)
                    if hasattr(st, "experimental_rerun"):
                        st.experimental_rerun()
    else:
        st.write("Belum ada data transportasi yang ditambahkan.")
    
    # --- Input Total Budget ---
    st.header("Input Total Budget")
    total_budget = st.number_input("Total Budget Yang Dimiliki (dalam Rupiah)", min_value=0.0, step=1.0, key="total_budget")
    st.caption("Masukkan total budget perusahaan dalam satuan Rupiah.")
    
    # --- Submit dan Optimasi ---
    if st.button("Submit dan Optimasi"):
        st.subheader("Data yang Dimasukkan:")
        if st.session_state["waste_entries"]:
            st.write("Data Limbah:")
            for entry in st.session_state["waste_entries"]:
                st.write(f"{entry['waste_type']} : {entry['weight']} kg")
        else:
            st.write("Tidak ada data limbah yang ditambahkan.")
        
        st.write("Treatment yang Dipilih:", selected_treatments)
        
        if st.session_state["transport_entries"]:
            st.write("Data Transportasi:")
            for entry in st.session_state["transport_entries"]:
                st.write(f"{entry['transport_type']} : {entry['travel_distance']} Km")
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
            selected_treatment_data = {t: treatment_data[t] for t in selected_treatments}
            
            status, allocation, overflow_value, total_emissions, total_cost = optimize_treatment(
                total_waste, total_budget, selected_treatments, selected_treatment_data
            )
            
            st.subheader("Hasil Optimasi")
            st.write("Status Solusi:", status)
            if status == "Optimal":
                st.write("Alokasi Limbah per Treatment:")
                for t, value in allocation.items():
                    st.write(f"{t} : {value:.2f} kg")
                if overflow_value > 0:
                    st.write(f"Overflow (dialihkan ke treatment alternatif): {overflow_value:.2f} kg")
                st.write("Total Emisi CO₂:", total_emissions, "satuan")
                st.write("Total Biaya:", total_cost, "Rupiah")
            else:
                st.error("Solusi optimal tidak ditemukan. Periksa kembali input dan constraint yang diberikan.")

if __name__ == "__main__":
    main()
