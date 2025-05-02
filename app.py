# streamlit_app.py

import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

def optimize_waste(user_df: pd.DataFrame, max_budget: float, origin_coords: tuple):
    # 1) Siapkan Quantity
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0

    # 2) Load static data
    TREAT = data.treatments_df
    TRANS  = data.transport_df
    LOC    = data.locations_df
    CAPTY  = data.facility_capacity_df
    RULES  = data.facility_rules
    MP     = data.max_prop_df

    # 3) Merge kapasitas + koordinat
    F = (CAPTY
         .merge(LOC, on='Facility_ID')
         .rename(columns={'Capacity':'Max_Capacity'}))

    # 4) Mulai model
    mdl = pulp.LpProblem("WasteOpt", pulp.LpMinimize)

    # 5) Total per kategori
    total_by_cat = user_df.groupby('Category')['Quantity'].sum().to_dict()

    # 6) Variabel y untuk alokasi kategori→treatment
    y_vars = {}
    for _, row in MP.iterrows():
        cat, trt, prop = row['Category'], row['Treatment'], float(row['Max_Proportion'])
        if cat not in total_by_cat:
            continue
        ub = prop * total_by_cat[cat]
        y = pulp.LpVariable(f"y_{cat}_{trt}", lowBound=0, upBound=ub)
        y_vars[(cat,trt)] = y

    # 7) Constraint: ∑ₜ y_{cat,ₜ} = total_by_cat
    for cat, total in total_by_cat.items():
        mdl += (
            pulp.lpSum(y_vars[(cat,trt)]
                       for _,trt, _ in MP.itertuples(index=False)
                       if (cat,trt) in y_vars)
            == total,
            f"SumByCat_{cat}"
        )

    # 8) Decision vars x untuk setiap baris input
    x_vars = {}
    for idx, row in user_df.iterrows():
        item, cat, qty = row['Waste_Item'], row['Category'], float(row['Quantity'])
        # treatments yang valid
        app = TREAT[(TREAT['Waste_Item']==item)&(TREAT['Category']==cat)]
        for _, t in app.iterrows():
            trt, ef, tc = t['Treatment'], float(t['Emission_Factor']), float(t['Treatment_Cost'])
            for fid, rules in RULES.items():
                if cat in rules['Category'] and trt in rules['Treatment']:
                    fac = F[(F['Facility_ID']==fid)&(F['Treatment']==trt)]
                    if fac.empty: 
                        continue
                    coords = (fac['Latitude'].iloc[0], fac['Longitude'].iloc[0])
                    x = pulp.LpVariable(f"x_{idx}_{trt}_{fid}", lowBound=0, upBound=qty)
                    x_vars[(idx,item,cat,trt,fid)] = {
                        'var': x, 'em_factor':ef, 'tr_cost':tc, 'coords':coords
                    }
                    # link x ≤ y_cat_trt
                    mdl += (
                        x <= y_vars[(cat,trt)],
                        f"Link_{idx}_{cat}_{trt}"
                    )
        # demand == qty
        mdl += (
            pulp.lpSum(v['var']
                       for (i,it,ct,tt,f),v in x_vars.items() if i==idx)
            == qty,
            f"Demand_{idx}"
        )

    # 9) Capacity per TPA
    for fid in F['Facility_ID'].unique():
        cap = float(F.loc[F['Facility_ID']==fid,'Max_Capacity'].iloc[0])
        mdl += (
            pulp.lpSum(v['var']
                       for (_,_,_,_,f),v in x_vars.items() if f==fid)
            <= cap,
            f"Cap_{fid}"
        )

    # 10) Objective: minimize emisi total
    obj = []
    for v in x_vars.values():
        var = v['var']
        poss = TRANS[TRANS['Max_Capacity']>=var.upBound]
        if poss.empty: poss = TRANS
        best = poss.nsmallest(1,'Emission_per_ton').iloc[0]
        d = geodesic(origin_coords, v['coords']).km
        obj.append(var*(v['em_factor'] + best['Emission_per_ton']*d))
    mdl += pulp.lpSum(obj), "TotalEmission"

    # 11) Budget constraint
    costs = []
    for v in x_vars.values():
        var = v['var']
        poss = TRANS[TRANS['Max_Capacity']>=var.upBound]
        if poss.empty: poss = TRANS
        best = poss.nsmallest(1,'Emission_per_ton').iloc[0]
        d = geodesic(origin_coords, v['coords']).km
        costs.append(var*(v['tr_cost'] + best.get('Cost_per_ton',0.0)*d))
    mdl += (
        pulp.lpSum(costs) <= max_budget,
        "Budget"
    )

    # 12) Solve & status
    stat = mdl.solve()
    status = pulp.LpStatus.get(stat, "Unknown")

    # 13) Kumpulkan hasil
    rows = []
    for (idx,item,cat,trt,fid),v in x_vars.items():
        amt = v['var'].varValue or 0
        if amt>1e-6:
            tpa = LOC.loc[LOC['Facility_ID']==fid,'Location'].iloc[0]
            poss = TRANS[TRANS['Max_Capacity']>=amt]
            if poss.empty: poss = TRANS
            best = poss.nsmallest(1,'Emission_per_ton').iloc[0]
            d = geodesic(origin_coords, v['coords']).km
            rows.append({
                'Waste_Item': item,
                'Category': cat,
                'Treatment': trt,
                'TPA_Name': tpa,
                'Amount': round(amt,6),
                'Treatment_Emission': v['em_factor'],
                'Transport_Mode': best['Mode'],
                'Distance_km': round(d,2),
                'Transport_Emission': best['Emission_per_ton']*d,
                'Cost_Treatment': v['tr_cost'],
                'Total_Emission': amt*(v['em_factor']+best['Emission_per_ton']*d),
                'Total_Cost': amt*(v['tr_cost']+best.get('Cost_per_ton',0.0)*d)
            })
    result_df = pd.DataFrame(rows)

    # debug proporsi aktual
    prop_checks = []
    for (cat,trt),y in y_vars.items():
        alloc = result_df.loc[
            (result_df['Category']==cat)&
            (result_df['Treatment']==trt),
            'Amount'
        ].sum()
        allowed = y.upBound
        prop_checks.append({
            'Category': cat,
            'Treatment': trt,
            'Allowed': allowed,
            'Allocated': alloc
        })
    prop_df = pd.DataFrame(prop_checks)

    return result_df, prop_df, status

def main():
    st.title("Waste Treatment Optimization")
    st.markdown("Upload Excel with Waste_Item, Category, (optional) Quantity.")

    uploaded   = st.file_uploader("Choose file", type=["xlsx","xls"])
    max_budget = st.number_input("Budget (Rp)", step=1000.0)

    st.subheader("Origin Coordinates")
    lat = st.number_input("Latitude", value=float(data.locations_df['Latitude'].mean()))
    lon = st.number_input("Longitude",value=float(data.locations_df['Longitude'].mean()))
    origin = (lat, lon)

    if uploaded and max_budget>0:
        df_in = pd.read_excel(uploaded, engine="openpyxl")
        if st.button("Optimize"):
            with st.spinner("Running..."):
                res, prop_df, status = optimize_waste(df_in, max_budget, origin)
            st.markdown(f"**Status:** {status}")
            st.subheader("Allocation")
            st.dataframe(res)
            st.subheader("Proporsi Check (y vs x)")
            st.dataframe(prop_df)

if __name__=="__main__":
    main()
