"""
multi_location_MeOH.py

Simulates 600 MW wind plants over a targeted region of the US for H2 electrolysis
(& eventual MeOH production w/NGCC plant captured CO2)
"""

from email.base64mime import header_length
import os
import sys
import pandas as pd
import numpy as np
import multiprocessing
import operator
from pathlib import Path
from itertools import repeat
import time
rng = np.random.default_rng()

from hybrid.keys import set_nrel_key_dot_env
from hybrid.log import analysis_logger as logger
from hybrid.sites import SiteInfo
from hybrid.sites import flatirons_site as sample_site
from hybrid.hybrid_simulation import HybridSimulation
from tools.analysis import create_cost_calculator
from tools.resource import *
from tools.resource.resource_loader import site_details_creator

resource_dir = Path(__file__).parent.parent.parent / "resource_files"

pd.set_option("display.max_rows", None, "display.max_columns", None)

set_nrel_key_dot_env()


def establish_save_output_dict():
    """
    Establishes and returns the base 'save_outputs' dictionary
    for storing all analysis variables.
    """
    # Establishes and returns a 'save_outputs' dict for saving the relevant analysis variables.
    save_outputs = dict()
    save_outputs['Scenario Description'] = list()
    save_outputs['Solar (%)'] = list()
    save_outputs['Solar (MW)'] = list()
    save_outputs['Wind (MW)'] = list()
    save_outputs['AEP (GWh)'] = list()
    save_outputs['Solar AEP (GWh)'] = list()
    save_outputs['Wind AEP (GWh)'] = list()
    save_outputs['Solar Capacity Factor'] = list()
    save_outputs['Capacity Factor'] = list()
    save_outputs['Wind Capacity Factor'] = list()
    save_outputs['Capacity Factor of Interconnect'] = list()
    save_outputs['NPV ($-million)'] = list()
    save_outputs['LCOE - Nominal'] = list()
    save_outputs['LCOE - Real'] = list()
    save_outputs['IRR (%)'] = list()
    save_outputs['PPA Price Used'] = list()
    save_outputs['TOD Profile Used'] = list()
    save_outputs['Revenue (PPA)'] = list()
    save_outputs['Revenue (TOD)'] = list()
    save_outputs['BOS Cost'] = list()
    save_outputs['BOS Cost percent reduction'] = list()
    save_outputs['Cost / MWh Produced'] = list()
    save_outputs['Cost / MWh Produced percent reduction'] = list()
    save_outputs['Percentage Curtailment'] = list()
    save_outputs['Pearson R Wind V Solar'] = list()

    return save_outputs


def establish_save_outputs_resource_loop_dict():
    """
    Establishes and returns a 'save_outputs_resource_loop' dict
    for saving the relevant analysis variables for each site.
    """

    save_outputs_resource_loop = dict()
    save_outputs_resource_loop['Site Lat'] = list()
    save_outputs_resource_loop['Site Lon'] = list()
    save_outputs_resource_loop['PPA Price'] = list()
    save_outputs_resource_loop['Wind Size(MW)'] = list()
    save_outputs_resource_loop['Solar Size(MW)'] = list()
    save_outputs_resource_loop['Hybrid Size(MW)'] = list()
    # save_outputs_resource_loop['Wind AEP (GWh)'] = list()
    # save_outputs_resource_loop['Solar AEP (GWh)'] = list()
    save_outputs_resource_loop['Hybrid AEP (GWh)'] = list()
    # save_outputs_resource_loop['Wind NPV ($-million)'] = list()
    # save_outputs_resource_loop['Solar NPV ($-million)'] = list()
    save_outputs_resource_loop['Hybrid NPV ($-million)'] = list()
    # save_outputs_resource_loop['Wind LCOE (real)'] = list()
    # save_outputs_resource_loop['Solar LCOE (real)'] = list()
    save_outputs_resource_loop['Hybrid LCOE (real)'] = list()
    # save_outputs_resource_loop['Wind Cost / MWh Produced'] = list()
    # save_outputs_resource_loop['Solar Cost / MWh Produced'] = list()
    save_outputs_resource_loop['Hybrid Cost / MWh Produced'] = list()
    # save_outputs_resource_loop['Solar Beats Wind AEP'] = list()
    # save_outputs_resource_loop['Solar Beats Wind NPV'] = list()
    # save_outputs_resource_loop['Solar Beats Wind Cost/MWh'] = list()
    # save_outputs_resource_loop['Max AEP Index'] = list()
    # save_outputs_resource_loop['Max AEP Value'] = list()
    # save_outputs_resource_loop['Max NPV Index'] = list()
    # save_outputs_resource_loop['Max NPV Value'] = list()
    # save_outputs_resource_loop['Cost / MWh Produced reduction (%)'] = list()
    # save_outputs_resource_loop['LCOE(real) reduction (%)'] = list()
    # save_outputs_resource_loop['LCOE(real) reduction (%) vs wind'] = list()
    # save_outputs_resource_loop['NPV Benefit ($-million) Hybrid Vs. Wind'] = list()
    # save_outputs_resource_loop['Wind BOS Cost'] = list()
    # save_outputs_resource_loop['Solar BOS Cost'] = list()
    save_outputs_resource_loop['Hybrid BOS Cost'] = list()
    # save_outputs_resource_loop['Wind Capacity Factor'] = list()
    # save_outputs_resource_loop['Solar Capacity Factor'] = list()
    # save_outputs_resource_loop['Interconnect Capacity Factor (Wind Case)'] = list()
    # save_outputs_resource_loop['Interconnect Capacity Factor (Solar Case)'] = list()
    save_outputs_resource_loop['Interconnect Capacity Factor (Hybrid Case)'] = list()
    # save_outputs_resource_loop['Percentage Curtailment (Wind)'] = list()
    # save_outputs_resource_loop['Percentage Curtailment (Solar)'] = list()
    save_outputs_resource_loop['Percentage Curtailment (Hybrid)'] = list()
    # save_outputs_resource_loop['Pearson R Wind V Solar'] = list()
    save_outputs_resource_loop['Solar File Used'] = list()
    save_outputs_resource_loop['Wind File Used'] = list()
    save_outputs_resource_loop['Time Zone (for solar)'] = list()

    return save_outputs_resource_loop


