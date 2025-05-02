# streamlit_app.py

import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

def optimize_waste(user_df: pd.DataFrame, max_budget: float, origin_coords: tuple):
    # 1) Pastikan kolom Quantity ada
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0

    # 2) Load data statis
    treatments_df   = data.treatments_df
    transport_df    = data.transport_df
    locations_df    = data.locations_df
    capacity_df     = data.facility_capacity_df
    facility_rules  = data.facility_rules
    max_prop_df     = data.max_prop_df

    # 3) Merge capacity + coords
    facility_df = (
        capacity_df
        .merge(locations_df, on='Facility_ID')
        .rename(columns={'Capacity':'Max_Capacity'})
    )

    # 4) Definisikan model
    model = pulp.LpProblem("Waste_Optimization", pulp.LpMinimize)
    decision_vars = {}

    # 5) Decision vars & demand constraints
    for idx, row in user_df.iterrows():
        item, cat, qty = row['Waste_Item'], row['Category'], float(row['Quantity'])
        # hanya treatments di treatments_df untuk item+cat
        app = treatments_df[
            (treatments_df['Waste_Item']==item) &
            (treatments_df['Category']==cat)
        ]
        for _, t in app.iterrows():
            tr, em_f, tr_cost = t['Treatment'], float(t['Emission_Factor']), float(t['Treatment_Cost'])
            for fid, rules in facility_rules.items():
                if cat in rules['Category'] and tr in rules['Treatment']:
                    fac = facility_df[
                        (facility_df['Facility_ID']==fid)&
                        (facility_df['Treatment']==tr)
                    ]
                    if fac.empty: continue
                    coords = (fac['Latitude'].iloc[0], fac['Longitude'].iloc[0])
                    var = pulp.LpVariable(f"x_{idx}_{item}_{tr}_{fid}", lowBound=0, upBound=qty)
                    decision_vars[(idx,item,cat,tr,fid)] = {
                        'var': var, 'category': cat, 'treatment': tr,
                        'em_factor': em_f, 'tr_cost': tr_cost, 'coords': coords
                    }
        # demand == qty
        model += (
            pulp.lpSum(v['var']
                       for k,v in decision_vars.items() if k[0]==idx)
            == qty,
            f"Demand_{idx}"
        )

    # 6) Max-proportion constraints
    total_by_cat = user_df.groupby('Category')['Quantity'].sum().to_dict()
    for _, mp in max_prop_df.iterrows():
        cat, trt, prop = mp['Category'], mp['Treatment'], float(mp['Max_Proportion'])
        if cat not in total_by_cat: continue
        cap = prop * total_by_cat[cat]
        vars_for = [
            v['var'] for k,v in decision_vars.items()
            if v['category']==cat and v['treatment']==trt
        ]
        if vars_for:
            model += (
                pulp.lpSum(vars_for) <= cap,
                f"MaxProp_{cat.replace(' ','')}_{trt.replace(' ','')}"
            )

    # 7) Capacity per TPA
    for fid in facility_df['Facility_ID'].unique():
        cap = float(facility_df.loc[facility_df['Facility_ID']==fid,'Max_Capacity'].iloc[0])
        vars_f = [v['var'] for k,v in decision_vars.items() if k[4]==fid]
        if vars_f:
            model += (
                pulp.lpSum(vars_f) <= cap,
                f"Cap_{fid}"
            )

    # 8) Objective: minimalisasi emisi
    terms = []
    for v in decision_vars.values():
        var = v['var']
        poss = transport_df[transport_df['Max_Capacity']>=var.upBound]
        if poss.empty: poss = transport_df
        best = poss.nsmallest(1,'Emission_per_ton').iloc[0]
        d_km = geodesic(origin_coords, v['coords']).km
        terms.append(var*(v['em_factor']+best['Emission_per_ton']*d_km))
    model += pulp.lpSum(terms), "Total_Emission"

    # 9) Budget constraint
    cost_terms = []
    for v in decision_vars.values():
        var = v['var']
        poss = transport_df[transport_df['Max_Capacity']>=var.upBound]
        if poss.empty: poss = transport_df
        best = poss.nsmallest(1,'Emission_per_ton').iloc[0]
        d_km = geodesic(origin_coords, v['coords']).km
        cost_terms.append(var*(v['tr_cost']+best.get('Cost_per_ton',0.0)*d_km))
    model += (
        pulp.lpSum(cost_terms)<= max_budget,
        "Budget"
    )

    # 10) Solve & status
    status_code = model.solve()
    status = pulp.LpStatus.get(status_code, "Unknown")

    # 11) Collect hasil
    rows = []
    for (idx,item,cat,tr,fid), v in decision_vars.items():
        amt = v['var'].varValue or 0
        if amt>1e-6:
            tpa = data.locations_df.loc[
                data.locations_df['Facility_ID']==fid,'Location'
            ].iloc[0]
            poss = transport_df[transport_df['Max_Capacity']>=amt]
            if poss.empty: poss = transport_df
            best = poss.nsmallest(1,'Emission_per_ton').iloc[0]
            d_km = geodesic(origin_coords, v['coords']).km
            rows.append({
                'Waste_Item': item,
                'Category': cat,
                'Treatment': tr,
                'TPA_Name': tpa,
                'Amount': round(amt,6),
                'Treatment_Emission': v['em_factor'],
                'Transport_Mode': best['Mode'],
                'Distance_km': round(d_km,2),
                'Transport_Emission': best['Emission_per_ton']*d_km,
                'Cost_Treatment': v['tr_cost'],
                'Total_Emission': amt*(v['em_factor']+best['Emission_per_ton']*d_km),
                'Total_Cost': amt*(v['tr_cost']+best.get('Cost_per_ton',0.0)*d_km)
            })

    result_df = pd.DataFrame(rows)

    # 12) **Debug: tampilkan proporsi aktual vs batas**
    prop_checks = []
    for _, mp in max_prop_df.iterrows():
        cat, trt, prop = mp['Category'], mp['Treatment'], float(mp['Max_Proportion'])
        total_cat = total_by_cat.get(cat,0)
        alloc = result_df.loc[
            (result_df['Category']==cat)&
            (result_df['Treatment']==trt),'Amount'
        ].sum()
        prop_checks.append({
            'Category': cat,
            'Treatment': trt,
            'Allowed_%': prop*100,
            'Allocated': alloc,
            'TotalCat': total_cat,
            'Used_%': (alloc/total_cat*100) if total_cat>0 else 0
        })
    prop_df = pd.DataFrame(prop_checks)

    return result_df, prop_df, result_df['Total_Emission'].sum(), result_df['Total_Cost'].sum(), status

