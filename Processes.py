from utils import *
import copy


class ProcessManager:
    def __init__(self):
        self.processes = dict()
        self.process_name0 = 'MeteoStation_Vaisala_Airp_Mbar'
        self.process_name1 = 'MeteoStation_Vaisala'
        self.process_name2 = 'MeteoStation_Aanderaa'
        self.process_name3 = 'Axys_WatchMate_Meteo'
        self.define_processes()

    def define_processes(self):
        # TODO: read database and access dat stuff from there plz
        # Hardcoded as hell
        self.processes[self.process_name0] = Process(self.process_name0)
        self.processes[self.process_name0].add_method('AIR_PRE')
        self.processes[self.process_name0].method_container['AIR_PRE'].title = 'AIR_PRE'
        self.processes[self.process_name0].get_method('AIR_PRE').range(960, 1050, 2)
        self.processes[self.process_name0].get_method('AIR_PRE').range(920, 1080, 4)
        self.processes[self.process_name0].get_method('AIR_PRE').spike(10, 6)
        self.processes[self.process_name0].get_method('AIR_PRE').gradient(60, 0.3, 4)
        self.processes[self.process_name0].get_method('AIR_PRE').stationary(6, 0, 4)
        self.processes[self.process_name0].get_method('AIR_PRE').stationary(12, 0.6, 4)

        self.processes[self.process_name0].add_method('AIR_TEM')
        self.processes[self.process_name0].method_container['AIR_TEM'].title = 'AIR_TEM'
        self.processes[self.process_name0].get_method('AIR_TEM').range(-5, 40, 2)
        self.processes[self.process_name0].get_method('AIR_TEM').range(-30, 60, 4)
        self.processes[self.process_name0].get_method('AIR_TEM').spike(3, 6)
        self.processes[self.process_name0].get_method('AIR_TEM').gradient(60, 0.9, 4)
        self.processes[self.process_name0].get_method('AIR_TEM').stationary(6, 0, 4)
        self.processes[self.process_name0].get_method('AIR_TEM').stationary(12, 0.2, 4)

        self.processes[self.process_name0].add_method('REL_HUM')
        self.processes[self.process_name0].method_container['REL_HUM'].title = 'REL_HUM'
        self.processes[self.process_name0].get_method('REL_HUM').range(0, 100, 4)
        self.processes[self.process_name0].get_method('REL_HUM').spike(4, 6)
        self.processes[self.process_name0].get_method('REL_HUM').gradient(60, 3.6, 4)
        self.processes[self.process_name0].get_method('REL_HUM').stationary(6, 0, 4)
        self.processes[self.process_name0].get_method('REL_HUM').stationary(12, 1, 4)

        self.processes[self.process_name0].add_method('WIN_SPE')
        self.processes[self.process_name0].method_container['WIN_SPE'].title = 'WIN_SPE'
        self.processes[self.process_name0].get_method('WIN_SPE').range(0, 30, 2)
        self.processes[self.process_name0].get_method('WIN_SPE').range(0, 79, 4)
        self.processes[self.process_name0].get_method('WIN_SPE').spike(10, 6)
        self.processes[self.process_name0].get_method('WIN_SPE').gradient(60, 7.2, 4)
        self.processes[self.process_name0].get_method('WIN_SPE').stationary(6, 0, 4)
        self.processes[self.process_name0].get_method('WIN_SPE').stationary(12, 0.3, 4)

        self.processes[self.process_name1] = copy.deepcopy(self.processes[self.process_name0])
        self.processes[self.process_name1].title = self.process_name1
        self.processes[self.process_name1].method_container['AIR_PRE'].title = 'AIRP'
        self.processes[self.process_name1].method_container['AIR_TEM'].title = 'AIRT'
        self.processes[self.process_name1].method_container['REL_HUM'].title = 'RHUM'
        self.processes[self.process_name1].method_container['WIN_SPE'].title = 'WSPE_AVG'

        self.processes[self.process_name1].method_container['REL_HUM'].method_data[1] = [10]

        self.processes[self.process_name2] = copy.deepcopy(self.processes[self.process_name0])
        self.processes[self.process_name2].title = self.process_name2
        self.processes[self.process_name2].method_container['AIR_PRE'].title = 'APRE'
        self.processes[self.process_name2].method_container['AIR_TEM'].title = 'AIRT'
        self.processes[self.process_name2].method_container['REL_HUM'].title = 'RHUM'
        self.processes[self.process_name2].method_container['WIN_SPE'].title = 'WSPE'

        self.processes[self.process_name2].method_container['AIR_TEM'].method_data[3] = [300, 0.42]
        self.processes[self.process_name2].method_container['AIR_PRE'].method_data[4] = [12, 0]
        self.processes[self.process_name2].method_container['AIR_PRE'].method_data[5] = [24, 1]

        self.processes[self.process_name2].method_container['REL_HUM'].method_data[1] = [10]
        self.processes[self.process_name2].method_container['REL_HUM'].method_data[2] = [300, 2.4]
        self.processes[self.process_name2].method_container['REL_HUM'].method_data[4] = [24, 1]

        self.processes[self.process_name2].method_container['WIN_SPE'].method_data[2] = [7]
        self.processes[self.process_name2].method_container['WIN_SPE'].method_data[3] = [300, 0.54]
        self.processes[self.process_name2].method_container['WIN_SPE'].method_data[5] = [24, 0.3]

        self.processes[self.process_name3] = copy.deepcopy(self.processes[self.process_name0])
        self.processes[self.process_name3].title = self.process_name3
        self.processes[self.process_name3].method_container['AIR_TEM'].method_data[3] = [60, 0.42]
        self.processes[self.process_name3].method_container['AIR_TEM'].method_data[5] = [24, 0.2]
        self.processes[self.process_name3].method_container['AIR_PRE'].method_data[4] = [12, 0]
        self.processes[self.process_name3].method_container['AIR_PRE'].method_data[5] = [24, 0.4]
        self.processes[self.process_name3].method_container['REL_HUM'].method_data[1] = [10]
        self.processes[self.process_name3].method_container['REL_HUM'].method_data[2] = [60, 18]
        self.processes[self.process_name3].method_container['REL_HUM'].method_data[4] = [24, 1]
        self.processes[self.process_name3].method_container['WIN_SPE'].method_data[2] = [7]
        self.processes[self.process_name3].method_container['WIN_SPE'].method_data[3] = [60, 0.54]
        self.processes[self.process_name3].method_container['WIN_SPE'].method_data[5] = [24, 0.3]


