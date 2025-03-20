import streamlit as st
import pandas as pd
import pulp

# Data emisi dan biaya treatment (Rp/kg) sebagai list of dictionaries
emission_data = [
    # Paper
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Paper", "Treatment": "Sanitary Landfill", "Emission Factor": 1.4270046, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Paper", "Treatment": "Incineration", "Emission Factor": 1.5121828, "Database": "Ecoinvent 3.10", "Treatment Cost": 1000},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Paper", "Treatment": "Recycle", "Emission Factor": 0.096969806, "Database": "Ecoinvent 3.10", "Treatment Cost": -200},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Paper", "Treatment": "Open Burning", "Emission Factor": 1.6045562, "Database": "Ecoinvent 3.10", "Treatment Cost": 0},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Paper", "Treatment": "Open Dump", "Emission Factor": 1.8941032, "Database": "Ecoinvent 3.10", "Treatment Cost": 300},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Paper", "Treatment": "Unsanitary Landfill", "Emission Factor": 2.5272223, "Database": "Ecoinvent 3.10", "Treatment Cost": 400},
    # Cardboard
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cardboard", "Treatment": "Sanitary Landfill", "Emission Factor": 1.8311121, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cardboard", "Treatment": "Incineration", "Emission Factor": 1.612536, "Database": "Ecoinvent 3.10", "Treatment Cost": 1000},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cardboard", "Treatment": "Unsanitary Landfill", "Emission Factor": 4.8095221, "Database": "Ecoinvent 3.10", "Treatment Cost": 400},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cardboard", "Treatment": "Open Dump", "Emission Factor": 3.6076679, "Database": "Ecoinvent 3.10", "Treatment Cost": 300},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cardboard", "Treatment": "Open Burning", "Emission Factor": 2.4673562, "Database": "Ecoinvent 3.10", "Treatment Cost": 0},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cardboard", "Treatment": "Recycle", "Emission Factor": 0.13406205, "Database": "Ecoinvent 3.10", "Treatment Cost": -200},
    # Plastic
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Plastic", "Treatment": "Incineration", "Emission Factor": 2.3799497, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Plastic", "Treatment": "Sanitary Landfill", "Emission Factor": 0.093376204, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Plastic", "Treatment": "Open Burning", "Emission Factor": 2.4421563, "Database": "Ecoinvent 3.10", "Treatment Cost": 0},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Plastic", "Treatment": "Open Dump", "Emission Factor": 0.11001912, "Database": "Ecoinvent 3.10", "Treatment Cost": 300},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Plastic", "Treatment": "Unsanitary Landfill", "Emission Factor": 0.15137911, "Database": "Ecoinvent 3.10", "Treatment Cost": 400},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Plastic", "Treatment": "Recycle", "Emission Factor": 0.32484773, "Database": "Ecoinvent 3.10", "Treatment Cost": -300},
    # Glass
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Glass", "Treatment": "Incineration", "Emission Factor": 0.029362056, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Glass", "Treatment": "Sanitary Landfill", "Emission Factor": 0.011295458, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Glass", "Treatment": "Open Burning", "Emission Factor": 0.20755625, "Database": "Ecoinvent 3.10", "Treatment Cost": 0},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Glass", "Treatment": "Open Dump", "Emission Factor": 0.0, "Database": "Ecoinvent 3.10", "Treatment Cost": 300},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Glass", "Treatment": "Unsanitary Landfill", "Emission Factor": 0.0048642436, "Database": "Ecoinvent 3.10", "Treatment Cost": 400},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Glass", "Treatment": "Recycle", "Emission Factor": 0.0094020212, "Database": "Ecoinvent 3.10", "Treatment Cost": -100},
    # Metal Scrap
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Metal Scrap", "Treatment": "Sanitary Landfill", "Emission Factor": 0.0062589514, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Metal Scrap", "Treatment": "Incineration", "Emission Factor": 0.033904942, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Metal Scrap", "Treatment": "Recycle", "Emission Factor": 0.062741046, "Database": "Ecoinvent 3.10", "Treatment Cost": -1000},
    # Household Waste
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Household Waste", "Treatment": "Incineration", "Emission Factor": 1.2460356, "Database": "Ecoinvent 3.10", "Treatment Cost": 1000},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Household Waste", "Treatment": "Sanitary Landfill", "Emission Factor": 0.74235224, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Household Waste", "Treatment": "Unsanitary Landfill", "Emission Factor": 1.3054325, "Database": "Ecoinvent 3.10", "Treatment Cost": 400},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Household Waste", "Treatment": "Open Burning", "Emission Factor": 1.3354462, "Database": "Ecoinvent 3.10", "Treatment Cost": 0},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Household Waste", "Treatment": "Open Dump", "Emission Factor": 0.97663096, "Database": "Ecoinvent 3.10", "Treatment Cost": 300},
    # Gypsump Plasterboard
    {"Category": "Hazardous Waste", "Type of Waste": "Gypsump Plasterboard", "Treatment": "Recycle", "Emission Factor": 0.0035980898, "Database": "Ecoinvent 3.10", "Treatment Cost": -500},
    {"Category": "Hazardous Waste", "Type of Waste": "Gypsump Plasterboard", "Treatment": "Sanitary Landfill", "Emission Factor": 0.035293422, "Database": "Ecoinvent 3.10", "Treatment Cost": 800},
    # Sludge
    {"Category": "Hazardous Waste", "Type of Waste": "Sludge", "Treatment": "Sanitary Landfill", "Emission Factor": 0.68407718, "Database": "Ecoinvent 3.10", "Treatment Cost": 1000},
    {"Category": "Hazardous Waste", "Type of Waste": "Sludge", "Treatment": "Incineration", "Emission Factor": 2.3036841, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    {"Category": "Hazardous Waste", "Type of Waste": "Sludge", "Treatment": "Energy Recovery", "Emission Factor": 2.3036841, "Database": "Ecoinvent 3.10", "Treatment Cost": 2000},
    # Paint
    {"Category": "Hazardous Waste", "Type of Waste": "Paint", "Treatment": "Sanitary Landfill", "Emission Factor": 0.09514224, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    {"Category": "Hazardous Waste", "Type of Waste": "Paint", "Treatment": "Incineration", "Emission Factor": 3.6305226, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    {"Category": "Hazardous Waste", "Type of Waste": "Paint", "Treatment": "Energy Recovery", "Emission Factor": 3.6305226, "Database": "Ecoinvent 3.10", "Treatment Cost": 2500},
    # Wood
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wood", "Treatment": "Sanitary Landfill", "Emission Factor": 0.08890813, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wood", "Treatment": "Incineration", "Emission Factor": 1.4786935, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wood", "Treatment": "Open Burning", "Emission Factor": 1.5953562, "Database": "Ecoinvent 3.10", "Treatment Cost": 0},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wood", "Treatment": "Open Dump", "Emission Factor": 0.10456916, "Database": "Ecoinvent 3.10", "Treatment Cost": 300},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wood", "Treatment": "Unsanitary Landfill", "Emission Factor": 0.14411984, "Database": "Ecoinvent 3.10", "Treatment Cost": 400},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wood", "Treatment": "Energy Recovery", "Emission Factor": 1.9432214, "Database": "Ecoinvent 3.10", "Treatment Cost": 2000},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wood", "Treatment": "Recycle", "Emission Factor": 0.051146157, "Database": "Ecoinvent 3.10", "Treatment Cost": -300},
    # Cement
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cement", "Treatment": "Sanitary Landfill", "Emission Factor": 0.007101107, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cement", "Treatment": "Recycle", "Emission Factor": 0.0035980898, "Database": "Ecoinvent 3.10", "Treatment Cost": -200},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Cement", "Treatment": "Incineration", "Emission Factor": 0.54191804, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    # Concrete
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Concrete", "Treatment": "Sanitary Landfill", "Emission Factor": 0.0062589516, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Concrete", "Treatment": "Recycle", "Emission Factor": 0.004379848, "Database": "Ecoinvent 3.10", "Treatment Cost": -100},
    # Wool
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wool", "Treatment": "Sanitary Landfill", "Emission Factor": 0.0062589514, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Wool", "Treatment": "Recycle", "Emission Factor": 0.032774278, "Database": "Ecoinvent 3.10", "Treatment Cost": -300},
    # Biowaste
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Biowaste", "Treatment": "Open Dump", "Emission Factor": 0.664828, "Database": "Ecoinvent 3.10", "Treatment Cost": 300},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Biowaste", "Treatment": "Industrial Composting", "Emission Factor": 0.28482961, "Database": "Ecoinvent 3.10", "Treatment Cost": 500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Biowaste", "Treatment": "Anaerobic Digestion", "Emission Factor": 0.33502074, "Database": "Ecoinvent 3.10", "Treatment Cost": 1000},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Biowaste", "Treatment": "Incineration", "Emission Factor": 0.55695052, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    # Electronic Waste
    {"Category": "Hazardous Waste", "Type of Waste": "Electronic Waste", "Treatment": "Open Burning", "Emission Factor": 0.89122624, "Database": "Ecoinvent 3.10", "Treatment Cost": 0},
    {"Category": "Hazardous Waste", "Type of Waste": "Electronic Waste", "Treatment": "Sanitary Landfill", "Emission Factor": 0.11764956, "Database": "Ecoinvent 3.10", "Treatment Cost": 1000},
    {"Category": "Hazardous Waste", "Type of Waste": "Electronic Waste", "Treatment": "Unsanitary Landfill", "Emission Factor": 0.19471437, "Database": "Ecoinvent 3.10", "Treatment Cost": 400},
    {"Category": "Hazardous Waste", "Type of Waste": "Electronic Waste", "Treatment": "Recycle", "Emission Factor": 0.34607495, "Database": "Ecoinvent 3.10", "Treatment Cost": -1500},
    # Other Hazardous Waste
    {"Category": "Hazardous Waste", "Type of Waste": "Other Hazardous Waste", "Treatment": "Incineration", "Emission Factor": 2.5239282, "Database": "Ecoinvent 3.10", "Treatment Cost": 2000},
    {"Category": "Hazardous Waste", "Type of Waste": "Other Hazardous Waste", "Treatment": "Energy Recovery", "Emission Factor": 2.5239282, "Database": "Ecoinvent 3.10", "Treatment Cost": 2500},
    {"Category": "Hazardous Waste", "Type of Waste": "Other Hazardous Waste", "Treatment": "Sanitary Landfill", "Emission Factor": 0.18600296, "Database": "Ecoinvent 3.10", "Treatment Cost": 1000},
    # Textile
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Textile", "Treatment": "Incineration", "Emission Factor": 1.6655581, "Database": "Ecoinvent 3.10", "Treatment Cost": 1500},
    {"Category": "Non-Hazardous Waste", "Type of Waste": "Textile", "Treatment": "Unsanitary Landfill", "Emission Factor": 1.1652431, "Database": "Ecoinvent 3.10", "Treatment Cost": 400},
]