def run_hopp_calc(Site, scenario_description, bos_details, total_hybrid_plant_capacity_mw, solar_size_mw, wind_size_mw,
                    nameplate_mw, interconnection_size_mw, load_resource_from_file,
                    ppa_price, results_dir):
    """ run_hopp_calc Establishes sizing models, creates a wind or solar farm based on the desired sizes,
     and runs SAM model calculations for the specified inputs.
     save_outputs contains a dictionary of all results for the hopp calculation.

    :param scenario_description: Project scenario - 'greenfield' or 'solar addition'.
    :param bos_details: contains bos details including type of analysis to conduct (cost/mw, json lookup, HybridBOSSE).
    :param total_hybrid_plant_capacity_mw: capacity in MW of hybrid plant.
    :param solar_size_mw: capacity in MW of solar component of plant.
    :param wind_size_mw: capacity in MW of wind component of plant.
    :param nameplate_mw: nameplate capacity of total plant.
    :param interconnection_size_mw: interconnection size in MW.
    :param load_resource_from_file: flag determining whether resource is loaded directly from file or through
     interpolation routine.
    :param ppa_price: PPA price in USD($)
    :return: collection of outputs from SAM and hybrid-specific calculations (includes e.g. AEP, IRR, LCOE),
     plus wind and solar filenames used
    (save_outputs)
    """
    # Get resource data
    if load_resource_from_file:
        pass
    else:
        Site['resource_filename_solar'] = ""  # Unsetting resource filename to force API download of wind resource
        Site['resource_filename_wind'] = ""  # Unsetting resource filename to force API download of solar resource

    # print('Establishing site number {}'.format(Site['site_num']))
    
    site = SiteInfo(Site, solar_resource_file=Site['resource_filename_solar'],
                    wind_resource_file=Site['resource_filename_wind'])

    #TODO: Incorporate this in SiteInfo
    # if 'roll_tz' in Site.keys():
    #     site.solar_resource.roll_timezone(Site['roll_tz'], Site['roll_tz'])

    # Set up technology and cost model info
    turb_rating_kw = 2000
    num_turbines = int(wind_size_mw * 1000 / turb_rating_kw)
    technologies = {'pv': {
                        'system_capacity_kw': solar_size_mw * 1000
                    },          # mw system capacity
                    'wind': {
                        'num_turbines': num_turbines,
                        'turbine_rating_kw': turb_rating_kw
                    },
                    'grid': interconnection_size_mw}    # mw interconnect

    # Create model
    hybrid_plant = HybridSimulation(technologies, site, interconnect_kw=interconnection_size_mw * 1000)

    hybrid_plant.setup_cost_calculator(create_cost_calculator(interconnection_size_mw,
                                                              bos_details['BOSSource'],
                                                              scenario_description,
                                                              modify_costs=bos_details['Modify Costs'],
                                                              cost_reductions=bos_details))

    hybrid_plant.ppa_price = ppa_price
    hybrid_plant.discount_rate = 6.4
    hybrid_plant.pv.system_capacity_kw = solar_size_mw * 1000
    hybrid_plant.pv.dc_degradation = (0,)
    hybrid_plant.wind.wake_model = 3
    actual_solar_pct = hybrid_plant.pv.system_capacity_kw / \
                       (hybrid_plant.pv.system_capacity_kw + hybrid_plant.wind.system_capacity_kw)

    logger.info("Run with solar percent {}".format(actual_solar_pct))
    hybrid_plant.simulate()
    outputs = hybrid_plant.hybrid_outputs()
    for k, v in outputs.items():
        outputs[k] = [v]

    return outputs, site.wind_resource.filename, site.solar_resource.filename


