import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

def optimize_waste(user_df: pd.DataFrame, max_budget: float, origin_coords: tuple):
    # Input waste quantity in tons; convert to kg
    user_df = user_df.copy()
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0
    # Quantity in tons -> kg
    user_df['Quantity_kg'] = user_df['Quantity'] * 1000.0

    # Load static data (emission & cost per kg, capacity in kg)
    treatments_df = data.treatments_df.copy()
    transport_df  = data.transport_df.copy()
    locations_df  = data.locations_df
    capacity_df   = data.facility_capacity_df.copy()
    facility_rules = data.facility_rules
    max_prop_df   = data.max_prop_df

    # Convert transport units: per ton -> per kg, and capacity ton -> kg
    transport_df['Emission_per_kg'] = transport_df['Emission_per_ton'] / 1000.0
    if 'Cost_per_ton' in transport_df.columns:
        transport_df['Cost_per_kg'] = transport_df['Cost_per_ton'] / 1000.0
    else:
        transport_df['Cost_per_kg'] = 0.0
    transport_df['Max_Capacity'] *= 1000.0

    # Convert facility capacities from tons to kg
    capacity_df['Capacity'] *= 1000.0

    # Merge capacities with coordinates
    facility_df = capacity_df.merge(locations_df, on='Facility_ID').rename(columns={'Capacity':'Max_Capacity'})

    # Build LP model
    model = pulp.LpProblem("Waste_Optimization_kg_input_ton", pulp.LpMinimize)
    decision_vars = {}

    # Decision variables & demand
    for idx, row in user_df.iterrows():
        item, category, qty_kg = row['Waste_Item'], row['Category'], row['Quantity_kg']
        # Valid treatments for this item+cat
        applicable = treatments_df[(treatments_df['Waste_Item']==item) & (treatments_df['Category']==category)]
        for _, t in applicable.iterrows():
            tr, em_fac, tr_cost = t['Treatment'], float(t['Emission_Factor']), float(t['Treatment_Cost'])
            for fid, rules in facility_rules.items():
                if category in rules['Category'] and tr in rules['Treatment']:
                    fac = facility_df[(facility_df['Facility_ID']==fid) & (facility_df.get('Treatment',tr)==tr)]
                    if fac.empty:
                        continue
                    coords = (float(fac['Latitude'].iloc[0]), float(fac['Longitude'].iloc[0]))
                    var = pulp.LpVariable(f"x_{idx}_{tr}_{fid}", lowBound=0, upBound=qty_kg)
                    decision_vars[(idx, item, category, tr, fid)] = {
                        'var': var,
                        'em_fac': em_fac,
                        'tr_cost': tr_cost,
                        'coords': coords
                    }
        # Demand constraint
        model += (
            pulp.lpSum(v['var'] for (i,_,_,_,_), v in decision_vars.items() if i==idx) == qty_kg,
            f"Demand_{idx}"
        )

    # Max-proportion constraints
    totals = user_df.groupby('Category')['Quantity_kg'].sum().to_dict()
    for _, mp in max_prop_df.iterrows():
        cat, trt, prop = mp['Category'], mp['Treatment'], float(mp['Max_Proportion'])
        if cat not in totals:
            continue
        cap_kg = prop * totals[cat]
        vars_for = [v['var'] for k,v in decision_vars.items() if k[2]==cat and k[3]==trt]
        if vars_for:
            model += (
                pulp.lpSum(vars_for) <= cap_kg,
                f"MaxProp_{cat.replace(' ','')}_{trt.replace(' ','')}"
            )

    # Facility capacity constraints
    for fid in facility_df['Facility_ID'].unique():
        cap_kg = float(facility_df.loc[facility_df['Facility_ID']==fid, 'Max_Capacity'].iloc[0])
        terms = [v['var'] for k,v in decision_vars.items() if k[4]==fid]
        if terms:
            model += (
                pulp.lpSum(terms) <= cap_kg,
                f"Cap_{fid}"
            )

    # Objective: minimize emissions\    
    obj_terms = []
    for props in decision_vars.values():
        var_kg = props['var']
        em_treat = var_kg * props['em_fac']          # kgCO2
        poss = transport_df[transport_df['Max_Capacity']>=var_kg]
        if poss.empty:
            poss = transport_df
        best = poss.nsmallest(1, 'Emission_per_kg').iloc[0]
        dist = geodesic(origin_coords, props['coords']).km
        em_trans = var_kg * best['Emission_per_kg'] * dist
        obj_terms.append(em_treat + em_trans)
    model += pulp.lpSum(obj_terms), "Total_Emission"

    # Budget constraint: treatment + transport cost
    cost_terms = []
    for props in decision_vars.values():
        var_kg = props['var']
        cost_tr = var_kg * props['tr_cost']
        poss = transport_df[transport_df['Max_Capacity']>=var_kg]
        if poss.empty:
            poss = transport_df
        best = poss.nsmallest(1, 'Cost_per_kg').iloc[0]
        dist = geodesic(origin_coords, props['coords']).km
        cost_trans = var_kg * best['Cost_per_kg'] * dist
        cost_terms.append(cost_tr + cost_trans)
    model += (
        pulp.lpSum(cost_terms) <= max_budget,
        "Budget_Constraint"
    )

    # Solve model
    status_code = model.solve()
    status = pulp.LpStatus.get(status_code, "Unknown")

    # Collect results
    results = []
    for (idx, item, cat, tr, fid), props in decision_vars.items():
        amt_kg = props['var'].varValue or 0
        if amt_kg > 1e-6:
            tpa = data.locations_df.loc[data.locations_df['Facility_ID']==fid, 'Location'].iloc[0]
            poss = transport_df[transport_df['Max_Capacity']>=amt_kg]
            if poss.empty:
                poss = transport_df
            best = poss.nsmallest(1, 'Emission_per_kg').iloc[0]
            dist = geodesic(origin_coords, props['coords']).km
            results.append({
                'Waste_Item': item,
                'Category': cat,
                'Treatment': tr,
                'TPA_Name': tpa,
                'Amount_kg': round(amt_kg, 3),
                'Total_Emission_kgCO2': round(amt_kg * (props['em_fac'] + best['Emission_per_kg'] * dist), 3),
                'Total_Cost_Rp': round(amt_kg * (props['tr_cost'] + best['Cost_per_kg'] * dist), 2)
            })
    df_out = pd.DataFrame(results)
    return df_out, df_out['Total_Emission_kgCO2'].sum(), df_out['Total_Cost_Rp'].sum(), status

