# AutomaticSocibQcRecheck
Create bokeh representations of the specified month (incl. QC and re-computed QC) from socib weather stations. Will highlight differences in red.

Needs still to be refined to use database access and picking good data only for some checks.

However, this is meant to be a prototype to show the usage of bokeh and to highlight potential problems with the socib  netCDF data sources.

Clone the repo or just download the the interactive HTML to see an example output.

Check also my other github repositories <a href="https://github.com/kriete/ScatterBokeh">ScatterBokeh</a>, <a href="https://github.com/kriete/bokehAutomaticYRangeUpdate">bokehAutomaticYRangeUpdate</a> and <a href="https://github.com/kriete/PlotBokehLatestMoorings">PlotBokehLatestMoorings</a> for additional inspiration.

#Notes
We use simple web scraping from the socib thredds server to obtain the opendap links to the desired weather station data.

Also, we create a javascript callback to automatically adjust the y-axis according to the current zoom-extend.

The QC thresholds/definitions are stored internally. No connection to the database is required nor implemented.

The QC tests (range, spike, gradient, stationary) are implemented but need small adjustments like using prior good data etc. However, this shouldn't affect the overall scope of this protoype.

The program creates one HTML file for each station and processes the variables Air Pressure, Wind Speed, Air Temperature and Relative Humidity.

!Please note that this repo has no setup! Entry point is the ProcessingManager.py!

#Latest Changes
Improved configuration to set desired year and month.

Added configuration to process only single stations (if desired).

Removed hard-coded paths.

Output directory must now be specified in the config.ini.

Prevented opening of new tabs in browser after processing a weather station.

Added possibility to use webgl for plotting (significantly faster rendering, but with some small visual "problems").

Removed toolbar from plots to prevent documented bug (11.07.) because of visual styling.

Added some configuration loading functions.

Tested with newest bokeh version (0.12).

#Screenshot of interactive html output
![...](/img/overview.png?raw=true "HTML bokeh output")
![...](/img/zoomed.png?raw=true "HTML bokeh output")

#Dependencies
<ul>
  <li>numpy</li>
  <li>pandas</li>
  <li>lxml</li>
  <li>netCDF4</li>
  <li>bokeh</li>
  <li>matplotlib</li>
  <li>pytz</li>
</ul>