# Fungsi model optimisasi menggunakan data emisi di atas
def run_optimization(waste_data, metrics, third_party_options=None):
    # Konversi data emisi ke DataFrame
    df_emission = pd.DataFrame(emission_data)

    # Buat model optimisasi dengan tujuan minimisasi total emisi
    prob = pulp.LpProblem("Waste_Treatment_Optimization", pulp.LpMinimize)
    cost_terms = []
    emission_terms = []
    allocation_details = []  # Untuk menyimpan detail alokasi tiap variabel keputusan

    # Iterasi setiap record limbah yang diinput
    for i, record in enumerate(waste_data):
        cat = record["Category"]
        typ = record["Type of Waste"]
        amount = record["Amount"]
        unit = record["Unit"]

        # Konversi jumlah limbah ke satuan kg
        if unit.lower() == "g":
            amount_kg = amount / 1000
        elif unit.lower() == "ton":
            amount_kg = amount * 1000
        else:
            amount_kg = amount

        # Opsi treatment yang diperbolehkan berdasarkan dictionary allowed_treatments
        allowed = allowed_treatments.get(cat, {}).get(typ, [])
        # Filter data emisi berdasarkan Category, Type of Waste, dan opsi Treatment yang diizinkan
        df_filtered = df_emission[
            (df_emission["Category"] == cat) &
            (df_emission["Type of Waste"] == typ) &
            (df_emission["Treatment"].isin(allowed))
        ]

        if df_filtered.empty:
            st.warning(f"Tidak ditemukan data emisi untuk limbah {cat} - {typ}. Record dilewati.")
            continue

        # Buat variabel keputusan untuk tiap opsi treatment pada record ini
        vars_i = {}
        for idx, row in df_filtered.iterrows():
            treatment = row["Treatment"]
            var_name = f"x_{i}_{treatment.replace(' ', '_')}"
            vars_i[treatment] = pulp.LpVariable(var_name, lowBound=0, cat="Continuous")
            cost_terms.append(row["Treatment Cost"] * vars_i[treatment])
            emission_terms.append(row["Emission Factor"] * vars_i[treatment])
            allocation_details.append({
                "Waste Record": i,
                "Category": cat,
                "Type of Waste": typ,
                "Treatment": treatment,
                "Emission Factor": row["Emission Factor"],
                "Cost per kg": row["Treatment Cost"],
                "Decision Var": vars_i[treatment]
            })
        # Constraint: jumlah alokasi harus sama dengan total limbah (kg)
        prob += pulp.lpSum(vars_i.values()) == amount_kg, f"waste_balance_{i}"

    # Constraint: total biaya tidak boleh melebihi batas perusahaan
    if "Biaya Maksimal Perusahaan" in metrics:
        company_cost = metrics["Biaya Maksimal Perusahaan"]
        prob += pulp.lpSum(cost_terms) <= company_cost, "company_cost_constraint"

    # Fungsi objektif: minimisasi total emisi
    prob += pulp.lpSum(emission_terms), "Total_Emissions"

    # Selesaikan model
    prob.solve()
    status = pulp.LpStatus[prob.status]
    total_emission = pulp.value(prob.objective)
    total_cost = pulp.value(pulp.lpSum(cost_terms))

    # Ambil hasil alokasi solusi
    allocation_result = []
    for detail in allocation_details:
        allocated_amount = pulp.value(detail["Decision Var"])
        if allocated_amount is not None and allocated_amount > 1e-6:
            allocation_result.append({
                "Waste Record": detail["Waste Record"],
                "Category": detail["Category"],
                "Type of Waste": detail["Type of Waste"],
                "Treatment": detail["Treatment"],
                "Allocated (kg)": allocated_amount,
                "Emission Factor": detail["Emission Factor"],
                "Cost per kg": detail["Cost per kg"],
                "Emissions (kg CO2 eq)": detail["Emission Factor"] * allocated_amount,
                "Cost (Rp)": detail["Cost per kg"] * allocated_amount
            })

    result = {
        "Status": status,
        "Total Emissions (kg CO2 eq)": total_emission,
        "Total Cost (Rp)": total_cost,
        "Allocation": allocation_result
    }
    return result

