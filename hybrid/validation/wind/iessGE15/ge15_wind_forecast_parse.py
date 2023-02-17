from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import circmean
import copy
import csv

import matplotlib.pyplot as plt

def process_wind_forecast(forecast_files:dict, forecast_hours_ahead:dict, forecast_hours_offset:dict,
                            forecast_year:int, resource_fp, resource_years:list, plot_corr=False):

    # Set up forecasts as dict of dataframes
    max_hours_ahead = 0
    for value in forecast_hours_ahead.values():
        max_hours_ahead = max(max(value),max_hours_ahead)

    year_hours = pd.date_range(str(forecast_year)+'-01-01', periods=8760, freq='H')
    # TODO: Correct for leap year (know we're not using a leap year rn)
    forecast_dict = {}
    for key in forecast_files.keys():
        forecast_dict[key] = pd.DataFrame([], index=year_hours, columns=np.arange(0,max_hours_ahead+1))
    
    # Read in forecasts
    for key, forecast_fp in forecast_files.items():
        forecast_df = forecast_dict[key]
        file_df = pd.read_csv(forecast_fp, parse_dates=True, index_col=0)
        file_df.columns = forecast_hours_ahead[key]
        forecast_times = file_df.index
        # TODO: Correct for DST
        # For now: only have forecasts during DST, so just subtract 1 hour
        forecast_times = [i - pd.Timedelta(1,unit='H') for i in forecast_times]
        for i, hours_ahead in enumerate(forecast_hours_ahead[key]):
            hours_offset = pd.Timedelta(forecast_hours_offset[key][i],unit='H')
            offset_times = [i + hours_offset for i in forecast_times]
            forecast_df.loc[offset_times,hours_ahead] = file_df.loc[:,hours_ahead].values

    # Read in resource data
    resource_dict = {}
    for key in forecast_files.keys():
        resource_dict[key] = pd.DataFrame([], index=year_hours, columns=resource_years+['Avg.'])
    year_idx = str(resource_fp).find('YYYY')
    for year in resource_years:
        year_fp = Path(str(resource_fp)[:year_idx] + 
                        str(year) + 
                        str(resource_fp)[year_idx+4:])
        res_file_df = pd.read_csv(year_fp, skiprows=[0,1,3,4], header=0)
        res_file_df.index = year_hours
        res_file_df.columns = ['temp_C','pres_mbar','dir_deg','speed_m_s']
        for column in res_file_df.columns:
            resource_dict[column].loc[:,year] = res_file_df[column].values*(1+999*(column=='pres_mbar'))
        resource_dict['gusts_m_s'].loc[:,year] = res_file_df['speed_m_s'].values

    # Average years
    for key, resource in resource_dict.items():
        if key == 'dir_deg':
            resource['Avg.'] = circmean(resource.loc[:,resource_years],360,axis=1)
        else:
            resource['Avg.'] = np.mean(resource.loc[:,resource_years],axis=1)

    # Use average resource data as long-term forecast (>1 week out)
    for key, forecast in forecast_dict.items():
        forecast.iloc[:,-1] = resource_dict[key]['Avg.']

    resource_speed = resource_dict['speed_m_s'][forecast_year].values
    resource_dir = resource_dict['dir_deg'][forecast_year].values
    forecast_speed = forecast_dict['speed_m_s'][1].values
    forecast_gusts = forecast_dict['gusts_m_s'][1].values
    # Down-select to where there is positive speed, good direction , good status
    forecast_idxs = forecast_speed>0
    resource_idxs = resource_speed>0
    min_dir = 243
    max_dir = 310
    dir_idxs = (resource_dir>min_dir) & (resource_dir<max_dir)
    good_idxs = np.where(forecast_idxs & resource_idxs & dir_idxs)[0]
    
    # If no gust data, say gusts are equal to sustained winds
    col = forecast.shape[1]
    while col > 1:
        col -= 1
        forecast_speed = forecast_dict['speed_m_s'][col].values
        forecast_gusts = forecast_dict['gusts_m_s'][col].values
        no_gusts = np.where((forecast_speed>0) & np.isnan(forecast_gusts.astype(float)))[0]
        forecast_gusts[no_gusts] = forecast_speed[no_gusts]
    
    if plot_corr:
        # Plot correlation between sustained wind, gusts, and actual wind speed
        plt.clf()
        plt.errorbar(resource_speed[good_idxs],
                        forecast_speed[good_idxs],
                        fmt='.',
                        yerr=(np.vstack((np.zeros(len(good_idxs)),
                                np.subtract(forecast_gusts[good_idxs],
                                            forecast_speed[good_idxs])))))
        plt.xlabel('Actual wind speed [m/s]')
        plt.ylabel('Hour-ahead forecast wind speed [m/s] - sustained + gust')
        plt.ylim([0,np.max(forecast_gusts[good_idxs])])
        plt.show()

        # Plot correlation between forecast direction and actual direction
        resource_dir = resource_dict['dir_deg'][forecast_year].values
        forecast_dir = forecast_dict['dir_deg'][1].values
        plt.plot(resource_dir[forecast_idxs], forecast_dir[forecast_idxs],'.')
        plt.xlabel('Actual dir [deg]')
        plt.ylabel('Hour-ahead forecast direction [deg]')
        plt.show()
    
    # Develop correlation between sustained wind/gust forecast and actual wind speed
    # Sustained winds m/s = S, Gusts m/s = G, acutal wind speed m/s = W
    # A matrix: [S^2, S*G, G^2, S, G, ones], b vector: [W]
    S = forecast_speed[good_idxs]
    G = forecast_gusts[good_idxs]
    W = resource_speed[good_idxs]
    A_cols = [np.square(S),np.multiply(S,G),np.square(G),S,G,np.ones(len(S))]
    b = W
    A = np.hstack([np.transpose(np.array([i])) for i in A_cols])
    A_means = np.mean(A, axis=0)
    A_n = np.divide(A,A_means)
    b_mean = np.mean(b)
    b_n = np.divide(b,b_mean)
    results = np.linalg.lstsq(A_n.astype(float),b_n.astype(float))
    x = results[0]

    # Correct forecast with correlation 
    for col in range(forecast.shape[1]-1):
        rows = np.where(np.invert(np.isnan(forecast_dict['speed_m_s'][col].values.astype(float))))[0]
        S = forecast_dict['speed_m_s'].iloc[rows,col].values
        G = forecast_dict['gusts_m_s'].iloc[rows,col].values
        A_cols = [np.square(S),np.multiply(S,G),np.square(G),S,G,np.ones(len(S))]
        A = np.hstack([np.transpose(np.array([i])) for i in A_cols])
        A_n = np.divide(A,A_means)
        b_n = np.sum(np.multiply(A_n,x),axis=1)
        W = np.multiply(b_n,b_mean)
        forecast_dict['speed_m_s'].iloc[rows,col] = W

    # Fill in nans
    for key, forecast in forecast_dict.items():
        col = forecast.shape[1]-1
        while col > 1:
            not_nan = np.where(np.invert(np.isnan(forecast.iloc[:,col].astype(float))))[0]
            prev_not_nan = copy.deepcopy(not_nan)
            col -= 1
            fill_values = np.full(forecast.shape[0],np.nan)
            fill_values[prev_not_nan] = forecast.iloc[prev_not_nan,col+1]
            not_nan = np.where(np.invert(np.isnan(forecast.iloc[:,col].astype(float))))[0]
            fill_values[not_nan] = forecast.iloc[not_nan,col]
            forecast.iloc[:,col] = fill_values
            
    # Use forecast year resource data as real-time data (0 hours advance)
    for key, forecast in forecast_dict.items():
        forecast.loc[:,0] = resource_dict[key][forecast_year]

    if plot_corr:
        # Check corrected correlation
        forecast_speed = forecast_dict['speed_m_s'][1].values
        plt.clf()
        plt.plot(resource_speed[good_idxs],
                    forecast_speed[good_idxs],
                    '.')
        plt.plot([0,max(resource_speed[good_idxs])],
                    [0,max(resource_speed[good_idxs])])
        plt.xlabel('Actual wind speed [m/s]')
        plt.ylabel('Hour-ahead forecast wind speed [m/s] - CORRELATED')
        plt.show()

    return forecast_dict


def save_wind_forecast_SAM(forecast_dict, time, orig_fp):

    with open(orig_fp) as fin:
        reader = csv.reader(fin)
        n_header_lines = 5
        lines = []
        for line in range(8760+n_header_lines):
            lines.append(reader.__next__())

    new_fp = Path(str(orig_fp)[:-4]+
                  '_{:02d}'.format(time.month)+
                  '_{:02d}'.format(time.day)+
                  '_{:02d}'.format(time.hour)+
                  '.srw')

    cols = ['temp_C','pres_mbar','dir_deg','speed_m_s']
    current_idx = forecast_dict[cols[0]].index.to_list().index(time)
    
    for key, forecast in forecast_dict.items():
        if key in cols:
            col_idx = cols.index(key)
            for forecast_row in range(current_idx,8760):
                forecast_col = min(forecast.shape[1]-1,forecast_row-current_idx)
                forecast_val = forecast.iloc[forecast_row,forecast_col]
                if key == 'pres_mbar':
                    forecast_val /= 1000
                lines[forecast_row+n_header_lines][col_idx] = forecast_val

    with open(new_fp, 'w', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerows(lines)

    return new_fp