# Streamlit UI remains same but displays Amount_kg and updated fields

def main():
    st.title("Waste Treatment Optimization")
    st.markdown("[Download Template](https://docs.google.com/spreadsheets/d/1_w-_bBK6BpI3i-WM6L8ZlSZphyOCx3yco_TBh1cCnH0/edit?usp=sharing)")
    uploaded = st.file_uploader("Choose Excel...", type=["xlsx","xls"])
    max_budget = st.number_input("Max Budget (Rp)", min_value=0.0, step=1000.0)
    st.subheader("Origin Coordinates")
    origin_lat = st.number_input("Latitude", value=float(data.locations_df['Latitude'].mean()))
    origin_lon = st.number_input("Longitude", value=float(data.locations_df['Longitude'].mean()))
    origin_coords = (origin_lat, origin_lon)

    if uploaded and max_budget>0:
        user_df = pd.read_excel(uploaded, engine='openpyxl')
        if st.button("Run Optimization"):
            with st.spinner("Optimizing..."):
                res, tot_em, tot_ct, status = optimize_waste(user_df, max_budget, origin_coords)
            st.subheader(f"Status: {status}")
            st.write(f"**Total Emission:** {tot_em:.2f} kg CO₂")
            st.write(f"**Total Cost:** Rp {tot_ct:,.2f}")
            st.dataframe(res)
            csv = res.to_csv(index=False).encode('utf-8')
            st.download_button("Download Results", csv, "results.csv", "text/csv")

if __name__ == "__main__":
    main()
