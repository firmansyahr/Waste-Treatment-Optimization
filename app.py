# streamlit_app.py

import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

# Optimization function

def optimize_waste(user_df: pd.DataFrame, max_budget: float, origin_coords: tuple):
    # Ensure Quantity column exists
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0

    # Load static data
    TREAT = data.treatments_df
    TRANS  = data.transport_df
    LOC    = data.locations_df
    CAPTY  = data.facility_capacity_df
    RULES  = data.facility_rules
    MP     = data.max_prop_df

    # Merge facility capacity with coordinates
    FAC = (
        CAPTY
        .merge(LOC, on='Facility_ID')
        .rename(columns={'Capacity':'Max_Capacity'})
    )

    # Build LP model
    mdl = pulp.LpProblem("WasteOptimization", pulp.LpMinimize)
    decision_vars = {}
    y_vars = {}

    # Total quantity per category
    total_by_cat = user_df.groupby('Category')['Quantity'].sum().to_dict()

    # Define y_vars for category-treatment proportions
    for _, row in MP.iterrows():
        cat, trt, prop = row['Category'], row['Treatment'], float(row['Max_Proportion'])
        if cat not in total_by_cat:
            continue
        ub = prop * total_by_cat[cat]
        y = pulp.LpVariable(f"y_{cat}_{trt}", lowBound=0, upBound=ub)
        y_vars[(cat, trt)] = y

    # Constraint: sum of y over treatments equals total_by_cat
    for cat, tot in total_by_cat.items():
        terms = [y for (c,t),y in y_vars.items() if c==cat]
        if terms:
            mdl += (pulp.lpSum(terms) == tot, f"SumByCat_{cat}")

    # Define x_vars for each input row, treatment, and facility
    for idx, row in user_df.iterrows():
        item, cat, qty = row['Waste_Item'], row['Category'], float(row['Quantity'])
        applicable = TREAT[(TREAT['Waste_Item']==item) & (TREAT['Category']==cat)]
        for _, t in applicable.iterrows():
            trt = t['Treatment']
            ef  = float(t['Emission_Factor'])
            tc  = float(t['Treatment_Cost'])
            for fid, rules in RULES.items():
                if cat in rules['Category'] and trt in rules['Treatment']:
                    fac = FAC[(FAC['Facility_ID']==fid) & (FAC['Treatment']==trt)]
                    if fac.empty:
                        continue
                    coords = (fac['Latitude'].iloc[0], fac['Longitude'].iloc[0])
                    x = pulp.LpVariable(f"x_{idx}_{trt}_{fid}", lowBound=0, upBound=qty)
                    decision_vars[(idx,item,cat,trt,fid)] = {
                        'var': x,
                        'em_factor': ef,
                        'tr_cost': tc,
                        'coords': coords
                    }
                    # Link x <= y_cat_trt
                    y = y_vars.get((cat, trt))
                    if y:
                        mdl += (x <= y, f"Link_{idx}_{cat}_{trt}")
        # Demand constraint
        mdl += (
            pulp.lpSum(v['var'] for (i,it,c,tt,f),v in decision_vars.items() if i==idx) == qty,
            f"Demand_{idx}"
        )

    # Facility capacity constraints
    for fid in FAC['Facility_ID'].unique():
        cap = float(FAC.loc[FAC['Facility_ID']==fid,'Max_Capacity'].iloc[0])
        terms = [v['var'] for (i,it,c,tt,f),v in decision_vars.items() if f==fid]
        if terms:
            mdl += (pulp.lpSum(terms) <= cap, f"Cap_{fid}")

    # Objective: minimize emissions (treatment + transport)
    obj_terms = []
    for props in decision_vars.values():
        var = props['var']
        possible = TRANS[TRANS['Max_Capacity']>=var.upBound]
        if possible.empty:
            possible = TRANS
        best = possible.nsmallest(1,'Emission_per_ton').iloc[0]
        dist = geodesic(origin_coords, props['coords']).km
        obj_terms.append(var * (props['em_factor'] + best['Emission_per_ton']*dist))
    mdl += (pulp.lpSum(obj_terms), "Total_Emission")

    # Budget constraint: cost
    cost_terms = []
    for props in decision_vars.values():
        var = props['var']
        possible = TRANS[TRANS['Max_Capacity']>=var.upBound]
        if possible.empty:
            possible = TRANS
        best = possible.nsmallest(1,'Emission_per_ton').iloc[0]
        dist = geodesic(origin_coords, props['coords']).km
        cost_terms.append(var * (props['tr_cost'] + best.get('Cost_per_ton',0.0)*dist))
    mdl += (pulp.lpSum(cost_terms) <= max_budget, "Budget_Constraint")

    # Solve model
    status_code = mdl.solve()
    status = pulp.LpStatus.get(status_code, 'Unknown')

    # Collect allocation results
    alloc_rows = []
    for (idx,item,cat,trt,fid), props in decision_vars.items():
        amt = props['var'].varValue or 0
        if amt > 1e-6:
            tpa = data.locations_df.loc[data.locations_df['Facility_ID']==fid,'Location'].iloc[0]
            possible = TRANS[TRANS['Max_Capacity']>=amt]
            if possible.empty:
                possible = TRANS
            best = possible.nsmallest(1,'Emission_per_ton').iloc[0]
            dist = geodesic(origin_coords, props['coords']).km
            alloc_rows.append({
                'Waste_Item': item,
                'Category': cat,
                'Treatment': trt,
                'TPA_Name': tpa,
                'Amount': round(amt,6),
                'Treatment_Emission': props['em_factor'],
                'Transport_Mode': best['Mode'],
                'Distance_km': round(dist,2),
                'Transport_Emission': best['Emission_per_ton']*dist,
                'Cost_Treatment': props['tr_cost'],
                'Total_Emission': amt*(props['em_factor']+best['Emission_per_ton']*dist),
                'Total_Cost': amt*(props['tr_cost']+best.get('Cost_per_ton',0.0)*dist)
            })
    alloc_df = pd.DataFrame(alloc_rows)

    # Proportion check
    prop_rows = []
    for (cat,trt), y in y_vars.items():
        alloc = alloc_df.loc[(alloc_df['Category']==cat)&(alloc_df['Treatment']==trt),'Amount'].sum()
        prop_rows.append({
            'Category': cat,
            'Treatment': trt,
            'Allowed': y.upBound,
            'Allocated': alloc
        })
    prop_df = pd.DataFrame(prop_rows)

    # Summary metrics
    total_em = alloc_df['Total_Emission'].sum()
    total_ct = alloc_df['Total_Cost'].sum()

    return alloc_df, prop_df, total_em, total_ct, status

