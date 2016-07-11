from utils import *
from netCDF4 import Dataset
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('[%(asctime)s] p%(process)s %(lineno)d - %(name)s - %(levelname)s - %(message)s', '%m-%d %H:%M:%S')
handler.setFormatter(formatter)
handler = logging.FileHandler('station.log')
handler.setLevel(logging.INFO)
logger.addHandler(handler)


class StationManager:
    def __init__(self, qc_definitions, year=None, month=None, station_names=None):
        if (year is None) or (month is None):
            year, month = read_year_month_config()
        if station_names is None:
            single_stations = read_single_stations_config()
        self.station_links = get_mooring_stations('http://thredds.socib.es/thredds/catalog/mooring/weather_station/catalog.html', year, month, only_single_stations=single_stations)
        self.year = year
        self.month = month
        self.qc_definitions = qc_definitions
        self.station_container = []
        self.create_stations()
        self.assign_qc_processes()
        self.process_stations()
        self.print_station_information()

    def print_station_information(self):
        for station in self.station_container:
            station.log_station_information()

    def create_stations(self):
        for link in self.station_links:
            if check_link_availability(link):
                name = get_station_name_from_link('weather_station/', '/L1/', link)
                logger.info('Found data for station ' + name)
                self.station_container.append(Station(link, name, self.year, self.month))
            else:
                logger.warning(link + ' does not exist. Will not use this station.')

    def assign_qc_processes(self):
        # TODO: also get dat stuff from database goddamn it
        # TODO: outsource dat here, should not be necessarily be here.... !
        # Btw, the philosophy of these definitions also suck (ye ye ye ye I am completely aware that they are hardcoded
        # and I should have really avoided that)
        axys_watchMate_meteo = ['buoy_canaldeibiza-scb_met010', 'buoy_bahiadepalma-scb_met008']
        meteoStation_aanderaa = ['station_salines-ime_met002']
        meteoStation_vaisala = ['mobims_calamillor-scb_met001']
        meteoStation_vaisala_airp_mbar = ['mobims_playadepalma-scb_met012', 'station_parcbit-scb_met004',
                                          'station_galfi-scb_met005', 'station_esporles-scb_met003',
                                          'mobims_sonbou-scb_met011']
        for station in self.station_container:
            cur_name = station.name
            if cur_name in axys_watchMate_meteo:
                cur_process_name = 'Axys_WatchMate_Meteo'
                station.process_name = cur_process_name
                station.process_definitions = self.qc_definitions.processes[cur_process_name]
            elif cur_name in meteoStation_aanderaa:
                cur_process_name = 'MeteoStation_Aanderaa'
                station.process_name = cur_process_name
                station.process_definitions = self.qc_definitions.processes[cur_process_name]
            elif cur_name in meteoStation_vaisala:
                cur_process_name = 'MeteoStation_Vaisala'
                station.process_name = cur_process_name
                station.process_definitions = self.qc_definitions.processes[cur_process_name]
            elif cur_name in meteoStation_vaisala_airp_mbar:
                cur_process_name = 'MeteoStation_Vaisala_Airp_Mbar'
                station.process_name = cur_process_name
                station.process_definitions = self.qc_definitions.processes[cur_process_name]
            else:
                logger.warning('No Process defined for this station: ' + cur_name + '. Will use default now.')
                cur_process_name = 'MeteoStation_Vaisala_Airp_Mbar'
                station.process_name = cur_process_name
                station.process_definitions = self.qc_definitions.processes[cur_process_name]
            station.get_defined_variables_of_interest()

    def process_stations(self):
        for station in self.station_container:
            logger.info('Processing station ' + station.name + '...')
            station.perform_qc()
            logger.info('Plotting and saving station ' + station.name + '...')
            station.run_through_variables_of_interest()
            logger.info('Processing station ' + station.name + ' finished.')


