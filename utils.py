from __future__ import division
from urllib2 import Request, urlopen, URLError
from lxml import html
from netCDF4 import Dataset
import ConfigParser
import numpy as np
import matplotlib.dates as md
from datetime import datetime
import pytz
import os
from bokeh.io import output_file, show, save
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


def merge_arrays(invalid_idx, qc_flag, cur_qc_array):
    flagable_idx = np.less(cur_qc_array, qc_flag)
    flag_idx = np.logical_and(invalid_idx, flagable_idx)
    cur_qc_array[flag_idx] = qc_flag
    return cur_qc_array


def compute_valid_range(data, valid_min, valid_max, qc_flag, cur_qc_array):
    logger.info('Applying Range check...')
    invalid_less = np.less(data, valid_min)
    invalid_greater = np.greater(data, valid_max)
    invalid_idx = np.logical_or(invalid_less, invalid_greater)
    return merge_arrays(invalid_idx, qc_flag, cur_qc_array)


def compute_stationary(data, cur_time, time_check_window, threshold, qc_flag, cur_qc_array):
    logger.info('Applying Stationary check...')
    time_interval = cur_time[1] - cur_time[0]
    slicer = float(time_check_window) / time_interval*3600.
    slicer = int(slicer)
    start_idx = 0
    end_idx = slicer
    invalid_idx = np.zeros((1, len(cur_time)))[0]
    for _ in range(slicer, len(cur_time)):
        window_slice = data[start_idx:end_idx]
        amount_nan = np.where(np.isnan(window_slice))[0]
        percent_nan = float(len(amount_nan)) / len(window_slice) * 100.
        if percent_nan >= 40:
            continue
        window_slice_min = np.nanmin(window_slice)
        window_slice_max = np.nanmax(window_slice)
        window_slice_difference = window_slice_max - window_slice_min
        if window_slice_difference <= threshold:
            invalid_idx[start_idx:end_idx] = True
        start_idx += 1
        end_idx += 1
    return merge_arrays(invalid_idx, qc_flag, cur_qc_array)


def compute_simple_gradient(data, threshold, qc_flag, cur_qc_array):
    invalid_idx = np.zeros((1, len(data)))[0]
    if (abs(data[0] - data[1])) > threshold:
        invalid_idx[0] = True
    for i in range(1, len(data)-1):
        if (abs(data[i] - data[i+1] + data[i-1] - data[i])) > threshold:
            invalid_idx[i] = True
    if (abs(data[-2] - data[-1])) > threshold:
        invalid_idx[-1] = True
    return merge_arrays(invalid_idx, qc_flag, cur_qc_array)


def compute_extended_gradient(data, cur_time, threshold, time_check_window, qc_flag, cur_qc_array):
    logger.info('Applying Gradient check...')
    invalid_idx = np.zeros((1, len(data)))[0]
    time_interval = cur_time[1] - cur_time[0]
    divide = time_check_window / float(time_interval)
    if divide <= 1:
        steps = 1
    else:
        steps = int(divide) + 1
    # initial case start
    v1 = data[0]
    c1 = cur_time[0]
    v2 = np.mean(data[1:1 + steps])
    c2 = np.mean(cur_time[1:1 + steps])
    check_value = abs((v1 - v2) / ((c1 - c2) / 60.))
    if check_value >= threshold:
        invalid_idx[0] = True
    # initial case end

    nan_list = np.where(np.isnan(data))[0]
    run_through_interval = np.array(range(steps, len(cur_time) - steps, steps))

    del_index_list = []
    for n in nan_list:
        if 0 < n < len(cur_time):
            del_index_list.append(n - 1)

    del_index_list = np.unique(del_index_list)
    run_through_interval = np.delete(run_through_interval, del_index_list)

    # intermediate case
    for i in run_through_interval:
        idx_before = range(i-steps, i)
        idx_before = get_good_measurement(invalid_idx, cur_qc_array, idx_before, 'before')
        idx_after = range(i+1, i+steps+1)
        idx_after = get_good_measurement(invalid_idx, cur_qc_array, idx_after, 'after')
        if (len(idx_before) == 0) or (len(idx_after) == 0):
            continue
        c1 = np.mean(float(np.array(cur_time[idx_before])))
        c2 = float(cur_time[i])
        c3 = np.mean(float(np.array(cur_time[idx_after])))

        w1 = (c1 - c2) / (c1 - c3)
        w2 = (c2 - c3) / (c1 - c3)

        v1 = np.mean(data[idx_before])
        v2 = data[i]
        v3 = np.mean(data[idx_after])

        check_value = abs(w1 * (v2 - v3) / ((c2 - c3) / 60) + w2 * (v1 - v2) / ((c1 - c2) / 60))
        if round(check_value, 10) >= threshold:
            invalid_idx[i] = True
            logger.debug('Gradient found: V2:' + str(v2) + ' V1: ' + str(v1) + ' V3: ' + str(v3) + '. Check value: ' + str(check_value) + ' (valid threshold: ' + str(threshold) + ').')
    return merge_arrays(invalid_idx, qc_flag, cur_qc_array)


