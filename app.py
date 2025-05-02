import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

# Streamlit app using kilograms (kg) as unit for all quantities

def optimize_waste(user_df: pd.DataFrame, max_budget: float, origin_coords: tuple):
    # Ensure Quantity column exists (in kg)
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0  # default 1 kg if missing

    # 1) Load static data and convert to kg-based units
    treatments_df = data.treatments_df.copy()
    transport_df  = data.transport_df.copy()
    locations_df  = data.locations_df
    capacity_df   = data.facility_capacity_df.copy()
    facility_rules = data.facility_rules
    max_prop_df   = data.max_prop_df

    # Convert treatment factors from per ton to per kg
    treatments_df['Emission_Factor'] = treatments_df['Emission_Factor'] / 1000.0  # kgCO2 per kg
    treatments_df['Treatment_Cost']    = treatments_df['Treatment_Cost']    / 1000.0  # Rp per kg

    # Convert transport factors from per ton to per kg, capacities to kg
    transport_df['Emission_per_kg'] = transport_df['Emission_per_ton'] / 1000.0  # kgCO2 per kg-km
    transport_df['Cost_per_kg']      = transport_df.get('Cost_per_ton', 0.0) / 1000.0  # Rp per kg-km
    transport_df['Max_Capacity']     = transport_df['Max_Capacity'] * 1000.0      # kg

    # Convert facility capacities from tons to kg
    capacity_df['Capacity'] = capacity_df['Capacity'] * 1000.0  # kg

    # Merge capacity with coordinates
    facility_df = (
        capacity_df
        .merge(locations_df, on='Facility_ID')
        .rename(columns={'Capacity':'Max_Capacity'})
    )

    # 2) Build LP model
    model = pulp.LpProblem("Waste_Optimization_kg", pulp.LpMinimize)
    decision_vars = {}

    # 3) Demand constraints and decision variables
    for idx, row in user_df.iterrows():
        item     = row['Waste_Item']
        category = row['Category']
        qty      = float(row['Quantity'])  # in kg

        # Only treatments defined for this Waste_Item + Category
        applicable = treatments_df[
            (treatments_df['Waste_Item']==item) &
            (treatments_df['Category']==category)
        ]
        for _, t in applicable.iterrows():
            tr        = t['Treatment']
            em_factor = float(t['Emission_Factor'])  # per kg
            tr_cost   = float(t['Treatment_Cost'])    # per kg

            # Only facilities that accept this comb.
            for fid, rules in facility_rules.items():
                if category in rules['Category'] and tr in rules['Treatment']:
                    fac = facility_df[
                        (facility_df['Facility_ID']==fid) &
                        (facility_df['Treatment']==tr)
                    ]
                    if fac.empty:
                        continue
                    coords = (
                        float(fac['Latitude'].iloc[0]),
                        float(fac['Longitude'].iloc[0])
                    )
                    var = pulp.LpVariable(f"x_{idx}_{item}_{tr}_{fid}", lowBound=0, upBound=qty)
                    decision_vars[(idx,item,tr,fid)] = {
                        'var': var,
                        'category': category,
                        'treatment': tr,
                        'em_factor': em_factor,
                        'tr_cost': tr_cost,
                        'coords': coords
                    }
        # Demand: sum of allocations for this row == qty
        model += (
            pulp.lpSum(v['var'] for (i,it,tt,f), v in decision_vars.items() if i==idx)
            == qty,
            f"Demand_{idx}"
        )

    # 4) Max-proportion constraints (per category-treatment)
    total_by_cat = user_df.groupby('Category')['Quantity'].sum().to_dict()
    for _, mp in max_prop_df.iterrows():
        cat = mp['Category']
        trt = mp['Treatment']
        prop = float(mp['Max_Proportion'])
        if cat not in total_by_cat:
            continue
        cap = prop * total_by_cat[cat]  # in kg
        vars_for = [v['var'] for v in decision_vars.values()
                    if v['category']==cat and v['treatment']==trt]
        if vars_for:
            model += (
                pulp.lpSum(vars_for) <= cap,
                f"MaxProp_{cat.replace(' ','')}_{trt.replace(' ','')}"
            )

    # 5) Facility capacity constraints
    for fid in facility_df['Facility_ID'].unique():
        cap = float(
            facility_df.loc[facility_df['Facility_ID']==fid, 'Max_Capacity'].iloc[0]
        )  # in kg
        vars_at_fid = [v['var'] for (i,it,tt,f), v in decision_vars.items() if f==fid]
        if vars_at_fid:
            model += (
                pulp.lpSum(vars_at_fid) <= cap,
                f"Cap_{fid}"
            )

    # 6) Objective: minimize total emissions (treatment + transport)
    obj_terms = []
    for props in decision_vars.values():
        var = props['var']
        poss = transport_df[transport_df['Max_Capacity'] >= var.upBound]
        if poss.empty:
            poss = transport_df
        best = poss.nsmallest(1, 'Emission_per_kg').iloc[0]
        dist_km = geodesic(origin_coords, props['coords']).km
        # emission per kg-km * distance + treatment per kg
        obj_terms.append(var * (props['em_factor'] + best['Emission_per_kg'] * dist_km))
    model += pulp.lpSum(obj_terms), "Total_Emission"

    # 7) Budget constraint: treatment + transport cost
    cost_terms = []
    for props in decision_vars.values():
        var = props['var']
        poss = transport_df[transport_df['Max_Capacity'] >= var.upBound]
        if poss.empty:
            poss = transport_df
        best = poss.nsmallest(1, 'Cost_per_kg').iloc[0]
        dist_km = geodesic(origin_coords, props['coords']).km
        cost_terms.append(var * (props['tr_cost'] + best['Cost_per_kg'] * dist_km))
    model += (
        pulp.lpSum(cost_terms) <= max_budget,
        "Budget_Constraint"
    )

    # 8) Solve and get status
    status_code = model.solve()
    status = pulp.LpStatus.get(status_code, 'Unknown')

    # 9) Collect results
    results = []
    for (idx,item,tr,fid), props in decision_vars.items():
        amt = props['var'].varValue or 0
        if amt > 1e-6:
            tpa = data.locations_df.loc[
                data.locations_df['Facility_ID']==fid, 'Location'
            ].iloc[0]
            poss = transport_df[transport_df['Max_Capacity'] >= amt]
            if poss.empty:
                poss = transport_df
            best = poss.nsmallest(1, 'Emission_per_kg').iloc[0]
            dist_km = geodesic(origin_coords, props['coords']).km
            results.append({
                'Waste_Item': item,
                'Category': props['category'],
                'Treatment': props['treatment'],
                'TPA_Name': tpa,
                'Amount_kg': round(amt, 6),
                'Treatment_Emission_kgCO2_per_kg': props['em_factor'],
                'Transport_Mode': best['Mode'],
                'Distance_km': round(dist_km, 2),
                'Transport_Emission_kgCO2': best['Emission_per_kg'] * dist_km * amt,
                'Cost_Treatment_Rp': props['tr_cost'] * amt,
                'Cost_Transport_Rp': best['Cost_per_kg'] * dist_km * amt,
                'Total_Emission_kgCO2': amt * (props['em_factor'] + best['Emission_per_kg'] * dist_km),
                'Total_Cost_Rp': amt * (props['tr_cost'] + best['Cost_per_kg'] * dist_km)
            })
    df = pd.DataFrame(results)
    return df, df['Total_Emission_kgCO2'].sum(), df['Total_Cost_Rp'].sum(), status

