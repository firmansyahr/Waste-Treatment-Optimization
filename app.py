# streamlit_app.py

import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

def optimize_waste(user_df: pd.DataFrame, max_budget: float, origin_coords: tuple):
    # 1) Ensure Quantity column exists
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0

    # 2) Load static tables
    treatments_df   = data.treatments_df
    transport_df    = data.transport_df
    locations_df    = data.locations_df
    capacity_df     = data.facility_capacity_df
    facility_rules  = data.facility_rules
    max_prop_df     = data.max_prop_df

    # 3) Merge facility capacity with coordinates
    facility_df = (
        capacity_df
        .merge(locations_df, on='Facility_ID')
        .rename(columns={'Capacity':'Max_Capacity'})
    )

    # 4) Build LP model
    model = pulp.LpProblem("Waste_Optimization", pulp.LpMinimize)
    decision_vars = {}

    # 5) Create decision variables and demand constraints
    for idx, row in user_df.iterrows():
        item     = row['Waste_Item']
        category = row['Category']
        qty      = float(row['Quantity'])

        # Only treatments defined for this Waste_Item and Category
        applicable = treatments_df[
            (treatments_df['Category']==category) &
            (treatments_df['Waste_Item']==item)
        ]
        for _, t in applicable.iterrows():
            tr        = t['Treatment']
            em_factor = float(t['Emission_Factor'])
            tr_cost   = float(t['Treatment_Cost'])

            # Only facilities that accept this combination
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
                    var = pulp.LpVariable(f"x_{item}_{tr}_{fid}_{idx}",
                                          lowBound=0, upBound=qty)
                    decision_vars[(item, tr, fid, idx)] = {
                        'var': var,
                        'category': category,
                        'treatment': tr,
                        'em_factor': em_factor,
                        'tr_cost': tr_cost,
                        'coords': coords
                    }

        # Demand constraint: allocate exactly qty for this row
        model += (
            pulp.lpSum(
                v['var'] for (it, _, _, i), v in decision_vars.items()
                if it == item and i == idx
            ) == qty,
            f"Demand_{item}_{idx}"
        )

    # 6) Max-proportion constraints per category-treatment
    total_by_cat = user_df.groupby('Category')['Quantity'].sum().to_dict()
    for _, mp in max_prop_df.iterrows():
        cat = mp['Category']
        trt = mp['Treatment']
        prop = float(mp['Max_Proportion'])
        if cat not in total_by_cat:
            continue
        cap = prop * total_by_cat[cat]
        vars_for = [
            v['var'] for v in decision_vars.values()
            if v['category']==cat and v['treatment']==trt
        ]
        if vars_for:
            model += (
                pulp.lpSum(vars_for) <= cap,
                f"MaxProp_{cat.replace(' ','')}_{trt.replace(' ','')}"
            )

    # 7) Facility capacity constraints
    for fid in facility_df['Facility_ID'].unique():
        cap = float(
            facility_df.loc[facility_df['Facility_ID']==fid, 'Max_Capacity']
            .iloc[0]
        )
        vars_at_fid = [
            v['var'] for (it, tr, f, i), v in decision_vars.items()
            if f == fid
        ]
        if vars_at_fid:
            model += (
                pulp.lpSum(vars_at_fid) <= cap,
                f"Cap_{fid}"
            )

    # 8) Objective: minimize total emissions (treatment + transport)
    obj_terms = []
    for props in decision_vars.values():
        var = props['var']
        possible = transport_df[transport_df['Max_Capacity'] >= var.upBound]
        if possible.empty:
            possible = transport_df
        best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]
        dist = geodesic(origin_coords, props['coords']).km
        obj_terms.append(var * (props['em_factor'] + best['Emission_per_ton'] * dist))
    model += pulp.lpSum(obj_terms), "Total_Emission"

    # 9) Budget constraint: treatment + transport cost
    cost_terms = []
    for props in decision_vars.values():
        var = props['var']
        possible = transport_df[transport_df['Max_Capacity'] >= var.upBound]
        if possible.empty:
            possible = transport_df
        best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]
        dist = geodesic(origin_coords, props['coords']).km
        cost_terms.append(
            var * (props['tr_cost'] + best.get('Cost_per_ton', 0.0) * dist)
        )
    model += (
        pulp.lpSum(cost_terms) <= max_budget,
        "Budget_Constraint"
    )

    # 10) Solve model and get status
    status_code = model.solve()
    status = pulp.LpStatus.get(status_code, "Unknown")

    # 11) Collect results
    results = []
    for (item, tr, fid, idx), props in decision_vars.items():
        amt = props['var'].varValue
        if amt is not None and amt > 1e-6:
            tpa_name = data.locations_df.loc[
                data.locations_df['Facility_ID']==fid, 'Location'
            ].iloc[0]
            possible = transport_df[transport_df['Max_Capacity'] >= amt]
            if possible.empty:
                possible = transport_df
            best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]
            dist = geodesic(origin_coords, props['coords']).km
            results.append({
                'Waste_Item': item,
                'Category': props['category'],
                'Treatment': tr,
                'TPA_Name': tpa_name,
                'Amount': round(amt, 6),
                'Treatment_Emission': props['em_factor'],
                'Transport_Mode': best['Mode'],
                'Distance_km': round(dist, 2),
                'Transport_Emission': best['Emission_per_ton'] * dist,
                'Cost_Treatment': props['tr_cost'],
                'Total_Emission': amt * (props['em_factor'] + best['Emission_per_ton'] * dist),
                'Total_Cost': amt * (props['tr_cost'] + best.get('Cost_per_ton', 0.0) * dist)
            })
    df = pd.DataFrame(results)
    return df, df['Total_Emission'].sum(), df['Total_Cost'].sum(), status

def main():
    st.title("Waste Treatment Optimization App")
    st.markdown("**Upload input** with columns: Waste_Item, Category, (optional) Quantity.")

    uploaded   = st.file_uploader("Choose Excel...", type=["xlsx", "xls"])
    max_budget = st.number_input("Maximal Budget (Rp)", value=0.0, step=1000.0)

    st.subheader("Origin Coordinates")
    origin_lat = st.number_input(
        "Latitude",
        value=float(data.locations_df['Latitude'].mean())
    )
    origin_lon = st.number_input(
        "Longitude",
        value=float(data.locations_df['Longitude'].mean())
    )
    origin_coords = (origin_lat, origin_lon)

    if uploaded and max_budget > 0:
        user_df = pd.read_excel(uploaded, engine="openpyxl")
        if st.button("Run Optimization"):
            with st.spinner("Optimizing..."):
                res_df, tot_em, tot_ct, status = optimize_waste(
                    user_df, max_budget, origin_coords
                )
            st.subheader(f"Status: {status}")
            st.write(f"**Total Emission:** {tot_em:.2f} kg CO₂")
            st.write(f"**Total Cost:** Rp {tot_ct:,.2f}")
            st.dataframe(res_df)
            csv = res_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "results.csv", "text/csv")

if __name__ == "__main__":
    main()
