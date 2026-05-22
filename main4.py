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

def process_file(file_name, data):
    input_exports_csv = ['ASSET_STEPS', 'ASSETS', 'CONGESTION_ASSETS', 'CONGESTIONS', 'OPERATION', 'VARIABLE_COST_MODELS']
    input_exports_json = []
    output_exports_csv = ['VIOLATIONS_OUTPUT']
    output_exports_json = ['OPERATION_OUTPUT']
    solve_state_exports_json = ['solve_status']

    state_key = f"results_{file_name}"

    if state_key not in st.session_state:
        with st.spinner("Processing..."):
            files_csv, files_json, log_decoded, step_summary, assets, launch_timestamp, results_timestamp = process_log(
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
                "launch_timestamp": launch_timestamp,
                "results_timestamp": results_timestamp,
            }

    results = st.session_state[state_key]


def download_files(file_name, launch_timestamp, results_timestamp):

    results = st.session_state[f"results_{file_name}"]

    zip_buffer = create_zip(results["files_csv"], results["files_json"])
    st.download_button(
        label="⬇️ Download ZIP",
        data=zip_buffer,
        file_name=f"{str(results_timestamp).replace(':', '-').replace(' ', '_')}_exports.zip",
        mime="application/zip",
        key=f"zip_{file_name}"
    )

def display_files(file_name, launch_timestamp, results_timestamp):
    
    results = st.session_state[f"results_{file_name}"]

    st.subheader("Production and Consumption Plot")
    fig_prod_conso = plot_prod_conso(results["step_summary"])
    st.plotly_chart(fig_prod_conso, key=f"prod_conso_{file_name}")

    st.subheader("State of Charge Plot")
    fig_soc = plot_soc(results["step_summary"], results["assets"])
    st.plotly_chart(fig_soc, key=f"soc_{file_name}")



# def process_and_display(file_name, label, data):
#     input_exports_csv = ['ASSET_STEPS', 'ASSETS', 'CONGESTION_ASSETS', 'CONGESTIONS', 'OPERATION', 'VARIABLE_COST_MODELS']
#     input_exports_json = []
#     output_exports_csv = ['VIOLATIONS_OUTPUT']
#     output_exports_json = ['OPERATION_OUTPUT']
#     solve_state_exports_json = ['solve_status']

#     state_key = f"results_{file_name}"

#     if state_key not in st.session_state:
#         with st.spinner("Processing..."):
#             files_csv, files_json, log_decoded, step_summary, assets = process_log(
#                 data,
#                 input_exports_csv,
#                 input_exports_json,
#                 output_exports_csv,
#                 output_exports_json,
#                 solve_state_exports_json
#             )
#             st.session_state[state_key] = {
#                 "files_csv": files_csv,
#                 "files_json": files_json,
#                 "step_summary": step_summary,
#                 "assets": assets,
#             }

#     results = st.session_state[state_key]

#     datetime = results["step_summary"]["time"].min()
#     st.subheader(f'Datetime: {datetime}')

#     zip_buffer = create_zip(results["files_csv"], results["files_json"])
#     st.download_button(
#         label="⬇️ Download ZIP",
#         data=zip_buffer,
#         file_name=f"{str(datetime).replace(':', '-').replace(' ', '_')}_exports.zip",
#         mime="application/zip",
#         key=f"zip_{file_name}"
#     )

#     st.subheader("Production and Consumption Plot")
#     fig_prod_conso = plot_prod_conso(results["step_summary"])
#     st.plotly_chart(fig_prod_conso, key=f"prod_conso_{file_name}")

#     st.subheader("State of Charge Plot")
#     fig_soc = plot_soc(results["step_summary"], results["assets"])
#     st.plotly_chart(fig_soc, key=f"soc_{file_name}")


def get_tab_label(uploaded_file):
    """Extract completed_at date from file data, fallback to filename."""
    try:
        data = json.load(uploaded_file)
        uploaded_file.seek(0)  # Reset stream after reading
        return data["decision_optimization"]["status"]["completed_at"][:19], data
    except Exception:
        uploaded_file.seek(0)
        return uploaded_file.name, None


def main():
    st.title("Decision Optimization Log Viewer")

    uploaded_files = st.file_uploader(
        "Upload your log files",
        type=["txt", "json"],
        accept_multiple_files=True
    )

    if uploaded_files:

        launch_timestamps = {}
        results_timestamps = {}

        for uploaded_file in uploaded_files:

            file_name = uploaded_file.name

            try:
                data = json.load(uploaded_file)
            
            except Exception as e:
                
                print(f"Error while reading {file_name}: {e}")
                data = None

            if data is not None:
                process_file(file_name, data)
            
                launch_timestamps[file_name] = st.session_state[f"results_{file_name}"]["launch_timestamp"]
                results_timestamps[file_name] = st.session_state[f"results_{file_name}"]["results_timestamp"]

        sorted_timestamps = sorted([results_timestamps[file_name] for file_name in results_timestamps])
        selected_label = st.sidebar.radio("Files", sorted_timestamps)

        for file_name in launch_timestamps:

            if results_timestamps[file_name] == selected_label:

                col1, col2, col3 = st.columns([2,2,1])

                with col1:
                    st.subheader("Launch datetime")
                    st.caption("Paris TZ")
                    st.write(launch_timestamps[file_name])

                with col2:
                    st.subheader("First timestamp")
                    st.caption('Local TZ')
                    st.write(results_timestamps[file_name])

                with col3:
                    st.subheader(' ')
                    download_files(file_name, launch_timestamps[file_name], results_timestamps[file_name])

                display_files(file_name, launch_timestamps[file_name], results_timestamps[file_name])

                break

            
    # if uploaded_files:
    #     # Parse all files upfront to get tab labels
    #     files_data = []
    #     for uploaded_file in uploaded_files:
    #         label, data = get_tab_label(uploaded_file)
    #         if data is None:
    #             data = json.load(uploaded_file)
    #         files_data.append((uploaded_file.name, label, data))

    #     # Vertical tabs via radio in sidebar
    #     tab_labels = [label for _, label, _ in files_data]
        # selected_label = st.sidebar.radio("Files", tab_labels)

        # Display the selected tab content
        # for file_name, label, data in files_data:
        #     if label == selected_label:
        #         st.subheader(label)
        #         process_and_display(file_name, label, data)
        #         break


if __name__ == "__main__":
    main()