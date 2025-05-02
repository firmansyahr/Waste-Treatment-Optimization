import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

def optimize_waste(user_df: pd.DataFrame, max_budget: float, origin_coords: tuple):
    # Input waste in tons → convert to kg
    user_df = user_df.copy()
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0
    # Quantity column now in tons; convert to kg
    user_df['Quantity_kg'] = user_df['Quantity'] * 1000.0

    # Load static data (all per kg)
    treatments_df   = data.treatments_df   # Emission_Factor (kgCO2/kg), Treatment_Cost (Rp/kg)
    transport_df    = data.transport_df    # Emission_per_kg (kgCO2 per kg-km), Cost_per_kg (Rp per kg-km), Max_Capacity (kg)
    locations_df    = data.locations_df    # Facility_ID, Latitude, Longitude
    capacity_df     = data.facility_capacity_df  # Facility_ID, Capacity (kg)
    facility_rules  = data.facility_rules
    max_prop_df     = data.max_prop_df    # Category, Treatment, Max_Proportion

    # Merge capacities with coords
    facility_df = capacity_df.merge(locations_df, on='Facility_ID')

    # Build LP model
    model = pulp.LpProblem("Waste_Optimization_kg_input_ton", pulp.LpMinimize)
    decision_vars = {}

    # Demand constraints and decision vars
    for idx, row in user_df.iterrows():
        item     = row['Waste_Item']
        category = row['Category']
        qty_kg   = row['Quantity_kg']

        # Treatments valid for this item & category
        applicable = treatments_df[
            (treatments_df['Waste_Item']==item) &
            (treatments_df['Category']==category)
        ]
        for _, t in applicable.iterrows():
            tr        = t['Treatment']
            em_factor = float(t['Emission_Factor'])  # kgCO2 per kg
            tr_cost   = float(t['Treatment_Cost'])    # Rp per kg

            # Facilities that accept
            for fid, rules in facility_rules.items():
                if category in rules['Category'] and tr in rules['Treatment']:
                    fac = facility_df[
                        (facility_df['Facility_ID']==fid) &
                        (facility_df['Treatment']==tr)
                    ] if 'Treatment' in facility_df.columns else facility_df[facility_df['Facility_ID']==fid]
                    if fac.empty:
                        continue
                    coords = (float(fac['Latitude'].iloc[0]), float(fac['Longitude'].iloc[0]))
                    # var in kg
                    var = pulp.LpVariable(f"x_{idx}_{item}_{tr}_{fid}", lowBound=0, upBound=qty_kg)
                    decision_vars[(idx, item, category, tr, fid)] = {
                        'var': var,
                        'em_factor': em_factor,
                        'tr_cost': tr_cost,
                        'coords': coords
                    }
        # Demand: sum allocations == qty_kg
        model += (
            pulp.lpSum(v['var'] for (i,_,_,_,_), v in decision_vars.items() if i==idx) == qty_kg,
            f"Demand_{idx}"
        )

    # Max-proportion constraints (unitless·kg)
    total_by_cat = user_df.groupby('Category')['Quantity_kg'].sum().to_dict()
    for _, mp in max_prop_df.iterrows():
        cat = mp['Category']
        trt = mp['Treatment']
        prop = float(mp['Max_Proportion'])
        if cat not in total_by_cat:
            continue
        cap_kg = prop * total_by_cat[cat]
        vars_for = [v['var'] for v in decision_vars.values() if v['var'].name.split('_')[2]==trt and v['var'].name.split('_')[3]==cat]
        # safer: filter by stored category/treatment
        vars_for = [v['var'] for k,v in decision_vars.items() if k[2]==cat and k[3]==trt]
        if vars_for:
            model += (
                pulp.lpSum(vars_for) <= cap_kg,
                f"MaxProp_{cat.replace(' ','')}_{trt.replace(' ','')}"
            )

    # Facility capacity constraints
    for fid in facility_df['Facility_ID'].unique():
        cap_kg = float(capacity_df.loc[capacity_df['Facility_ID']==fid, 'Capacity'].iloc[0])
        vars_at = [v['var'] for k,v in decision_vars.items() if k[4]==fid]
        if vars_at:
            model += (
                pulp.lpSum(vars_at) <= cap_kg,
                f"Cap_{fid}"
            )

    # Objective: minimize emissions (treatment + transport)
    obj_terms = []
    for k, props in decision_vars.items():
        var = props['var']  # kg
        em_treat = var * props['em_factor']
        # transport emission: kgCO2 per kg-km * distance * var
        poss = transport_df[transport_df['Max_Capacity'] >= var.upBound]
        if poss.empty:
            poss = transport_df
        best = poss.nsmallest(1, 'Emission_per_kg').iloc[0]
        dist = geodesic(origin_coords, props['coords']).km
        em_trans = var * best['Emission_per_kg'] * dist
        obj_terms.append(em_treat + em_trans)
    model += pulp.lpSum(obj_terms), "Total_Emission"

    # Budget constraint: cost (treatment + transport)
    cost_terms = []
    for k, props in decision_vars.items():
        var = props['var']
        cost_treat = var * props['tr_cost']
        poss = transport_df[transport_df['Max_Capacity'] >= var.upBound]
        if poss.empty:
            poss = transport_df
        best = poss.nsmallest(1, 'Cost_per_kg').iloc[0]
        dist = geodesic(origin_coords, props['coords']).km
        cost_trans = var * best['Cost_per_kg'] * dist
        cost_terms.append(cost_treat + cost_trans)
    model += (
        pulp.lpSum(cost_terms) <= max_budget,
        "Budget_Constraint"
    )

    # Solve
    status_code = model.solve()
    status = pulp.LpStatus.get(status_code, "Unknown")

    # Collect results
    results = []
    for (idx, item, cat, tr, fid), props in decision_vars.items():
        amt_kg = props['var'].varValue or 0
        if amt_kg > 1e-6:
            tpa = data.locations_df.loc[data.locations_df['Facility_ID']==fid, 'Location'].iloc[0]
            poss = transport_df[transport_df['Max_Capacity'] >= amt_kg]
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
                'Emission_kgCO2_treatment': round(amt_kg*props['em_factor'],3),
                'Emission_kgCO2_transport': round(amt_kg*best['Emission_per_kg']*dist,3),
                'Total_Emission_kgCO2': round(amt_kg*(props['em_factor']+best['Emission_per_kg']*dist),3),
                'Cost_Rp_treatment': round(amt_kg*props['tr_cost'],2),
                'Cost_Rp_transport': round(amt_kg*best['Cost_per_kg']*dist,2),
                'Total_Cost_Rp': round(amt_kg*(props['tr_cost']+best['Cost_per_kg']*dist),2)
            })
    df_out = pd.DataFrame(results)
    return df_out, df_out['Total_Emission_kgCO2'].sum(), df_out['Total_Cost_Rp'].sum(), status

# Streamlit UI remains same but displays Amount_kg and updated fields

def main():
    st.title("Waste Treatment Optimization (static in kg, input in ton)")
    st.markdown("Upload Excel with Waste_Item, Category, Quantity (in tons). Static data uses kg.")
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