def get_good_measurement(logical_array, cur_qc_array, desired_idx, find_type):
    # TODO: run only over good measurements at the qc_logical shitstuff, but don't forget to fix indices afterwards..!
    # Might improve the efficiency
    out_idx = []
    for cur_des_idx in desired_idx:
        if (not logical_array[cur_des_idx]) and (cur_qc_array[cur_des_idx] == 1) \
                and (cur_des_idx not in out_idx):
            out_idx.append(cur_des_idx)
            # copy_of_logical_array[cur_des_idx] = True
        else:
            if find_type == 'before':
                full_qc_logical = np.logical_and(np.logical_not(logical_array[0:cur_des_idx]), (cur_qc_array[0:cur_des_idx]==1))
                reversed_qc_logical = np.fliplr([full_qc_logical])[0]
                if np.all(~reversed_qc_logical):
                    continue
                for i, value in np.ndenumerate(reversed_qc_logical):
                    new_idx = cur_des_idx-i[0]-1
                    if value and (new_idx not in out_idx):
                        out_idx.append(new_idx)
                        break
            elif find_type == 'after':
                full_qc_logical = np.logical_and(np.logical_not(logical_array[cur_des_idx::]), (cur_qc_array[cur_des_idx::]==1))
                # full_qc_array = merge_arrays(logical_array[cur_des_idx::], 9, cur_qc_array[cur_des_idx::])
                # full_qc_logical = (full_qc_array == 1)
                for i, value in np.ndenumerate(full_qc_logical):
                    new_idx = cur_des_idx+i[0]
                    if value and (new_idx not in out_idx):
                        out_idx.append(new_idx)
                        break
            else:
                logger.warning('Find type for finding good measurement not found.')
    return out_idx


def compute_spike(data, threshold, qc_flag, cur_qc_array):
    logger.info('Applying Spike check...')
    invalid_idx = np.zeros((1, len(data)))[0]

    nan_list = np.where(np.isnan(data))[0]
    run_through_interval = np.array(range(1, len(data) - 1, 1))

    del_index_list = []
    for n in nan_list:
        if 0 < n < len(data):
            del_index_list.append(n - 1)

    del_index_list = np.unique(del_index_list)
    run_through_interval = np.delete(run_through_interval, del_index_list)

    for i in run_through_interval:
        idx_before = get_good_measurement(invalid_idx, cur_qc_array, [i-1], 'before')
        idx_after = get_good_measurement(invalid_idx, cur_qc_array, [i+1], 'after')
        # check_value = abs(data[i] - (data[i+1] + data[i-1]) / 2.) - abs((data[i+1] - data[i-1]) / 2.)
        check_value = abs(data[i] - (data[idx_after] + data[idx_before]) / 2.) - abs((data[idx_after] - data[idx_before]) / 2.)
        if check_value > threshold:
            invalid_idx[i] = True
    return merge_arrays(invalid_idx, qc_flag, cur_qc_array)


def get_bokeh_tab(conv_time, data, variable, conv_time_backward, qc_data=None, new_qc_data=None, diff_idx=None):
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
    zeros = np.zeros(len(diff_idx))
    tens = zeros[:] + 10
    use_webgl = read_value_config('General', 'use_webgl')
    if use_webgl == 'True':
        # Still a bit erroneous at points with missing data
        use_webgl = True
    else:
        use_webgl = False
    # We disable the toolbar_location since a confirmed visual bug causes a bit disturbing appearance
    p = figure(plot_width=1200, plot_height=300, tools=["pan, xwheel_zoom, hover, reset"], x_axis_type="datetime",
               y_range=(cur_min, cur_max), y_axis_label=variable.units, toolbar_location=None, logo=None,
               active_scroll='xwheel_zoom', webgl=use_webgl)
    p.line(conv_time, data)
    p.square(conv_time, data, name="data", source=data_source)
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

    p.segment(conv_time[diff_idx], zeros, conv_time[diff_idx], tens, line_width=0.5, color="red", y_range_name="foo")
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
    base_dir = read_value_config('General', 'output_path')
    output_file(base_dir + str(year) + '_' + str(month).zfill(2) + '_' + filename + '.html')
    save(tabs)


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


def get_mooring_stations(base_url, year, month, only_single_stations=None):
    # Please note this was originally meant to be used for _latest datasets only. I adapted this to specify month and
    # year.
    # Added single stations bypass.
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
            if only_single_stations != [] and name not in only_single_stations:
                logger.info('Skipping station ' + name + '. (Single station bypass).')
                continue
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
    config_handler.read(os.getcwd() + '/config.ini')
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


def read_value_config(section, variable):
    config_handler = ConfigParser.ConfigParser()
    config_handler.read(os.getcwd() + '/config.ini')
    if config_handler.has_section(section):
        return config_handler.get(section, variable)
    else:
        logger.warning('Specified section ' + section + ' not found.')
        return ''


def read_year_month_config():
    year = int(read_value_config('General', 'year'))
    month = int(read_value_config('General', 'month'))
    return year, month


def read_single_stations_config():
    single_stations = []
    decision = read_value_config('General', 'use_only_single_stations')
    if decision == 'True':
        single_stations_strings = read_value_config('General', 'single_stations')
        comma_idx = find_all_instances(single_stations_strings, ',')
        start_idx = 0
        for i in comma_idx:
            single_stations.append(single_stations_strings[start_idx:i])
            start_idx = i + 1
        single_stations.append(single_stations_strings[start_idx+1::])
    return single_stations


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