# Streamlit UI

def main():
    st.title("Waste Treatment Optimization (Units: kg)")
    st.markdown("**Upload Excel** with columns: Waste_Item, Category, Quantity (in kg).")

    uploaded = st.file_uploader("Choose Excel...", type=["xlsx", "xls"])
    max_budget = st.number_input("Maximal Budget (Rp)", value=0.0, step=1000.0)

    st.subheader("Origin Coordinates")
    origin_lat = st.number_input("Latitude", value=float(data.locations_df['Latitude'].mean()))
    origin_lon = st.number_input("Longitude", value=float(data.locations_df['Longitude'].mean()))
    origin_coords = (origin_lat, origin_lon)

    if uploaded and max_budget > 0:
        user_df = pd.read_excel(uploaded, engine='openpyxl')
        if st.button("Run Optimization"):
            with st.spinner("Optimizing..."):
                res_df, tot_em, tot_ct, status = optimize_waste(user_df, max_budget, origin_coords)
            st.subheader(f"Status: {status}")
            st.write(f"**Total Emission:** {tot_em:.2f} kg CO₂")
            st.write(f"**Total Cost:** Rp {tot_ct:,.2f}")
            st.dataframe(res_df)
            csv = res_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "results_kg.csv", "text/csv")

if __name__ == "__main__":
    main()
