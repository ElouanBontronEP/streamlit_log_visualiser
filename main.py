import pandas as pd
import numpy as np
import json
import streamlit as st
import datetime as dt

from process_log import process_log
from plots import plot_prod_conso, plot_soc

st.set_page_config(layout="wide")

def main():
    st.title("Decision Optimization Log Viewer")

    uploaded_file = st.file_uploader("Upload your log file", type=["txt", "json"])

    if uploaded_file is not None:
        data = json.load(uploaded_file)

        input_exports_csv = ['ASSET_STEPS', 'ASSETS', 'CONGESTION_ASSETS', 'CONGESTIONS', 'OPERATION', 'VARIABLE_COST_MODELS']
        input_exports_json = []
        output_exports_csv = ['VIOLATIONS_OUTPUT']
        output_exports_json = ['OPERATION_OUTPUT']
        solve_state_exports_json = ['solve_status']

        if st.button("Process Log"):
            files_csv, files_json, log_decoded, step_summary, assets = process_log(
                data,
                input_exports_csv,
                input_exports_json,
                output_exports_csv,
                output_exports_json,
                solve_state_exports_json
            )

            # st.subheader("Decoded Log")
            # st.text(log_decoded)

            # st.subheader("Step Summary")
            # st.dataframe(step_summary)

            # if st.button("download files"):
            #     for id, df in files_csv.items():
            #         csv = df.to_csv(index=False).encode('utf-8')
            #         st.download_button(
            #             label=f"Download {id}.csv",
            #             data=csv,
            #             file_name=f"{id}.csv",
            #             mime='text/csv',
            #         )
            #     for id, content in files_json.items():
            #         json_str = json.dumps(content, indent=4)
            #         st.download_button(
            #             label=f"Download {id}.json",
            #             data=json_str,
            #             file_name=f"{id}.json",
            #             mime='application/json',
            #         )

            st.subheader("Production and Consumption Plot")

            fig_prod_conso = plot_prod_conso(step_summary)
            st.plotly_chart(fig_prod_conso)

            st.subheader("State of Charge Plot")

            fig_soc = plot_soc(step_summary, assets)
            st.plotly_chart(fig_soc)

if __name__ == "__main__":
    main()   