class Station:
    def __init__(self, link, name, year, month):
        # TODO: fix converted_time1 plz
        self.year = year
        self.month = month
        self.link = link
        self.name = name
        self.root = Dataset(link)
        self.time = get_data_array(self.root['time'])
        self.converted_time = get_md_datenum(self.time)
        date_converted = [datetime.fromtimestamp(ts) for ts in self.time]
        self.converted_time1 = get_pandas_timestamp_series(date_converted)
        translate_time = self.converted_time1.apply(lambda x: x.to_pydatetime())
        self.converted_time_backward = map(totimestamp, translate_time)
        self.process_name = ''
        self.process_definitions = None
        self.variables_of_interest = []
        self.qc_variables_of_interest = []
        self.definitions_of_interest = dict()
        self.qc_output = dict()

    def get_defined_variables_of_interest(self):
        for method_name, method_definition in self.process_definitions.method_container.items():
            var_name = method_definition.title
            if not self.check_variable_existence(var_name):
                continue
            self.variables_of_interest.append(var_name)
            self.definitions_of_interest[method_definition.title] = method_definition
            qc_variable_name = self.root[var_name].ancillary_variables
            self.qc_variables_of_interest.append(qc_variable_name)

    def log_station_information(self):
        logger.info('---')
        logger.info('Station ' + self.name)
        logger.info('Provided by source link ' + self.link)
        logger.info('Has been assigned to the process ' + self.process_name)
        logger.info('Has processes defined for the variables ' + str(self.process_definitions.method_container.keys()))
        logger.info('The definitions were connected with the variables ' + str(self.variables_of_interest))

    def check_variable_existence(self, variable_name):
        try:
            self.root[variable_name]
        except IndexError:
            logger.warning('Variable of interest ' + variable_name + ' not found. Will pop it out.')
            return False
        return True

    def run_through_variables_of_interest(self):
        variable_counter = 0
        tab_holder = []
        for variable_name in self.variables_of_interest:
            variable = self.root[variable_name]
            qc_variable = self.root[self.qc_variables_of_interest[variable_counter]]
            variable_data = get_data_array(variable)
            qc_variable_data = get_data_array(qc_variable)
            # new_qc_variable_data = np.asarray(np.ones((1, len(qc_variable_data)))[0])
            new_qc_variable_data = self.qc_output[variable_name]
            difference_highlights_idx = np.where(qc_variable_data != new_qc_variable_data)[0]

            tab_holder.append(get_bokeh_tab(self.converted_time1, variable_data, variable,
                                            self.converted_time_backward, qc_data=qc_variable_data,
                                            new_qc_data=new_qc_variable_data, diff_idx=difference_highlights_idx))
            variable_counter += 1
        plot_bokeh(tab_holder, self.name, self.year, self.month)

    def perform_qc(self):
        for variable_name in self.variables_of_interest:
            variable = self.root[variable_name]
            variable_data = get_data_array(variable)
            self.qc_output[variable_name] = np.ones((1, len(variable_data)))[0]
            nan_idx = np.isnan(variable_data)
            self.qc_output[variable_name][nan_idx] = 9
            method_definitions = self.definitions_of_interest[variable_name].get_method_arrays()
            cur_qc_methods = method_definitions[0]
            cur_qc_input_parameters = method_definitions[1]
            cur_qc_lookup = method_definitions[2]
            if len(cur_qc_methods) != len(cur_qc_lookup):
                logger.error("Incorrect amount of flags with respect to the QC methods set.")
                return
            qc_counter = 0
            for qc_method in cur_qc_methods:
                input_parameters = cur_qc_input_parameters[qc_counter]
                if qc_method == 'range':
                    if len(input_parameters) != 2:
                        logger.error('Not enough input parameters.')
                        continue
                    self.qc_output[variable_name] = compute_valid_range(variable_data, input_parameters[0], input_parameters[1], cur_qc_lookup[qc_counter], self.qc_output[variable_name])
                elif qc_method == 'spike':
                    if len(input_parameters) != 1:
                        logger.error('Not enough input parameters.')
                        continue
                    self.qc_output[variable_name] = compute_spike(variable_data, input_parameters[0], cur_qc_lookup[qc_counter], self.qc_output[variable_name])
                elif qc_method == 'gradient':
                    if len(input_parameters) != 2:
                        logger.error('Not enough input parameters.')
                        continue
                    # self.qc_output[variable_name] = compute_simple_gradient(variable_data, input_parameters[1], cur_qc_lookup[qc_counter], self.qc_output[variable_name])
                    self.qc_output[variable_name] = compute_extended_gradient(variable_data, self.time, input_parameters[1], input_parameters[0], cur_qc_lookup[qc_counter], self.qc_output[variable_name])
                elif qc_method == 'stationary':
                    if len(input_parameters) != 2:
                        logger.error('Not enough input parameters.')
                        continue
                    self.qc_output[variable_name] = compute_stationary(variable_data, self.time, input_parameters[0], input_parameters[1], cur_qc_lookup[qc_counter], self.qc_output[variable_name])
                qc_counter += 1