def run_hybrid_calc(year, site_num, scenario_descriptions, results_dir, load_resource_from_file,
                    resource_filename_wind, resource_filename_solar, site_lat, site_lon,
                    wind_size, solar_size, hybrid_size, interconnection_size,
                    bos_details, ppa_price, solar_tracking_mode, hub_height, correct_wind_speed_for_height, all_run_dir):
    """
    run_hybrid_calc loads the specified resource for each site, and runs wind, solar, hybrid and solar addition
    scenarios by calling run_hopp_calc for each scenario. Returns a DataFrame of all results for the supplied site
    :param year: year for which analysis is conducted
    :param site_num: number representing the site studied. Generally 1 to num sites to be studied.
    :param scenario_descriptions: description of scenario type, e.g. wind only, solar only, hybrid.
    :param results_dir: path to results directory.
    :param load_resource_from_file: flag determining whether resource is loaded from file directly or other routine.
    :param resource_filename_wind: filename of wind resource file.
    :param resource_filename_solar: filename of solar resource file.
    :param site_lat: site latitude (degrees).
    :param site_lon: site longitude (degrees).
    :param wind_size: capacity in MW of wind component of plant.
    :param solar_size: capacity in MW of solar component of plant.
    :param hybrid_size: capacity in MW of hybrid plant.
    :param interconnection_size: capacity in MW of interconnection.
    :param bos_details: contains bos details including type of analysis to conduct (cost/mw,
     json lookup, HybridBOSSE).
    :param ppa_price: PPA price in USD($).
    :param solar_tracking_mode: solar tracking mode (e.g. fixed, single-axis, two-axis).
    :param hub_height: hub height in meters.
    :param correct_wind_speed_for_height: (boolean) flag determining whether wind speed is extrapolated
     to hub height.
    :param all_run_dir: path to directory for results from all runs
    :return: save_outputs_resource_loop_dataframe <pandas dataframe> dataframe of all site outputs from hopp runs
    """
    
    # Wait to de-synchronize api requests
    wait = 10+rng.integers(10)
    time.sleep(wait)

    # Set up hopp_outputs dictionary
    hopp_outputs = dict()

    # Site details
    Site = sample_site  # sample_site has been loaded from flatirons_site to provide sample site boundary information
    Site['lat'] = site_lat
    Site['lon'] = site_lon
    Site['site_num'] = site_num
    Site['resource_filename_solar'] = resource_filename_solar
    Site['resource_filename_wind'] = resource_filename_wind
    Site['year'] = year

    # Get the Timezone offset value based on the lat/lon of the site
    try:
        location = {'lat': Site['lat'], 'long': Site['lon']}
        tz_val = get_offset(**location)
        Site['tz'] = (tz_val - 1)
    except:
        print('Timezone lookup failed for {}'.format(location))

    scenario_description = 'greenfield'

    # # Case 1 - Wind
    # solar_size_mw = 0
    # wind_size_mw = wind_size
    # total_hybrid_plant_capacity_mw = solar_size + wind_size
    # nameplate_mw = total_hybrid_plant_capacity_mw
    # interconnection_size_mw = interconnection_size
    # hopp_outputs['Wind'], resource_filename_wind, resource_filename_solar = \
    #     run_hopp_calc(Site, scenario_description, bos_details, total_hybrid_plant_capacity_mw, solar_size_mw, wind_size_mw,
    #                 nameplate_mw, interconnection_size_mw, load_resource_from_file,
    #                 ppa_price, results_dir)

    # # Case 2 - Solar
    # solar_size_mw = solar_size
    # wind_size_mw = 0
    # total_hybrid_plant_capacity_mw = solar_size + wind_size
    # nameplate_mw = total_hybrid_plant_capacity_mw
    # interconnection_size_mw = interconnection_size
    # hopp_outputs['Solar'], resource_filename_wind, resource_filename_solar\
    #     = run_hopp_calc(Site, scenario_description, bos_details, total_hybrid_plant_capacity_mw, solar_size_mw, wind_size_mw,
    #                 nameplate_mw, interconnection_size_mw, load_resource_from_file,
    #                 ppa_price, results_dir)

    # Case 3 - Hybrid Wind + Solar
    solar_size_mw = solar_size
    wind_size_mw = wind_size
    total_hybrid_plant_capacity_mw = solar_size + wind_size
    nameplate_mw = total_hybrid_plant_capacity_mw
    interconnection_size_mw = interconnection_size
    hopp_outputs['Hybrid'], resource_filename_wind, resource_filename_solar \
        = run_hopp_calc(Site, scenario_description, bos_details, total_hybrid_plant_capacity_mw, solar_size_mw, wind_size_mw,
                    nameplate_mw, interconnection_size_mw, load_resource_from_file,
                    ppa_price, results_dir)

    # max_aep_index, max_aep_value = max(enumerate([hopp_outputs['Wind']['AEP (GWh)'][0],
    #                                               hopp_outputs['Solar']['AEP (GWh)'][0],
    #                                               hopp_outputs['Hybrid']['AEP (GWh)'][0]]),
    #                                    key=operator.itemgetter(1))
    # max_npv_index, max_npv_value = max(enumerate([hopp_outputs['Wind']['NPV ($-million)'][0],
    #                                               hopp_outputs['Solar']['NPV ($-million)'][0],
    #                                               hopp_outputs['Hybrid']['NPV ($-million)'][0]]),
    #                                    key=operator.itemgetter(1))

    # # Determine the differential between standalone wind + standalone solar vs. wind + adding solar
    # hopp_outputs['Hybrid vs. Separate'] = establish_save_output_dict()
    # hopp_outputs['Hybrid vs. Separate']['Scenario Description'].append(
    #     '(Combined Wind & Solar) - (Standalone Wind + Standalone Solar)')
    # hopp_outputs['Hybrid vs. Separate']['Solar (%)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Solar (MW)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Wind (MW)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['AEP (GWh)'].append((hopp_outputs['Hybrid']['AEP (GWh)'][0])
    #                                                        - (hopp_outputs['Wind']['AEP (GWh)'][0]
    #                                                           + hopp_outputs['Solar']['AEP (GWh)'][0]))
    # hopp_outputs['Hybrid vs. Separate']['Solar AEP (GWh)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Wind AEP (GWh)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Solar Capacity Factor'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Capacity Factor'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Wind Capacity Factor'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Capacity Factor of Interconnect'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Percentage Curtailment'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['NPV ($-million)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['LCOE - Nominal'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['LCOE - Real'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['IRR (%)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['PPA Price Used'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['TOD Profile Used'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Revenue (PPA)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Revenue (TOD)'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['Pearson R Wind V Solar'].append(float('nan'))
    # hopp_outputs['Hybrid vs. Separate']['BOS Cost'].append((hopp_outputs['Hybrid']['BOS Cost'][0])
    #                                                       - (hopp_outputs['Wind']['BOS Cost'][0]
    #                                                          + hopp_outputs['Solar']['BOS Cost'][0]))
    # hopp_outputs['Hybrid vs. Separate']['BOS Cost percent reduction'].append(100 * ((
    #                                                                                    hopp_outputs[
    #                                                                                        'Hybrid vs. Separate'][
    #                                                                                        'BOS Cost'][0]) /
    #                                                                                ((hopp_outputs['Wind']['BOS Cost'][0]
    #                                                                                  + hopp_outputs['Solar']['BOS Cost'][
    #                                                                                      0]))))
    # hopp_outputs['Hybrid vs. Separate']['Cost / MWh Produced'].append((hopp_outputs['Hybrid']
    # ['Cost / MWh Produced'][0])
    #                                                                  - (hopp_outputs['Wind']['Cost / MWh Produced'][0]
    #                                                                     + hopp_outputs['Solar']['Cost / MWh Produced'][
    #                                                                         0]) / 2)
    # hopp_outputs['Hybrid vs. Separate']['Cost / MWh Produced percent reduction']. \
    #     append(100 * ((hopp_outputs['Hybrid vs. Separate']
    # ['Cost / MWh Produced'][0])
    #                   / ((hopp_outputs['Wind']['Cost / MWh Produced'][0]
    #                       + hopp_outputs['Solar']
    #                       ['Cost / MWh Produced'][0]))))
    # cost_per_mw_reduction_hybrid_vs_standalone = ((hopp_outputs['Hybrid']['Cost / MWh Produced'][0])
    #                                               - (hopp_outputs['Wind']['Cost / MWh Produced'][0]
    #                                                  + hopp_outputs['Solar']['Cost / MWh Produced'][0]) / 2)
    # cost_per_mw_reduction_hybrid_vs_standalone_percent = (100 * ((hopp_outputs['Hybrid vs. Separate']
    # ['Cost / MWh Produced'][0])
    #                                                              / ((hopp_outputs['Wind']
    #                                                                  ['Cost / MWh Produced'][0]
    #                                                                  + hopp_outputs['Solar']
    #                                                                  ['Cost / MWh Produced'][0]))))
    # lcoe_real_reduction_hybrid_percentage_vs_wind = 100 * abs((hopp_outputs['Hybrid']['LCOE - Real'][0]
    #                                                            - hopp_outputs['Wind']['LCOE - Real'][0])
    #                                                           / hopp_outputs['Wind']['LCOE - Real'][0])
    # lcoe_real_reduction_hybrid_percentage = 100 * abs((hopp_outputs['Hybrid']['LCOE - Real'][0]
    #                                                    - min(hopp_outputs['Wind']['LCOE - Real'][0]
    #                                                          , hopp_outputs['Solar']['LCOE - Real'][0]))
    #                                                   / min(hopp_outputs['Wind']['LCOE - Real'][0]
    #                                                         , hopp_outputs['Solar']['LCOE - Real'][0]))
    # # Determine Percentage Change in COE/reduction in bos for solar to compete with wind
    # percent_change_solar_coe_to_compete_with_wind = max(0, 100 * ((hopp_outputs['Solar']['Cost / MWh Produced'][0]
    #                                                                - hopp_outputs['Wind']['Cost / MWh Produced'][0])
    #                                                               / hopp_outputs['Solar']['Cost / MWh Produced'][0]))
    # change_in_npv_hybrid_vs_wind = hopp_outputs['Hybrid']['NPV ($-million)'][0] - \
    #                                hopp_outputs['Wind']['NPV ($-million)'][0]

    # Save all relevant outputs for each site
    hopp_outputs_all = establish_save_outputs_resource_loop_dict()
    hopp_outputs_all['Site Lat'].append(Site['lat'])
    hopp_outputs_all['Site Lon'].append(Site['lon'])
    hopp_outputs_all['PPA Price'].append(ppa_price)
    hopp_outputs_all['Wind Size(MW)'].append(wind_size)
    hopp_outputs_all['Solar Size(MW)'].append(solar_size)
    hopp_outputs_all['Hybrid Size(MW)'].append(hybrid_size)
    # hopp_outputs_all['Wind AEP (GWh)'].append(hopp_outputs['Wind']['AEP (GWh)'][0])
    # hopp_outputs_all['Solar AEP (GWh)'].append(hopp_outputs['Solar']['AEP (GWh)'][0])
    hopp_outputs_all['Hybrid AEP (GWh)'].append(hopp_outputs['Hybrid']['AEP (GWh)'][0])
    # hopp_outputs_all['Wind NPV ($-million)'].append(hopp_outputs['Wind']['NPV ($-million)'][0])
    # hopp_outputs_all['Solar NPV ($-million)'].append(hopp_outputs['Solar']['NPV ($-million)'][0])
    hopp_outputs_all['Hybrid NPV ($-million)'].append(hopp_outputs['Hybrid']['NPV ($-million)'][0])
    # hopp_outputs_all['Wind LCOE (real)'].append(hopp_outputs['Wind']['LCOE - Real'][0])
    # hopp_outputs_all['Solar LCOE (real)'].append(hopp_outputs['Solar']['LCOE - Real'][0])
    hopp_outputs_all['Hybrid LCOE (real)'].append(hopp_outputs['Hybrid']['LCOE - Real'][0])
    # hopp_outputs_all['LCOE(real) reduction (%)'].append(lcoe_real_reduction_hybrid_percentage)
    # hopp_outputs_all['LCOE(real) reduction (%) vs wind'].append(lcoe_real_reduction_hybrid_percentage_vs_wind)
    # hopp_outputs_all['Wind Cost / MWh Produced'].append(hopp_outputs['Wind']['Cost / MWh Produced'][0])
    # hopp_outputs_all['Solar Cost / MWh Produced'].append(hopp_outputs['Solar']['Cost / MWh Produced'][0])
    hopp_outputs_all['Hybrid Cost / MWh Produced'].append(hopp_outputs['Hybrid']['Cost / MWh Produced'][0])
    # hopp_outputs_all['Wind BOS Cost'].append(hopp_outputs['Wind']['BOS Cost'][0])
    # hopp_outputs_all['Solar BOS Cost'].append(hopp_outputs['Solar']['BOS Cost'][0])
    hopp_outputs_all['Hybrid BOS Cost'].append(hopp_outputs['Hybrid']['BOS Cost'][0])
    # hopp_outputs_all['Cost / MWh Produced reduction (%)'].append(
    #     cost_per_mw_reduction_hybrid_vs_standalone_percent)
    # hopp_outputs_all['NPV Benefit ($-million) Hybrid Vs. Wind'].append(change_in_npv_hybrid_vs_wind)
    # hopp_outputs_all['Solar Beats Wind AEP'].append(
    #     1 * (hopp_outputs['Solar']['AEP (GWh)'][0] > hopp_outputs['Wind']['AEP (GWh)'][0]))
    # hopp_outputs_all['Solar Beats Wind NPV'].append(
    #     1 * (hopp_outputs['Solar']['NPV ($-million)'][0] > hopp_outputs['Wind']['NPV ($-million)'][0]))
    # hopp_outputs_all['Solar Beats Wind Cost/MWh'].append(1 * (hopp_outputs['Solar']['Cost / MWh Produced'][0]
    #                                                                     < hopp_outputs['Wind']['Cost / MWh Produced'][
    #                                                                         0]))
    # hopp_outputs_all['Max AEP Index'].append(max_aep_index)
    # hopp_outputs_all['Max AEP Value'].append(max_aep_value)
    # hopp_outputs_all['Max NPV Index'].append(max_npv_index)
    # hopp_outputs_all['Max NPV Value'].append(max_npv_value)
    # hopp_outputs_all['Wind Capacity Factor'].append(hopp_outputs['Wind']['Wind Capacity Factor'][0])
    # hopp_outputs_all['Solar Capacity Factor'].append(hopp_outputs['Solar']['PV Capacity Factor'][
    #                                                                0])  # save_outputs_resource_loop['NPV @ 100% Solar'].append(npv_at_100_solar)
    # hopp_outputs_all['Interconnect Capacity Factor (Wind Case)'].append(
    #     hopp_outputs['Wind']['Capacity Factor of Interconnect'][0])
    # hopp_outputs_all['Interconnect Capacity Factor (Solar Case)'].append(
    #     hopp_outputs['Solar']['Capacity Factor of Interconnect'][0])
    hopp_outputs_all['Interconnect Capacity Factor (Hybrid Case)'].append(
        hopp_outputs['Hybrid']['Capacity Factor of Interconnect'][0])
    # hopp_outputs_all['Percentage Curtailment (Wind)'].append(hopp_outputs['Wind']['Percentage Curtailment'][0])
    # hopp_outputs_all['Percentage Curtailment (Solar)'].append(
    #     hopp_outputs['Solar']['Percentage Curtailment'][0])
    hopp_outputs_all['Percentage Curtailment (Hybrid)'].append(
        hopp_outputs['Hybrid']['Percentage Curtailment'][0])
    # hopp_outputs_all['Pearson R Wind V Solar'].append(hopp_outputs['Hybrid']['Pearson R Wind V Solar'][0])
    hopp_outputs_all['Solar File Used'].append(resource_filename_solar)
    hopp_outputs_all['Wind File Used'].append(resource_filename_wind)
    hopp_outputs_all['Time Zone (for solar)'].append(Site['tz'])
    #hopp_outputs_all_dataframe = pd.DataFrame(hopp_outputs_all)

    lat = hopp_outputs_all['Site Lat'][0]
    lon = hopp_outputs_all['Site Lon'][0]
    LCOE = hopp_outputs_all['Hybrid LCOE (real)'][0]
    NPV = hopp_outputs_all['Hybrid NPV ($-million)'][0]

    print('Finished site number {}'.format(site_num))

    results_filename = all_run_dir+'_LCOE\{}_{}.txt'.format(lat,lon)
    np.savetxt(results_filename,[LCOE])
    results_filename = all_run_dir+'_NPV\{}_{}.txt'.format(lat,lon)
    np.savetxt(results_filename,[NPV])

    # return [lat, lon, LCOE]#_dataframe