class Process:
    def __init__(self, title):
        self.title = title
        self.method_container = dict()
        # CARE! HardCoded lookup table here.
        # TODO: read stuff from config
        self.method_lookup_table = read_key_value_config('Processes', 'internal_lookup_table')

    def add_method(self, name):
        self.method_container[name] = Method(name)

    def get_method(self, name):
        return self.method_container[name]


class Method:
    def __init__(self, title):
        self.title = title
        # self.method_dictionary = dict()
        self.method_names = []
        self.method_data = []
        self.flag_array = []

    def get_method_arrays(self):
        return self.method_names, self.method_data, self.flag_array

    def fill_dict(self, name, data, flag):
        self.method_names.append(name)
        self.method_data.append(data)
        self.flag_array.append(flag)

    def range(self, range_min, range_max, flag):
        name = 'range'
        data = [range_min, range_max]
        self.fill_dict(name, data, flag)

    def spike(self, threshold, flag):
        name = 'spike'
        data = [threshold]
        self.fill_dict(name, data, flag)

    def gradient(self, interval, threshold, flag):
        name = 'gradient'
        data = [interval, threshold]
        self.fill_dict(name, data, flag)

    def stationary(self, interval, threshold, flag):
        name = 'stationary'
        data = [interval, threshold]
        self.fill_dict(name, data, flag)
