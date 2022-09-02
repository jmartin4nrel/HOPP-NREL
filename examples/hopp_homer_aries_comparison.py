from pathlib import Path
import json
from tabnanny import filename_only
from tkinter.ttk import Style
from turtle import width
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Import HOPP results
filepath = 'results/' + 'yearlong_outputs_batt.json'
hopp_results = pd.read_json(filepath)
hopp_solar = hopp_results.loc[:,'pv generation (kW)']
hopp_wind = hopp_results.loc[:,'wind generation (kW)']
hopp_batt_neg = hopp_results.loc[:,'battery charge (kW)']
hopp_batt_pos = hopp_results.loc[:,'battery discharge (kW)']
hopp_batt_soc = hopp_results.loc[:,'dispatch battery SOC (%)']
hopp_load = hopp_results.loc[:,'load (kW)']
hopp_hy_pow = hopp_results.loc[:,'optimized dispatch (kW)']
hopp_grid_pow = hopp_results.loc[:,'grid supplied load (kW)']
hopp_solar = pd.concat([hopp_solar.loc[4343:],hopp_solar.loc[:4342]])
hopp_batt_val = np.sum([hopp_batt_neg.values,hopp_batt_pos.values],axis=0)
hopp_index = pd.date_range(start="2021-06-30 23:00:00", periods=8760, freq="h")
hopp_solar.index = hopp_index
hopp_wind.index = hopp_index
hopp_batt = pd.DataFrame(data=hopp_batt_val,index=hopp_index)
hopp_batt_soc.index = hopp_index
hopp_load.index = hopp_index
hopp_hy_pow.index = hopp_index
hopp_grid_pow.index = hopp_index
hopp_results = pd.concat([hopp_solar,hopp_wind,hopp_batt,hopp_batt_soc,hopp_load,hopp_hy_pow,hopp_grid_pow],axis=1) 
hopp_results.columns = ['Solar','Wind','Battery','Battery SOC','Load','Hybrid Plant Power','Grid Power Needed']

# Import other HOPP results for comparison
filepath = 'results/' + 'yearlong_outputs_batt.json'
hopp_results_comparison = pd.read_json(filepath)
hopp_solar = hopp_results_comparison.loc[:,'pv generation (kW)']
hopp_wind = hopp_results_comparison.loc[:,'wind generation (kW)']
hopp_batt_pos = hopp_results_comparison.loc[:,'battery discharge (kW)']
hopp_batt_soc = hopp_results_comparison.loc[:,'dispatch battery SOC (%)']
hopp_solar = pd.concat([hopp_solar.loc[4343:],hopp_solar.loc[:4342]])
hopp_solar.index = hopp_index
hopp_wind.index = hopp_index
hopp_batt = pd.DataFrame(data=hopp_batt_val,index=hopp_index)
hopp_batt_soc.index = hopp_index
hopp_results_comparison = pd.concat([hopp_solar,hopp_wind,hopp_batt,hopp_batt_soc],axis=1) 
hopp_results_comparison.columns = ['Solar','Wind','Battery','Battery SOC']

filepath = 'results/' + 'yearlong_wind_misalignment.json'
pitch_misalignment = pd.read_json(filepath)

# Import HOMER results
filepath = 'results/' + 'yearlong_homer_output.csv'
homer_results = pd.read_csv(filepath)
homer_solar = homer_results.loc[:,'Generic flat plate PV Power Output, kW']
homer_wind = homer_results.loc[:,'GE 1.5 MW Power Output, kW']
homer_gen = pd.concat([homer_solar,homer_wind],axis=1)
homer_gen.index = pd.date_range(start="2021-06-30 23:00:00", periods=8760, freq="h")
homer_gen.columns = ['Solar','Wind']

# Import ARIES generation
filepath = 'resource_files/' + 'yearlong_aries_generation.csv'
aries_gen = pd.read_csv(filepath)
aries_gen.index = pd.date_range(start="2021-06-30 23:00:00", periods=8760, freq="h")
aries_gen.columns = ['Solar','Wind']

# Convert turbine status to codes
filepath = 'resource_files/' + 'yearlong_ge15_turbine_status.csv'
turbine_status = pd.read_csv(filepath)
turbine_status = turbine_status.loc[:,'Turbine Status'].values
for idx, value in enumerate(turbine_status):
    if value == 7:
        newvalue = 5
    elif value == 5 or value == 6:
        newvalue = 6
    elif value > 7:
        newvalue = 6
    else:
        newvalue = value
    turbine_status[idx] = newvalue
codes = ['*NO DATA*',
    'Turbine OK',
    'Grid Connection',
    'Running/Idle',
    'Maintenance',
    'Weather Conditions',
    'Other']

# Parse results
hopp_solar = hopp_results.loc[:,'Solar']*305/430 # 125 kW PV inverter was out
hopp_solar_comparison = hopp_results_comparison.loc[:,'Solar']*305/430
hopp_wind = hopp_results.loc[:,'Wind']
hopp_wind_comparison = hopp_results_comparison.loc[:,'Wind']
hopp_batt = hopp_results.loc[:,'Battery']
hopp_batt_soc = hopp_results.loc[:,'Battery SOC']
hopp_load = hopp_results.loc[:,'Load']
hopp_hy_pow = hopp_results.loc[:,'Hybrid Plant Power']
hopp_grid_pow = hopp_results.loc[:,'Grid Power Needed']
homer_solar = homer_gen.loc[:,'Solar']*305/430
homer_wind = homer_gen.loc[:,'Wind']
aries_solar = aries_gen.loc[:,'Solar']
aries_wind = aries_gen.loc[:,'Wind']