def run_all_hybrid_calcs(site_details, scenario_descriptions, results_dir, load_resource_from_file, wind_size,
                         solar_size, hybrid_size, interconnection_size, bos_details, ppa_price, solar_tracking_mode, hub_height,
                         correct_wind_speed_for_height, all_run_dir):
    """
    Performs a multi-threaded run of run_hybrid_calc for the given input parameters.
    Returns a dataframe result for all sites
    :param site_details: DataFrame containing site details for all sites to be analyzed,
    including site_nums, lat, long, wind resource filename and solar resource filename.
    :param scenario_description: Project scenario - e.g. 'Wind Only', 'Solar Only', 'Hybrid - Wind & Solar'.
    :param results_dir: path to results directory
    :param load_resource_from_file: (boolean) flag which determines whether
    :param wind_size: capacity in MW of wind plant.
    :param solar_size: capacity in MW of solar plant.
    :param hybrid_size: capacity in MW of hybrid plant.
    :param bos_details: contains bos details including type of analysis to conduct (cost/mw, json lookup, HybridBOSSE).
    :param ppa_price: ppa price in $(USD)
    :param solar_tracking_mode: solar tracking mode
    :param hub_height: hub height in meters.
    :param correct_wind_speed_for_height: (boolean) flag determining whether wind speed is extrapolated to hub height.
    :param all_run_dir: path to directory for results from all runs
    :return: DataFrame of results for run_hybrid_calc at all sites (save_all_runs)
    """
    # Establish output DataFrame
    #save_all_runs = pd.DataFrame()
    lats = []
    lons = []
    LCOEs = []

    # Combine all arguments to pass to run_hybrid_calc
    all_args = zip(site_details['year'], site_details['site_nums'], repeat(scenario_descriptions), repeat(results_dir),
                   repeat(load_resource_from_file),
                   site_details['wind_filenames'], site_details['solar_filenames'],
                   site_details['lat'], site_details['lon'],
                   repeat(wind_size), repeat(solar_size), repeat(hybrid_size), repeat(interconnection_size),
                   repeat(bos_details), repeat(ppa_price),
                   repeat(solar_tracking_mode), repeat(hub_height),
                   repeat(correct_wind_speed_for_height), repeat(all_run_dir))

    # Run a multi-threaded analysis
    with multiprocessing.Pool(8) as p:
        p.starmap(run_hybrid_calc, all_args)

    # # Run a single-threaded analysis
    # for all_arg in all_args:
    #     run_hybrid_calc(*all_arg)

