import pandas as pd
import numpy as np
import json
import base64
import datetime as dt

def process_log(data, input_exports_csv, input_exports_json, output_exports_csv, output_exports_json, solve_state_exports_json):

    files_csv = {}
    files_json = {}

    decision_optimisation = data["decision_optimization"]
    input_data = decision_optimisation["input_data"]
    output_data = decision_optimisation["output_data"]
    output_data_references = decision_optimisation["output_data_references"]
    solve_parameters = decision_optimisation["solve_parameters"]
    solve_state = decision_optimisation["solve_state"]
    status = decision_optimisation["status"]

    inputs = {}
    for i in range(len(input_data)):
        inputs[f'{input_data[i]["id"]}'[:-4]] = pd.DataFrame(input_data[i]["values"], columns=input_data[i]["fields"])

    inputs["ASSETS"]['compensation_model'] = inputs["ASSETS"]['compensation_model'].astype("str")
    inputs["ASSETS"]['var_cost_model'] = inputs["ASSETS"]['var_cost_model'].astype("str")
    inputs['ASSETS'].loc[inputs['ASSETS']['compensation_model'] == "-1.0", 'compensation_model'] = "NO_COMPENSATION_MODEL"
    inputs['ASSETS'].loc[inputs['ASSETS']['var_cost_model'] == "-1.0", 'var_cost_model'] = "NO_VAR_COST_MODEL"

    for id in input_exports_csv:
        files_csv[id] = inputs[id]
    for id in input_exports_json:
        files_json[id] = inputs[id]

    outputs = {}
    for i in range(len(output_data)):
        if output_data[i]["id"][-4:] == ".csv" and 'HEADER' not in output_data[i]["id"] and 'EMPTY' not in output_data[i]["id"]:
            outputs[f'{output_data[i]["id"]}'[:-4]] = pd.DataFrame(output_data[i]["values"], columns=output_data[i]["fields"])
        elif output_data[i]["id"] == "log.txt":
            log_encoded = output_data[i]["content"]

    for id in output_exports_csv:
        files_csv[id] = outputs[id]
    for id in output_exports_json:
        files_json[id] = outputs[id]

    for id in solve_state_exports_json:
        files_json[id] = solve_state[id]

    log_decoded = base64.b64decode(log_encoded).decode('utf-8')

    asset_steps_output = outputs['ASSET_STEPS_OUTPUT']
    steps_link = inputs['OPERATION_STEPS_LINK']
    assets = inputs['ASSETS']

    load_assets = assets[assets['type'] == 'LOAD'].copy()
    intermittent_assets = assets[assets['type'] == 'INTERMITTENT'].copy()
    generator_assets = assets[assets['type'] == 'GENERATOR'].copy()
    storage_assets = assets[assets['type'] == 'STORAGE'].copy()

    load_steps = {}
    for i in range(load_assets.shape[0]):
        id = load_assets.iloc[i]['asset_id']
        df = asset_steps_output[asset_steps_output['asset_id'] == id].copy()
        df[f'{id}_load_{i}_kw'] = df['power_target']
        load_steps[f'{id}_load_{i}'] = df[['step_id', f'{id}_load_{i}_kw']]

    intermittent_steps = {}
    for i in range(intermittent_assets.shape[0]):
        id = intermittent_assets.iloc[i]['asset_id']
        df = asset_steps_output[asset_steps_output['asset_id'] == id].copy()
        df[f'{id}_intermittent_{i}_kw'] = df['power_target']
        df[f'{id}_intermittent_{i}_curtailment_kw'] = df['curtailment_target']
        intermittent_steps[f'{id}_intermittent_{i}'] = df[['step_id', f'{id}_intermittent_{i}_kw', f'{id}_intermittent_{i}_curtailment_kw']]

    generator_steps = {}
    for i in range(generator_assets.shape[0]):
        id = generator_assets.iloc[i]['asset_id']
        df = asset_steps_output[asset_steps_output['asset_id'] == id].copy()
        df[f'{id}_generator_{i}_kw'] = df['power_target']
        generator_steps[f'{id}_generator_{i}'] = df[['step_id', f'{id}_generator_{i}_kw']]

    storage_steps = {}
    for i in range(storage_assets.shape[0]):
        id = storage_assets.iloc[i]['asset_id']
        df = asset_steps_output[asset_steps_output['asset_id'] == id].copy()
        df[f'{id}_storage_{i}_power_kw'] = df['power_target']
        df[f'{id}_storage_{i}_state'] = df['power_target'].apply(lambda x : 'discharge' if x<0 else ('charge' if x>0 else 'idle'))
        df[f'{id}_storage_{i}_energy_KWh'] = df['storage_target']
        if df['target_soc'].max() == 0:
            df[f'{id}_storage_{i}_soc'] = 100*df['storage_target']/storage_assets.iloc[i]['max_energy']
        else:
            df[f'{id}_storage_{i}_soc'] = df['target_soc']
        storage_steps[f'{id}_storage_{i}'] = df[['step_id', f'{id}_storage_{i}_power_kw', f'{id}_storage_{i}_state', f'{id}_storage_{i}_energy_KWh', f'{id}_storage_{i}_soc']]

    step_summary = pd.concat([df.set_index('step_id') for df in load_steps.values()] +
                    [df.set_index('step_id') for df in intermittent_steps.values()] +
                    [df.set_index('step_id') for df in generator_steps.values()] +
                    [df.set_index('step_id') for df in storage_steps.values()], axis=1)
    
    step_summary.reset_index(inplace=True)

    step_summary = pd.merge(steps_link[['asset_step', 'asset_step_day_local_time', 'asset_step_hour_local_time', 'asset_step_minute_local_time']], step_summary, left_on='asset_step', right_on='step_id', how='right')
    step_summary.drop(columns=['step_id'], inplace=True)
    step_summary = step_summary.rename(columns={'asset_step': 'step_id'})

    launch_timestamp = str(status['completed_at'])

    date_launch = launch_timestamp[:10]
    day_launch = int(date_launch[8:10])
    month_launch = int(date_launch[5:7])
    year_launch = int(date_launch[:4])

    days_by_months = {
        1: 31,
        2: 29 if (year_launch % 4 == 0 and year_launch % 100 != 0) or (year_launch % 400 == 0) else 28,
        3: 31,
        4: 30,
        5: 31,
        6: 30,
        7: 31,
        8: 31,
        9: 30,
        10: 31,
        11: 30,
        12: 31
    }

    step_summary['month'] = month_launch
    step_summary['year'] = year_launch

    if day_launch == days_by_months[month_launch]:

        new_month = (step_summary['asset_step_day_local_time'] == 1)
        not_december = (step_summary['month'] != 12)
        step_summary.loc[new_month & not_december, 'month'] = step_summary.loc[new_month & not_december, 'month'] + 1
        step_summary.loc[new_month & ~not_december, 'month'] = 1
        step_summary.loc[new_month & ~not_december, 'year'] = step_summary.loc[new_month & ~not_december, 'year'] + 1

    elif day_launch == 1:
        days_in_month = step_summary['month'].map(days_by_months)
        new_month = (step_summary['asset_step_day_local_time'] == days_in_month)
        not_january = (step_summary['month'] != 1)
        step_summary.loc[new_month & not_january, 'month'] = step_summary.loc[new_month & not_january, 'month'] - 1
        step_summary.loc[new_month & ~not_january, 'month'] = 12
        step_summary.loc[new_month & ~not_january, 'year'] = step_summary.loc[new_month & ~not_january, 'year'] - 1        

    step_summary['time'] = pd.to_datetime({
        'year': step_summary['year'],
        'month': step_summary['month'],
        'day': step_summary['asset_step_day_local_time'],
        'hour': step_summary['asset_step_hour_local_time'],
        'minute': step_summary['asset_step_minute_local_time']
    })
    
    step_summary['power_balance'] = step_summary[[col for col in step_summary.columns if col.endswith('_kw') and 'curtailment' not in col]].sum(axis=1)

    step_summary['is_power_balance_ok'] = step_summary['power_balance'].abs() < 0.01

    step_summary['active_generators'] = ''
    step_summary['event'] = ''

    for i in range(generator_assets.shape[0]):
        id = generator_assets.iloc[i]['asset_id']
        is_active = (step_summary[f'{id}_generator_{i}_kw'] < 0)
        is_initial_active = generator_assets.iloc[i]['initial_power'] < 0
        prev_active = is_active.shift(fill_value=is_initial_active)
        power_on = (~prev_active) & (is_active)
        power_off = (prev_active) & (~is_active)
        step_summary.loc[power_on, 'event'] = step_summary.loc[power_on, 'event'] + f'{id}_generator_{i} started / '
        step_summary.loc[power_off, 'event'] = step_summary.loc[power_off, 'event'] + f'{id}_generator_{i} stopped / '
        step_summary.loc[is_active, 'active_generators'] = step_summary.loc[is_active, 'active_generators'] + f'{id}_generator_{i} / '

    for i in range(storage_assets.shape[0]):
        id = storage_assets.iloc[i]['asset_id']
        is_charging = step_summary[f'{id}_storage_{i}_power_kw'] > 0
        is_discharging = step_summary[f'{id}_storage_{i}_power_kw'] < 0
        is_initial_charging = storage_assets.iloc[i]['initial_power'] > 0
        is_initial_discharging = storage_assets.iloc[i]['initial_power'] < 0
        prev_charging = is_charging.shift(fill_value=is_initial_charging)
        prev_discharging = is_discharging.shift(fill_value=is_initial_discharging)
        charging = (~prev_charging) & (is_charging)
        discharging = (~prev_discharging) & (is_discharging)
        step_summary.loc[charging, 'event'] = step_summary.loc[charging, 'event'] + f'{id}_storage_{i} started charging / '
        step_summary.loc[discharging, 'event'] = step_summary.loc[discharging, 'event'] + f'{id}_storage_{i} started discharging / '
        step_summary.loc[~is_charging & prev_charging, 'event'] = step_summary.loc[~is_charging & prev_charging, 'event'] + f'{id}_storage_{i} stopped charging / '
        step_summary.loc[~is_discharging & prev_discharging, 'event'] = step_summary.loc[~is_discharging & prev_discharging, 'event'] + f'{id}_storage_{i} stopped discharging / '
   
    for i in range(intermittent_assets.shape[0]):
        id = intermittent_assets.iloc[i]['asset_id']
        initial_power = intermittent_assets.iloc[i]['initial_power']
        power_change = step_summary[f'{id}_intermittent_{i}_kw'] - step_summary[f'{id}_intermittent_{i}_kw'].shift(fill_value=initial_power)
        brutal_change = power_change.abs() > abs(0.1*intermittent_assets.iloc[i]['min_power'])
        msg = pd.Series('', index=step_summary.index)

        msg.loc[brutal_change] = (
            f'{id}_intermittent_{i} power changed by '
            + power_change.loc[brutal_change].round(0).astype(str)
            + ' kW / '
        )

        step_summary['event'] = step_summary['event'] + msg
   
    files_csv['step_summary'] = step_summary

    launch_timestamp = str(status['completed_at'])
    results_timestamp = str(step_summary['time'].min())

    site_id = inputs['SITE_STEPS']['site_id'].unique()[0] # assuming only one site per log for now
   
    return files_csv, files_json, log_decoded, step_summary, assets, launch_timestamp, results_timestamp, site_id

