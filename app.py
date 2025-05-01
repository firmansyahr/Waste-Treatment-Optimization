import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

# Optimization function
def optimize_waste(user_df: pd.DataFrame, max_budget: float, origin_coords: tuple):
    # Default Quantity if missing
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0

    treatments_df      = data.treatments_df
    transport_df       = data.transport_df
    locations_df       = data.locations_df
    capacity_df        = data.facility_capacity_df
    facility_rules     = data.facility_rules

    # Merge facility capacity with coords
    facility_df = (
        capacity_df.merge(locations_df, on='Facility_ID')
                   .rename(columns={'Capacity': 'Max_Capacity'})
    )

    # Define LP model
    model = pulp.LpProblem("Waste_Optimization", pulp.LpMinimize)
    decision_vars = {}

    # Create vars and demand constraints
    for _, row in user_df.iterrows():
        item     = row['Waste_Item']
        category = row['Category']
        qty      = float(row['Quantity'])

        for _, t in treatments_df[treatments_df['Category']==category].iterrows():
            tr         = t['Treatment']
            em_factor  = float(t['Emission_Factor'])
            tr_cost    = float(t['Treatment_Cost'])

            for fid, rules in facility_rules.items():
                if (category in rules['Category']) and (tr in rules['Treatment']):
                    fac = facility_df[
                        (facility_df['Facility_ID']==fid) &
                        (facility_df['Treatment']==tr)
                    ]
                    if fac.empty:
                        continue
                    cap    = float(fac['Max_Capacity'].iloc[0])
                    coords = (
                        float(fac['Latitude'].iloc[0]),
                        float(fac['Longitude'].iloc[0])
                    )

                    var = pulp.LpVariable(f"x_{item}_{tr}_{fid}", lowBound=0, upBound=qty)
                    decision_vars[(item,tr,fid)] = {
                        'var': var,
                        'em_factor': em_factor,
                        'tr_cost': tr_cost,
                        'capacity': cap,
                        'coords': coords
                    }

        # Demand constraint: sum allocations == qty
        model += (
            pulp.lpSum(v['var'] for (it,_,_), v in decision_vars.items() if it==item)
            == qty,
            f"Demand_{item}"
        )

    # Objective: minimize emissions including transport distance
    obj_terms = []
    for (item,tr,fid), props in decision_vars.items():
        var = props['var']
        possible = transport_df[transport_df['Max_Capacity'] >= var.upBound]
        if possible.empty:
            possible = transport_df
        best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]

        dist_km = geodesic(origin_coords, props['coords']).km
        trans_em_total = best['Emission_per_ton'] * dist_km
        obj_terms.append(var * (props['em_factor'] + trans_em_total))
    model += pulp.lpSum(obj_terms), "Total_Emission"

    # Budget constraint: treatment + transport cost by distance
    cost_terms = []
    for (item,tr,fid), props in decision_vars.items():
        var = props['var']
        possible = transport_df[transport_df['Max_Capacity'] >= var.upBound]
        if possible.empty:
            possible = transport_df
        best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]

        dist_km = geodesic(origin_coords, props['coords']).km
        trans_cost_total = best.get('Cost_per_ton', 0.0) * dist_km
        cost_terms.append(var * (props['tr_cost'] + trans_cost_total))
    model += pulp.lpSum(cost_terms) <= max_budget, "Budget_Constraint"

    # Solve
    model.solve()

    # Collect results
    results = []
    for (item,tr,fid), props in decision_vars.items():
        amt = props['var'].varValue
        if amt and amt > 0:
            possible = transport_df[transport_df['Max_Capacity'] >= amt]
            if possible.empty:
                possible = transport_df
            best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]

            dist_km = geodesic(origin_coords, props['coords']).km
            trans_em_total = best['Emission_per_ton'] * dist_km
            trans_cost_total = best.get('Cost_per_ton', 0.0) * dist_km

            results.append({
                'Waste_Item': item,
                'Treatment': tr,
                'Facility_ID': fid,
                'Amount': amt,
                'Treatment_Emission': props['em_factor'],
                'Transport_Mode': best['Mode'],
                'Distance_km': round(dist_km, 2),
                'Transport_Emission_Total': trans_em_total,
                'Cost_Treatment': props['tr_cost'],
                'Transport_Cost_Total': trans_cost_total,
                'Total_Emission': amt * (props['em_factor'] + trans_em_total),
                'Total_Cost': amt * (props['tr_cost'] + trans_cost_total)
            })
    df = pd.DataFrame(results)
    return df, df['Total_Emission'].sum(), df['Total_Cost'].sum()


# Streamlit UI
def main():
    st.title("Waste Treatment Optimization App")
    st.markdown("Upload Excel dengan kolom: Waste_Item, Category, (opsional) Quantity.")

    uploaded = st.file_uploader("Pilih file Excel...", type=["xlsx","xls"])
    max_budget = st.number_input("Maksimal Budget (Rp)", min_value=0.0, step=1000.0)

    st.subheader("Lokasi Asal Limbah")
    origin_lat = st.number_input("Latitude", value=float(data.locations_df['Latitude'].mean()))
    origin_lon = st.number_input("Longitude", value=float(data.locations_df['Longitude'].mean()))
    origin_coords = (origin_lat, origin_lon)

    if uploaded and max_budget > 0:
        user_df = pd.read_excel(uploaded)
        if st.button("Jalankan Optimasi"):
            with st.spinner("Mengoptimalkan..."):
                res_df, tot_em, tot_ct = optimize_waste(user_df, max_budget, origin_coords)
            st.subheader("Hasil Optimasi")
            st.write(f"**Total Emisi:** {tot_em:.2f} kg CO₂")
            st.write(f"**Total Biaya:** Rp {tot_ct:,.2f}")
            st.dataframe(res_df)
            csv = res_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "results.csv", "text/csv")

if __name__ == "__main__":
    main()