if __name__ == '__main__':

    # Set paths
    parent_path = os.path.abspath(os.path.dirname(__file__))
    main_path = os.path.abspath(os.path.join(parent_path, 'analysis'))
    print("Parent path: ", parent_path)
    print("Main path", main_path)
    results_dir = os.path.join(parent_path, 'results')
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)

    # Establish Project Scenarios and Parameter Ranges:
    bos_details = dict()
    bos_details['BOSSource'] = 'BOSLookup'  # Cost/MW, BOSLookup, HybridBOSSE, HybridBOSSE_manual
    bos_details['BOSFile'] = 'UPDATED_BOS_Summary_Results.json'
    bos_details['BOSScenario'] = 'TBD in analysis'  # Will be set to Wind Only, Solar Only,
    # Variable Ratio Wind and Solar Greenfield, or Solar Addition
    bos_details['BOSScenarioDescription'] = ''  # Blank or 'Overbuild'
    bos_details['Modify Costs'] = True
    bos_details['wind_capex_reduction'] = 0
    bos_details['solar_capex_reduction'] = 0
    bos_details['wind_bos_reduction'] = 0
    bos_details['solar_bos_reduction'] = 0
    bos_details['wind_capex_reduction_hybrid'] = 0
    bos_details['solar_capex_reduction_hybrid'] = 0
    bos_details['wind_bos_reduction_hybrid'] = 0
    bos_details['solar_bos_reduction_hybrid'] = 0

    load_resource_from_file = True
    solar_from_file = True
    wind_from_file = True
    on_land_only = False
    in_usa_only = False  # Only use one of (in_usa / on_land) flags

    # Set Analysis Location and Details
    year = 2013
    lat_int = 30 # lattitute interval in degrees
    lon_int = 20 # longitude interval in degrees
    NE_vertex = np.array([43.3,-77.3]) # NE of Buffalo
    SE_vertex = np.array([40.3,-79.7]) # SE of Pittsburgh
    SW_vertex = np.array([24.6,-98.3]) # SW of Brownsville
    NW_vertex = np.array([48.0,-101.9]) # NW of Bismarck
    num_lon = round((NE_vertex[1]+SE_vertex[1]-NW_vertex[1]-SW_vertex[1])/2/lon_int)+1
    coords = np.array([[],[]]).transpose()
    for i in range(num_lon):
        N_vertex = NE_vertex+(NW_vertex-NE_vertex)*i/(num_lon-1)
        S_vertex = SE_vertex+(SW_vertex-SE_vertex)*i/(num_lon-1)
        num_lat = round((N_vertex[0]-S_vertex[0])/lat_int)+1
        for j in range(num_lat):
            coords = np.vstack([coords,N_vertex+(S_vertex-N_vertex)*j/(num_lat-1)])
    num_loc = np.shape(coords)[0]
    desired_lats = list(coords[:,0])
    desired_lons = list(coords[:,1])

    # Load locations from list - cancels out previous block
    lon_lat_name_list = ['ngcc_just2.csv',]