# Fungsi utama aplikasi Streamlit
def main():
    st.title("Waste Treatment Optimization")

    # Inisialisasi session state
    if "waste_data" not in st.session_state:
        st.session_state.waste_data = []
    if "metrics" not in st.session_state:
        st.session_state.metrics = {}

    # --- STEP 1: Input Data Limbah ---
    st.header("Step 1: Input Data Limbah")
    with st.form(key="waste_form"):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            waste_category = st.selectbox("Category", ["Non-Hazardous Waste", "Hazardous Waste"])
        if waste_category == "Non-Hazardous Waste":
            waste_types = ["Paper", "Cardboard", "Plastic", "Glass", "Metal Scrap", "Household Waste", "Wood", "Cement", "Concrete", "Wool", "Biowaste", "Textile"]
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
            "Allowed Treatments": ", ".join(allowed_treatments.get(waste_category, {}).get(selected_waste_type, []))
        }
        st.session_state.waste_data.append(new_waste)
        st.success("Data limbah berhasil ditambahkan!")

    if st.session_state.waste_data:
        st.subheader("Daftar Limbah yang Telah Ditambahkan")
        df = pd.DataFrame(st.session_state.waste_data)
        df_style = df.style.set_properties(subset=["Allowed Treatments"], **{"width": "30%"})
        st.dataframe(df_style, use_container_width=True)

    # --- STEP 2: Input Metrik Lainnya ---
    st.header("Step 2: Input Metrik Lainnya")
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
    st.header("Step 3: Third Party Pengelola Limbah (Optional)")
    include_third_party = st.checkbox("Include Third Party Pengelola Limbah")
    third_party_options = None
    if include_third_party:
        st.subheader("Input Lokasi Third Party")
        col_tp = st.columns(3)
        tp_name = col_tp[0].text_input("Third Party Name", key="tp_name")
        third_party_lat = col_tp[1].number_input("Latitude", format="%.6f", key="tp_lat")
        third_party_long = col_tp[2].number_input("Longitude", format="%.6f", key="tp_long")
        st.subheader("Non-Hazardous Waste Options")
        non_hazardous_options = ["Sanitary Landfill", "Incineration", "Recycle", "Open Burning", "Open Dump", "Unsanitary Landfill", "Energy Recovery", "Industrial Composting", "Anaerobic Digestion"]
        third_party_non_hazardous = {}
        for i in range(0, len(non_hazardous_options), 2):
            cols = st.columns(2)
            for j, option in enumerate(non_hazardous_options[i:i+2]):
                third_party_non_hazardous[option] = cols[j].number_input(f"{option} (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0, key=f"np_{option}")
        st.subheader("Hazardous Waste Options")
        hazardous_options = ["Sanitary Landfill", "Incineration", "Recycle", "Open Burning", "Open Dump", "Unsanitary Landfill", "Energy Recovery"]
        third_party_hazardous = {}
        for i in range(0, len(hazardous_options), 2):
            cols = st.columns(2)
            for j, option in enumerate(hazardous_options[i:i+2]):
                third_party_hazardous[option] = cols[j].number_input(f"{option} (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0, key=f"hp_{option}")
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
        result = run_optimization(
            st.session_state.get("waste_data", []),
            st.session_state.get("metrics", {}),
            third_party_options
        )
        if result:
            st.subheader("Hasil Optimisasi")
            st.write("Status:", result["Status"])
            st.write("Total Emissions (kg CO2 eq):", result["Total Emissions (kg CO2 eq)"])
            st.write("Total Cost (Rp):", result["Total Cost (Rp)"])
            if result["Allocation"]:
                allocation_df = pd.DataFrame(result["Allocation"])
                st.dataframe(allocation_df)
            else:
                st.write("Tidak ada alokasi (mungkin data limbah tidak sesuai dengan data emisi).")

if __name__ == '__main__':
    main()
