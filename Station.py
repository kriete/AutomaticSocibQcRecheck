from utils import *
from netCDF4 import Dataset
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = logging.FileHandler('station.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s p%(process)s {%(pathname)s:%(lineno)d} - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class StationManager:
    def __init__(self, year, month, qc_definitions):
        self.station_links = get_mooring_stations('http://thredds.socib.es/thredds/catalog/mooring/weather_station/catalog.html', year, month)
        self.qc_definitions = qc_definitions
        self.station_container = []
        self.create_stations()
        self.assign_qc_processes()
        self.print_station_information()

    def print_station_information(self):
        for station in self.station_container:
            station.log_station_information()

    def create_stations(self):
        for link in self.station_links:
            if check_link_availability(link):
                name = get_station_name_from_link('weather_station/', '/L1/', link)
                logger.info('Found data for station ' + name)
                self.station_container.append(Station(link, name))
            else:
                logger.warning(link + ' does not exist. Will not use this station.')

    def assign_qc_processes(self):
        # TODO: also get dat stuff from database goddamn it
        # TODO: outsource dat here, should not be necessarily be here.... !
        # Btw, the philosophy of these definitions also suck (ye ye ye ye I am completely aware that they are hardcoded
        # and I should have really avoided that)
        axys_watchMate_meteo = ['buoy_canaldeibiza-scb_met010', 'buoy_bahiadepalma-scb_met008']
        meteoStation_aanderaa = ['station_salines-ime_met002']
        meteoStation_vaisala = ['mobims_sonbou-scb_met011', 'mobims_calamillor-scb_met001']
        meteoStation_vaisala_airp_mbar = ['mobims_playadepalma-scb_met012', 'station_parcbit-scb_met004',
                                          'station_galfi-scb_met005', 'station_esporles-scb_met003']
        for station in self.station_container:
            cur_name = station.name
            if cur_name in axys_watchMate_meteo:
                station.process_name = 'Axys_WatchMate_Meteo'
            elif cur_name in meteoStation_aanderaa:
                station.process_name = 'MeteoStation_Aanderaa'
            elif cur_name in meteoStation_vaisala:
                station.process_name = 'MeteoStation_Vaisala'
            elif cur_name in meteoStation_vaisala_airp_mbar:
                station.process_name = 'MeteoStation_Vaisala_Airp_Mbar'
            else:
                logger.warning('No Process defined for this station: ' + cur_name + '. Will use default now.')
                station.process_name = 'MeteoStation_Vaisala_Airp_Mbar'


class Station:
    def __init__(self, link, name):
        self.link = link
        self.name = name
        self.root = Dataset(link)
        self.process_name = ''
        self.process_definitions = dict()

    def log_station_information(self):
        logger.info('---')
        logger.info('Station ' + self.name)
        logger.info('Provided by source link ' + self.link)
        logger.info('Has been assigned to the process ' + self.process_name)