def main():
    st.title("Waste Treatment Optimization")
    st.markdown("Upload Excel with Waste_Item, Category, (opt) Quantity.")

    uploaded   = st.file_uploader("Choose file", type=["xlsx","xls"])
    max_budget = st.number_input("Budget (Rp)", min_value=0.0, step=1000.0)

    st.subheader("Origin Coordinates")
    origin_lat = st.number_input("Latitude", value=float(data.locations_df['Latitude'].mean()))
    origin_lon = st.number_input("Longitude", value=float(data.locations_df['Longitude'].mean()))
    origin = (origin_lat, origin_lon)

    if uploaded and max_budget>0:
        df_in = pd.read_excel(uploaded, engine="openpyxl")
        if st.button("Optimize"):
            with st.spinner("Running..."):
                res, prop_df, tot_em, tot_ct, status = optimize_waste(df_in, max_budget, origin)
            st.markdown(f"**Status:** {status}")
            st.markdown(f"**Total Emission:** {tot_em:.2f} kgCO₂ — **Total Cost:** Rp {tot_ct:,.2f}")
            st.subheader("Allocation Results")
            st.dataframe(res)
            st.subheader("Proportion Check (Allocated vs Allowed)")
            st.dataframe(prop_df)
            st.download_button("Download Results CSV", res.to_csv(index=False), "res.csv")
            st.download_button("Download Prop Checks CSV", prop_df.to_csv(index=False), "prop_checks.csv")

if __name__=="__main__":
    main()
