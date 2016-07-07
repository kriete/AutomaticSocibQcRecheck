from urllib2 import Request, urlopen, URLError
from lxml import html
from netCDF4 import Dataset
import ConfigParser
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
handler = logging.FileHandler('utils.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s p%(process)s {%(pathname)s:%(lineno)d} - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def find_all_instances(s, ch):
    return [i for i, ltr in enumerate(s) if ltr == ch]


def get_mooring_stations(base_url, year, month):
    # Please note this was originally meant to be used for _latest datasets only. I adapted this to specify month and
    # year.
    # TODO: refine to have a month selection here.
    # TODO: replace self -- haha very sacrificing
    # TODO: use logger instead of print s**t
    name_list = []
    URLBuilder = []
    req = Request(base_url)
    try:
        response = urlopen(req)
    except URLError as e:
        if hasattr(e, 'reason'):
            print 'We failed to reach a server.'
            print 'Reason: ', e.reason
        elif hasattr(e, 'code'):
            print 'The server couldn\'t fulfill the request.'
            print 'Error code: ', e.code
    else:
        url_builder = []
        tree = html.fromstring(response.read())
        link_path = tree.xpath('//a')
        for x in range(1, len(link_path)):
            url_builder.append(link_path[x].values())
        URLLister = []
        for n in range(0, len(url_builder) - 4):
            string = str(url_builder[n])
            idx = string.find("/")
            # url = "http://thredds.socib.es/thredds/catalog/mooring/weather_station/" + URLBuilder[n][0][0:idx-1] + "/L1/catalog.html"
            url = "http://thredds.socib.es/thredds/catalog/mooring/weather_station/" + url_builder[n][0][
                                                                                       0:idx - 1] + "L1/catalog.html"
            name = url_builder[n][0][0:idx - 2]
            req = Request(url)
            try:
                response = urlopen(req)
            except URLError as e:
                if hasattr(e, 'reason'):
                    print 'We failed to reach a server.'
                    print 'Reason: ', e.reason
                elif hasattr(e, 'code'):
                    print 'The server couldn\'t fulfill the request.'
                    print 'Error code: ', e.code
            else:
                URLLister.append(url)
                name_list.append(name)

        for m in URLLister:
            req = Request(m)
            try:
                response = urlopen(req)
            except URLError as e:
                if hasattr(e, 'reason'):
                    print 'We failed to reach a server.'
                    print 'Reason: ', e.reason
                elif hasattr(e, 'code'):
                    print 'The server couldn\'t fulfill the request.'
                    print 'Error code: ', e.code
            else:
                tree = html.fromstring(response.read())
                link_path = tree.xpath('//a')
                for x in range(1, len(link_path)):
                    string = str(link_path[x].values())
                    idx = string.find("=")

                    out_string = "http://thredds.socib.es/thredds/dodsC/" + str(link_path[x].values()[0][idx - 1:len(string)])
                    idx = out_string.find("L1/")
                    out_string = out_string[0:idx] + 'L1/' + str(year) + '' + out_string[idx+2::]
                    idx = out_string.find("_latest")
                    out_string = out_string[0:idx] + '_' + str(year) + '-' + str(month).zfill(2) + '.nc'
                    URLBuilder.append(out_string)
                    break
    return URLBuilder


def read_key_value_config(section, variable):
    config_handler = ConfigParser.ConfigParser()
    config_handler.read('/home/akrietemeyer/workspace/qc_comparison/config.ini')
    out = dict()
    if config_handler.has_section(section):
        full = config_handler.get(section, variable)
        idx = find_all_instances(full, ';')
        start_counter = 0
        for i in idx:
            pair = full[start_counter:i]
            comma_idx = find_all_instances(pair, ',')
            key = pair[0:comma_idx[0]]
            value = pair[comma_idx[0]+1::]
            out[key] = value.strip()
            start_counter = i + 1
    else:
        logger.warning('Specified section ' + section + ' not found in config.ini.')
    return out


def check_link_availability(link):
    assert isinstance(link, str)
    try:
        Dataset(link)
    except RuntimeError:
        logger.debug('We failed to reach a server.')
        return False
    else:
        return True


def get_station_name_from_link(prior_string, posterior_string, cur_link):
        assert cur_link, str
        start_str = prior_string
        idx_start = cur_link.find(start_str)
        idx_end = cur_link.find(posterior_string)
        return cur_link[idx_start+len(start_str):idx_end]