# Zero out negative solar from ARIES
zero_inds = aries_solar.values<0
aries_solar.iloc[zero_inds] = 0

# Plot results
start = '2022-06-05'
end = '2022-06-18'
start_dt = pd.to_datetime(start)
end_dt = pd.to_datetime(end)
hopp_label = 'HOPP Modeled Output'
homer_label = 'HOMER Modeled Output'
act_label = 'Actual Power Output'
label_mod = ', DC:AC ratio = 1.3'
hopp_batt_label = 'HOPP Modeled (Commanded) Output'
hopp_soc_label = 'HOPP Modeled SOC'

# Export selected results to .csv
short_df = pd.concat([hopp_solar,homer_solar,aries_solar,hopp_wind,homer_wind,aries_wind],axis=1)
short_df.columns = ['HOPP Solar [kW]','HOMER Solar','ARIES Solar [kW]','HOPP Wind [kW]','HOMER Wind [kW]','ARIES Wind [kW]']
short_df = short_df.loc[start_dt:end_dt]
examples_dir = Path(__file__).parent.absolute()
filename = 'yearlong_outputs_selected.csv'
short_df.to_csv(str(examples_dir) + '/results/' + filename)

plt.subplot(4,1,1)
plt.plot(hopp_solar.index,hopp_solar.values,label=hopp_label,color='C0')
# plt.plot(hopp_solar.index,hopp_solar_comparison.values,'--',label=hopp_label+label_mod,color='C0')
# plt.plot(homer_solar.index,homer_solar.values,label=homer_label,color='C2')
plt.plot(aries_solar.index,aries_solar.values,label=act_label,color='C1')
plt.ylabel("First Solar 430 kW PV [kW]")
plt.legend(ncol=4)
plt.ylim([0,500])
plt.xlim([start_dt,end_dt])

plt.subplot(4,1,2)
plt.plot(hopp_wind.index,hopp_wind.values,label=hopp_label,color='C0')
# plt.plot(hopp_wind.index,hopp_wind_comparison.values,'--',label=hopp_label+label_mod,color='C0')
# plt.plot(homer_wind.index,homer_wind.values,label=homer_label,color='C2')
plt.plot(aries_wind.index,aries_wind.values,label=act_label,color='C1')
plt.ylabel("GE 1.5 MW Turbine [kW]")
plt.legend(ncol=3)
plt.ylim([0,1600])
plt.xlim([start_dt,end_dt])

plt.subplot(4,1,3)

# plt.plot(hopp_wind.index,pitch_misalignment.loc['Pitch'].values,label='Pitch')
# plt.plot(hopp_wind.index,pitch_misalignment.loc['Yaw Misalignment'].values,label='Yaw Misalignment')
# plt.ylabel("Angle [degrees]")
# plt.legend()

# plt.plot(hopp_wind.index,turbine_status)
# plt.ylim([-.5,6.5])
# plt.xlim([start_dt,end_dt])
# Ax = plt.gca()
# Ax.set_yticks([0,1,2,3,4,5,6])
# Ax.set_yticklabels(codes)
# plt.grid(axis='y')
# plt.ylabel('Turbine Status')

plt.plot(hopp_batt.index,hopp_batt.values*0,'--',color='k',linewidth=.5)
plt.plot(hopp_batt.index,hopp_batt.values,label=hopp_label,color='C0')
plt.ylabel('1 MW BESS [kW]',color='C0')
plt.xlim([start_dt,end_dt])
plt.ylim([-600,600])
ax1 = plt.gca()
ax2 = plt.twinx(ax1)
ax2.plot(-1,-1,label=hopp_batt_label,color='C0')
ax2.plot(hopp_batt_soc.index,hopp_batt_soc.values,label=hopp_soc_label,color='C2')
plt.ylabel('1 MW BESS SOC [%]',color='C2')
plt.legend(ncol=3)
plt.xlim([start_dt,end_dt])
plt.ylim([0,100])

plt.subplot(4,1,4)

plt.plot(hopp_load.index,hopp_load.values,color='C1',label='Building Load')
# plt.plot(hopp_hy_pow.index,hopp_hy_pow.values+hopp_grid_pow.values,'--',color='C0')
plt.plot(hopp_hy_pow.index,hopp_wind.values+hopp_solar.values+hopp_batt.values,'--',color='C0',label='HOPP Modeled Wind/Solar/Batt Hybrid Output')
# plt.plot(hopp_grid_pow.index,hopp_grid_pow.values,color='C1',label='Grid Just Bought')
plt.plot(hopp_load.index,hopp_load.values-(hopp_wind.values+hopp_solar.values+hopp_batt.values),'--',color='C2',label='HOPP Modeled Grid Electricity Bought/Sold')
plt.xlim([start_dt,end_dt])
plt.legend(ncol=3)
plt.ylim([-800,1000])
plt.ylabel('Other Measurements [kW]')
plt.plot(hopp_batt.index,hopp_batt.values*0,'--',color='k',linewidth=.5)

plt.show()

asdf