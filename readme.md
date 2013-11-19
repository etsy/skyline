## Skyline

[![Build Status](https://travis-ci.org/etsy/skyline.png)](https://travis-ci.org/etsy/skyline)

![x](https://raw.github.com/etsy/skyline/master/screenshot.png)

Skyline is a real-time* anomaly detection* system*, built to enable passive
monitoring of hundreds of thousands of metrics, without the need to configure a
model/thresholds for each one, as you might do with Nagios. It is designed to be
used wherever there are a large quantity of high-resolution timeseries which
need constant monitoring. Once a metrics stream is set up (from StatsD or
Graphite or other source), additional metrics are automatically added to Skyline
for analysis. Skyline's easily extendible algorithms automatically detect what
it means for each metric to be anomalous. After Skyline detects an anomalous
metric, it surfaces the entire timeseries to the webapp, where the anomaly can be
viewed and acted upon.

Read the details in the [wiki](https://github.com/etsy/skyline/wiki).

## Install

1. `sudo pip install -r requirements.txt` for the easy bits

2. Install numpy, scipy, pandas, patsy, statsmodels, msgpack_python in that
order.

2. You may have trouble with SciPy. If you're on a Mac, try:

* `sudo port install gcc48`
* `sudo ln -s /opt/local/bin/gfortran-mp-4.8 /opt/local/bin/gfortran`
* `sudo pip install scipy`

On Debian, apt-get works well for Numpy and SciPy. On Centos, yum should do the
trick. If not, hit the Googles, yo.

3. `cp src/settings.py.example src/settings.py`

4. Add directories: 

``` 
sudo mkdir /var/log/skyline
sudo mkdir /var/run/skyline
sudo mkdir /var/log/redis
sudo mkdir /var/dump/
```

5. Download and install the latest Redis release

6. Start 'er up

* `cd skyline/bin`
* `sudo redis-server redis.conf`
* `sudo ./horizon.d start`
* `sudo ./analyzer.d start`
* `sudo ./webapp.d start`

By default, the webapp is served on port 1500.

7. Check the log files to ensure things are running.

[Debian + Vagrant specific, if you prefer](https://github.com/etsy/skyline/wiki/Debian-and-Vagrant-Installation-Tips)

### Gotchas

* If you already have a Redis instance running, it's recommended to kill it and
restart using the configuration settings provided in bin/redis.conf

* Be sure to create the log directories.

### Hey! Nothing's happening!
Of course not. You've got no data! For a quick and easy test of what you've 
got, run this:
```
cd utils
python seed_data.py
```
This will ensure that the Horizon
service is properly set up and can receive data. For real data, you have some 
options - see [wiki](https://github.com/etsy/skyline/wiki/Getting-Data-Into-Skyline)

Once you get real data flowing through your system, the Analyzer will be able
start analyzing for anomalies!

### Alerts
Skyline can alert you! In your settings.py, add any alerts you want to the ALERTS
list, according to the schema `(metric keyword, strategy, expiration seconds)` where
`strategy` is one of `smtp`, `hipchat`, or `pagerduty`. You can also add your own
alerting strategies. For every anomalous metric, Skyline will search for the given
keyword and trigger the corresponding alert(s). To prevent alert fatigue, Skyline
will only alert once every <expiration seconds> for any given metric/strategy
combination. To enable Hipchat integration, uncomment the python-simple-hipchat
line in the requirements.txt file.

### How do you actually detect anomalies?
An ensemble of algorithms vote. Majority rules. Batteries __kind of__ included.
See [wiki](https://github.com/etsy/skyline/wiki/Analyzer)

### Architecture
See the rest of the
[wiki](https://github.com/etsy/skyline/wiki)

### Contributions
1. Clone your fork
2. Hack away
3. If you are adding new functionality, document it in the README or wiki
4. If necessary, rebase your commits into logical chunks, without errors
5. Verfiy your code by running the test suite and pep8, adding additional tests if able.
6. Push the branch up to GitHub
7. Send a pull request to the etsy/skyline project.

We actively welcome contributions. If you don't know where to start, try
checking out the [issue list](https://github.com/etsy/skyline/issues) and
fixing up the place. Or, you can add an algorithm - a goal of this project
is to have a very robust set of algorithms to choose from.

Also, feel free to join the 
[skyline-dev](https://groups.google.com/forum/#!forum/skyline-dev) mailing list
for support and discussions of new features.

(*depending on your data throughput, *you might need to write your own
algorithms to handle your exact data, *it runs on one box)
