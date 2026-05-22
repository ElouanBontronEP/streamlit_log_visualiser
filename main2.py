import pandas as pd
import numpy as np
import json
import streamlit as st
import datetime as dt
import zipfile
import io

from process_log import process_log
from plots import plot_prod_conso, plot_soc

st.set_page_config(layout="wide")


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        if isinstance(obj, pd.Series):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (dt.date, dt.datetime)):
            return obj.isoformat()
        return super().default(obj)


def create_zip(files_csv, files_json):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for id, df in files_csv.items():
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            zip_file.writestr(f"{id}.csv", csv_bytes)
        for id, content in files_json.items():
            json_bytes = json.dumps(content, indent=4, cls=CustomEncoder).encode("utf-8")
            zip_file.writestr(f"{id}.json", json_bytes)
    zip_buffer.seek(0)
    return zip_buffer


def process_and_display(file_name, data):
    input_exports_csv = ['ASSET_STEPS', 'ASSETS', 'CONGESTION_ASSETS', 'CONGESTIONS', 'OPERATION', 'VARIABLE_COST_MODELS']
    input_exports_json = []
    output_exports_csv = ['VIOLATIONS_OUTPUT']
    output_exports_json = ['OPERATION_OUTPUT']
    solve_state_exports_json = ['solve_status']

    state_key = f"results_{file_name}"

    if st.button("Process Log", key=f"btn_{file_name}"):
        with st.spinner("Processing..."):
            files_csv, files_json, log_decoded, step_summary, assets = process_log(
                data,
                input_exports_csv,
                input_exports_json,
                output_exports_csv,
                output_exports_json,
                solve_state_exports_json
            )
            st.session_state[state_key] = {
                "files_csv": files_csv,
                "files_json": files_json,
                "step_summary": step_summary,
                "assets": assets,
            }
    

    if state_key in st.session_state:
        results = st.session_state[state_key]

        st.subheader(f'Datetime: {results["step_summary"]["time"].min()}')

        zip_buffer = create_zip(results["files_csv"], results["files_json"])
        st.download_button(
            label="⬇️ Download ZIP",
            data=zip_buffer,
            file_name=f"{file_name.rsplit('.', 1)[0]}_exports.zip",
            mime="application/zip",
            key=f"zip_{file_name}"
        )

        st.subheader("Production and Consumption Plot")
        fig_prod_conso = plot_prod_conso(results["step_summary"])
        st.plotly_chart(fig_prod_conso, key=f"prod_conso_{file_name}")

        st.subheader("State of Charge Plot")
        fig_soc = plot_soc(results["step_summary"], results["assets"])
        st.plotly_chart(fig_soc, key=f"soc_{file_name}")


def main():
    st.title("Decision Optimization Log Viewer")

    uploaded_files = st.file_uploader(
        "Upload your log files",
        type=["txt", "json"],
        accept_multiple_files=True
    )

    if uploaded_files:
        tabs = st.tabs([f.name for f in uploaded_files])

        for tab, uploaded_file in zip(tabs, uploaded_files):
            with tab:
                data = json.load(uploaded_file)
                process_and_display(uploaded_file.name, data)


if __name__ == "__main__":
    main()