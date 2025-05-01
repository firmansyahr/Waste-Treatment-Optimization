import streamlit as st
import pandas as pd
import pulp
from geopy.distance import geodesic
import data

# Default origin coordinates: mean of all facilities (adjust in data.py if needed)
ORIGIN_COORDS = (
    data.locations_df['Latitude'].mean(),
    data.locations_df['Longitude'].mean()
)

# Optimization function
def optimize_waste(user_df: pd.DataFrame, max_budget: float):
    # Ensure Quantity column exists
    if 'Quantity' not in user_df.columns:
        user_df['Quantity'] = 1.0

    # References to static data
    treatments_df       = data.treatments_df
    transport_df        = data.transport_df
    locations_df        = data.locations_df
    capacity_df         = data.facility_capacity_df
    facility_rules      = data.facility_rules

    # Merge facility capacity with their coordinates
    facility_df = (
        capacity_df
        .merge(locations_df, on='Facility_ID')
        .rename(columns={'Capacity':'Max_Capacity'})
    )

    # Build LP problem
    model = pulp.LpProblem("Waste_Optimization", pulp.LpMinimize)
    decision_vars = {}

    # Create decision variables & demand constraints
    for _, row in user_df.iterrows():
        item     = row['Waste_Item']
        category = row['Category']
        qty      = float(row['Quantity'])

        # For each treatment applicable to this category
        for _, t in treatments_df[treatments_df['Category']==category].iterrows():
            tr = t['Treatment']
            em_factor = float(t['Emission_Factor'])
            tr_cost   = float(t['Treatment_Cost'])

            # For each facility that accepts this combination
            for fid, rules in facility_rules.items():
                if (category in rules['Category']) and (tr in rules['Treatment']):
                    fac = facility_df[
                        (facility_df['Facility_ID']==fid) &
                        (facility_df['Treatment']==tr)
                    ]
                    if fac.empty:
                        continue
                    cap   = float(fac['Max_Capacity'].iloc[0])
                    coords = (
                        float(fac['Latitude'].iloc[0]),
                        float(fac['Longitude'].iloc[0])
                    )

                    var = pulp.LpVariable(f"x_{item}_{tr}_{fid}", lowBound=0, upBound=qty)
                    decision_vars[(item, tr, fid)] = {
                        'var': var,
                        'em_factor': em_factor,
                        'tr_cost': tr_cost,
                        'capacity': cap,
                        'coords': coords
                    }

        # Demand constraint: total allocated == qty
        model += (
            pulp.lpSum(v['var'] for (it,_,_), v in decision_vars.items() if it==item)
            == qty,
            f"Demand_{item}"
        )

    # Objective: minimize total emissions (treatment + transport)
    obj_terms = []
    for (item, tr, fid), props in decision_vars.items():
        var = props['var']
        # choose transport mode with lowest emission capable of qty
        possible = transport_df[transport_df['Max_Capacity']>= var.upBound]
        if possible.empty:
            possible = transport_df
        best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]
        trans_em = float(best['Emission_per_ton'])
        obj_terms.append(var * (props['em_factor'] + trans_em))
    model += pulp.lpSum(obj_terms), "Total_Emission"

    # Budget constraint
    cost_terms = []
    for (item, tr, fid), props in decision_vars.items():
        var = props['var']
        possible = transport_df[transport_df['Max_Capacity']>= var.upBound]
        if possible.empty:
            possible = transport_df
        best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]
        trans_cost = float(best.get('Cost_per_ton', 0.0))
        cost_terms.append(var * (props['tr_cost'] + trans_cost))
    model += pulp.lpSum(cost_terms) <= max_budget, "Budget_Constraint"

    # Solve
    model.solve()

    # Collect results
    results = []
    for (item, tr, fid), props in decision_vars.items():
        amt = props['var'].varValue
        if amt and amt > 0:
            possible = transport_df[transport_df['Max_Capacity']>= amt]
            if possible.empty:
                possible = transport_df
            best = possible.nsmallest(1, 'Emission_per_ton').iloc[0]
            results.append({
                'Waste_Item': item,
                'Treatment': tr,
                'Facility_ID': fid,
                'Amount': amt,
                'Treatment_Emission': props['em_factor'],
                'Transport_Mode': best['Mode'],
                'Transport_Emission': best['Emission_per_ton'],
                'Cost_Treatment': props['tr_cost'],
                'Cost_Transport': best.get('Cost_per_ton', 0.0),
                'Total_Emission': amt * (props['em_factor'] + best['Emission_per_ton']),
                'Total_Cost': amt * (props['tr_cost'] + best.get('Cost_per_ton', 0.0))
            })
    df = pd.DataFrame(results)
    return df, df['Total_Emission'].sum(), df['Total_Cost'].sum()

# Streamlit UI

def main():
    st.title("Waste Treatment Optimization App")
    st.markdown("**Upload Excel** dengan kolom: `Waste_Item`, `Category`, dan (opsional) `Quantity`. Jika `Quantity` tidak ada, dianggap 1 per baris.")

    uploaded = st.file_uploader("Pilih file Excel...", type=["xlsx", "xls"] )
    max_budget = st.number_input("Maksimal Budget (Rp)", min_value=0.0, step=1000.0)

    if uploaded and max_budget > 0:
        user_df = pd.read_excel(uploaded)
        if st.button("Jalankan Optimasi"):
            with st.spinner("Mengoptimalkan..."):
                res_df, tot_em, tot_ct = optimize_waste(user_df, max_budget)
            st.subheader("Hasil Optimasi")
            st.write(f"**Total Emisi:** {tot_em:.2f} kg CO₂")
            st.write(f"**Total Biaya:** Rp {tot_ct:,.2f}")
            st.dataframe(res_df)
            csv = res_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "results.csv", "text/csv")

if __name__ == "__main__":
    main()
