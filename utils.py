from __future__ import division
from urllib2 import Request, urlopen, URLError
from lxml import html
from netCDF4 import Dataset
import ConfigParser
import numpy as np
import matplotlib.dates as md
from datetime import datetime
import pytz
from bokeh.io import output_file, show
from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import PanTool, Range1d, LinearAxis, CustomJS, HoverTool
from bokeh.models.widgets import Panel, Tabs
import pandas as pd
from collections import OrderedDict

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
handler = logging.FileHandler('utils.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s p%(process)s {%(pathname)s:%(lineno)d} - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_min_max_ranges(data):
    cur_min = np.nanmin(data)
    cur_max = np.nanmax(data)
    difference = cur_max - cur_min
    cur_buffer = difference / 10.
    cur_min -= cur_buffer
    cur_max += cur_buffer
    return cur_min, cur_max


def get_bokeh_tab(conv_time, data, variable, conv_time_backward, qc_data=None, new_qc_data=None):
    cur_min, cur_max = get_min_max_ranges(data)
    time_strings = map(get_str, conv_time)
    data_source = ColumnDataSource(
        data=dict(
            time=time_strings,
            data=data,
            python_qc=new_qc_data,
            # applied_qc=applied_qcs,
            imported_qc=qc_data,
        )
    )
    p = figure(plot_width=1200, plot_height=300, tools=["pan, xwheel_zoom, hover, reset"], x_axis_type="datetime",
               y_range=(cur_min, cur_max), y_axis_label=variable.units)
    p.line(conv_time, data, name="data", source=data_source)
    p.square(conv_time, data)
    if qc_data is not None:
        p.extra_y_ranges = {"foo": Range1d(start=0, end=10)}

        p.line(conv_time, qc_data, color="firebrick", alpha=0.5, y_range_name="foo")
        p.line(conv_time, new_qc_data, color="green", alpha=0.5, y_range_name="foo")
        p.add_layout(LinearAxis(y_range_name="foo"), 'right')
        jscode = """
                range.set('start', parseInt(%s));
                range.set('end', parseInt(%s));
                """
        p.extra_y_ranges['foo'].callback = CustomJS(
            args=dict(range=p.extra_y_ranges['foo']),
            code=jscode % (p.extra_y_ranges['foo'].start,
                           p.extra_y_ranges['foo'].end)
        )
        hover = p.select(dict(type=HoverTool))
        hover.names = ["data"]
        hover.tooltips = OrderedDict([
            ('time', '@time'),
            ('value', '@data{0.0}'),
            ('python qc', '@python_qc'),
            # ('py-method', '@applied_qc'),
            ('imported qc', '@imported_qc'),

        ])
    automatic_range_jscode = automatic_range_jscode_defintion()
    source = ColumnDataSource({'x': conv_time_backward, 'y': data})
    p.y_range.callback = CustomJS(args=dict(source=source, yrange=p.y_range, xrange=p.x_range), code=automatic_range_jscode)
    p.x_range.callback = CustomJS(args=dict(source=source, yrange=p.y_range, xrange=p.x_range), code=automatic_range_jscode)
    pan_tool_standard = p.select(dict(type=PanTool))
    pan_tool_standard.dimensions = ["width"]
    return Panel(child=p, title=variable.name)


def automatic_range_jscode_defintion():
    jscode = """
    function isNumeric(n) {
      return !isNaN(parseFloat(n)) && isFinite(n);
    }
    var data = source.get('data');
    var start = yrange.get('start');
    var end = yrange.get('end');

    var time_start = xrange.get('start')/1000;
    var time_end = xrange.get('end')/1000;

    var pre_max_old = end;
    var pre_min_old = start;

    var time = data['x'];
    var pre = data['y'];
    t_idx_start = time.filter(function(st){return st>=time_start})[0];
    t_idx_start = time.indexOf(t_idx_start);

    t_idx_end = time.filter(function(st){return st>=time_end})[0];
    t_idx_end = time.indexOf(t_idx_end);

    var pre_interval = pre.slice(t_idx_start, t_idx_end);
    pre_interval = pre_interval.filter(function(st){return !isNaN(st)});
    var pre_max = Math.max.apply(null, pre_interval);
    var pre_min = Math.min.apply(null, pre_interval);
    var ten_percent = (pre_max-pre_min)*0.1;

    pre_max = pre_max + ten_percent;
    pre_min = pre_min - ten_percent;

    if((!isNumeric(pre_max)) || (!isNumeric(pre_min))) {
        pre_max = pre_max_old;
        pre_min = pre_min_old;
    }

    yrange.set('start', pre_min);
    yrange.set('end', pre_max);

    source.trigger('change');
    """
    return jscode


def get_str(x): return str(x)


def plot_bokeh(tab_holder, filename, year, month):
    tabs = Tabs(tabs=tab_holder)
    output_file('/home/akrietemeyer/workspace/qc_comparison/' + str(year) + '_' + str(month).zfill(2) + '_' + filename + '.html')
    show(tabs)


def totimestamp(dt, epoch=datetime(1970, 1, 1)):
    td = dt - epoch
    # return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 86400) * 10**6) / 10**6


def get_pandas_timestamp_series(datetime_array):
    out = pd.Series(np.zeros(len(datetime_array)))
    counter = 0
    for i in datetime_array:
        out[counter] = pd.tslib.Timestamp(i)
        counter += 1
    return out


def get_md_datenum(obs_time):
    dates = [datetime.fromtimestamp(ts, tz=pytz.utc) for ts in obs_time]
    return md.date2num(dates)


def get_data_array(data_array):
    if type(data_array.__array__()) is np.ma.masked_array:
        return data_array.__array__().data
    else:
        return data_array.__array__()


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