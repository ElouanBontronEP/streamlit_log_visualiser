import pandas as pd
import numpy as np
import plotly.graph_objects as go

def plot_prod_conso(step_summary):
    
    fig = go.Figure()

    type_to_colors = {
        'load': "#3341FF",
        'intermittent': "#FFC933",
        'generator': "#1EA53C",
        'storage': "#33E0FF"
    }

    for col in step_summary.columns:

        if col.endswith('_kw') and 'curtailment' not in col:

            type = col.split('_')[-3]

            if 'storage' in col:
                type = 'storage'

            fig.add_trace(
                go.Bar(
                    x=step_summary['time'],
                    y=step_summary[col],
                    name=col,
                    marker_color=type_to_colors.get(type, '#000000')
                )
            ) 

        elif col.endswith('_curtailment_kw'):

            fig.add_trace(
                go.Scatter(
                    x=step_summary['time'],
                    y=step_summary[col[:-15]+'_kw'] + step_summary[col],
                    name=col,
                    marker_color="#FFA033"
                )
            )
        
    fig.update_layout(
        # title="Power Target ELECTRICITY [kW]",
        barmode="relative",   # clé pour stacking positif/négatif
        template="simple_white",
        xaxis_title="Time",
        yaxis_title="Power [kW]",
        legend=dict(orientation="v")
    )

    return fig

def plot_soc(step_summary, assets):

    fig = go.Figure()

    storage_cols = [col for col in step_summary.columns if col.endswith('_soc')]

    for col in storage_cols:
        fig.add_trace(
            go.Scatter(
                x=step_summary['time'],
                y=step_summary[col],
                name=col,
                mode='lines+markers'
            )
        )

        asset_id = col[:-14]
        max_soc = assets.loc[assets['asset_id'] == asset_id, 'max_SOC'].iloc[0]
        min_soc = assets.loc[assets['asset_id'] == asset_id, 'min_SOC'].iloc[0]

        fig.add_trace(
            go.Scatter(
                x=[step_summary['time'].min(), step_summary['time'].max()],
                y=[max_soc, max_soc],
                name=col.replace('_soc', '_max_soc'),
                mode='lines',
                line=dict(dash='dash', color='red')
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[step_summary['time'].min(), step_summary['time'].max()],
                y=[min_soc, min_soc],
                name=col.replace('_soc', '_min_soc'),
                mode='lines',
                line=dict(dash='dash', color='red')
            )
        )

    fig.update_layout(
        # title="State of Charge over Time",
        xaxis_title="Time",
        yaxis_title="State of Charge (%)",
        legend_title="Storage Assets",
        template="simple_white"
    )

    return fig