# Streamlit UI

def main():
    st.title("Waste Treatment Optimization App")
    st.markdown("**Upload Excel** with columns: Waste_Item, Category, (optional) Quantity.")

    uploaded   = st.file_uploader("Choose Excel...", type=["xlsx","xls"])
    max_budget = st.number_input("Maximal Budget (Rp)", min_value=0.0, step=1000.0)

    st.subheader("Origin Coordinates")
    origin_lat = st.number_input("Latitude", value=float(data.locations_df['Latitude'].mean()))
    origin_lon = st.number_input("Longitude", value=float(data.locations_df['Longitude'].mean()))
    origin_coords = (origin_lat, origin_lon)

    if uploaded and max_budget > 0:
        user_df = pd.read_excel(uploaded, engine='openpyxl')
        if st.button("Run Optimization"):
            with st.spinner("Optimizing..."):
                alloc_df, prop_df, tot_em, tot_ct, status = optimize_waste(
                    user_df, max_budget, origin_coords
                )
            st.subheader(f"Status: {status}")
            st.write(f"**Total Emission:** {tot_em:.2f} kg CO₂")
            st.write(f"**Total Cost:** Rp {tot_ct:,.2f}")

            st.subheader("Allocation Results")
            st.dataframe(alloc_df)

            st.subheader("Proportion Check")
            st.dataframe(prop_df)

            csv1 = alloc_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Allocation CSV", csv1, "allocation.csv", "text/csv")

            csv2 = prop_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Proportion CSV", csv2, "proportion.csv", "text/csv")

if __name__ == "__main__":
    main()