# 'ngcc1.csv',
#                         'ngcc2.csv',
#                         'ngcc3.csv',
#                         'ngcc4.csv',
#                         'ngcc5.csv',
#                         'ngcc6.csv',
#                         'ngcc7.csv',
#                         'ngcc8.csv',
#                         'ngcc9.csv',
    # lon_lat_name_list = ['ngcc10.csv',
    #                     'ngcc11.csv',
    #                     'ngcc12.csv',
    #                     'ngcc13.csv',
    #                     'ngcc14.csv',
    #                     'ngcc15.csv',
    #                     'ngcc16.csv',
    #                     'ngcc17.csv',
    #                     'ngcc18.csv',
    #                     'ngcc19.csv']
    for lon_lat_name in lon_lat_name_list:
        lon_lats = pd.read_csv(lon_lat_name,header=None)
        desired_lats = list(lon_lats.values[:,1])
        desired_lons = list(lon_lats.values[:,0])

        # Load wind and solar resource files for location nearest desired lats and lons
        # NB this resource information will be overriden by API retrieved data if load_resource_from_file is set to False
        sitelist_name = 'filtered_site_details_{}_locs_{}_year'.format(num_loc, year)
        # sitelist_name = 'site_details.csv'
        if load_resource_from_file:
            # Loads resource files in 'resource_files', finds nearest files to 'desired_lats' and 'desired_lons'
            site_details = resource_loader_file(resource_dir, desired_lats, desired_lons, year, not_rect=True,\
                                                max_dist=.1)  # Return contains
            # site_details = filter_sites(site_details, location='usa only')
            site_details.to_csv(os.path.join(resource_dir, 'site_details.csv'))
        else:
            # Creates the site_details file containing grid of lats, lons, years, and wind and solar filenames (blank
            # - to force API resource download)
            if os.path.exists(sitelist_name):
                site_details = pd.read_csv(sitelist_name)
            else:
                site_details = site_details_creator.site_details_creator(desired_lats, desired_lons, year, not_rect=True)
                # Filter to locations in USA - MOVE TO PARALLEL
                site_details = filter_sites(site_details, location='usa only')
                site_details.to_csv(sitelist_name)

        solar_tracking_mode = 'Fixed'  # Currently not making a difference
        ppa_prices = [0.00]  # [0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
        hub_height_options = [200]  # [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200]
        correct_wind_speed_for_height = True
        interconnection_sizes = [400]
        wind_sizes = [600,500,400,300,200,100,0]
        solar_sizes = [0,100,200,300,400,500,600]
        hybrid_sizes = [wind_sizes[i] + solar_sizes[i] for i in range(len(wind_sizes))]

        for ppa_price in ppa_prices:
            for hub_height in hub_height_options:
                for interconnection_size in interconnection_sizes:
                    for i, wind_size in enumerate(wind_sizes):
                        solar_size = solar_sizes[i]
                        hybrid_size = hybrid_sizes[i]

                        # Save results from all locations to folder
                        all_run_folder = 'All_Runs_WindSize_{}_MW_SolarSize_{}_MW'\
                            .format(wind_size, solar_size)
                        all_run_dir = os.path.join(parent_path, all_run_folder)
                        if not os.path.exists(all_run_dir):
                            os.mkdir(all_run_dir)

                        # Run hybrid calculation for all sites
                        # save_all_runs = 
                        run_all_hybrid_calcs(site_details, "greenfield", results_dir,
                                                            load_resource_from_file, wind_size,
                                                            solar_size, hybrid_size, interconnection_size, bos_details,
                                                            ppa_price, solar_tracking_mode, hub_height,
                                                            correct_wind_speed_for_height, all_run_dir)
                    
                        # print(save_all_runs)
