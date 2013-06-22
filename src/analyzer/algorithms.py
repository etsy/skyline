import pandas
import numpy as np
import scipy
import statsmodels.api as sm
from time import time
import traceback
import logging

from settings import (
    ALGORITHMS,
    CONSENSUS,
    FULL_DURATION,
    MAX_TOLERABLE_BOREDOM,
    MIN_TOLERABLE_LENGTH,
    STALE_PERIOD
)

from algorithm_exceptions import *

logger = logging.getLogger("AnalyzerLog")

"""
This is no man's land. Do anything you want in here,
as long as you return a boolean that determines whether the input
timeseries is anomalous or not.

To add an algorithm, define it here, and add its name to settings.ALGORITHMS.
"""

def tail_avg(timeseries):
    """
    This is a utility function used to calculate the average of the last three
    datapoints in the series as a measure, instead of just the last datapoint.
    It reduces noise, but it also reduces sensitivity and increases the delay
    to detection.
    """
    try:
        t = (timeseries[-1][1] + timeseries[-2][1] + timeseries[-3][1]) / 3
        return t
    except IndexError:
        return timeseries[-1][1]

def grubbs(timeseries):
    """
    A timeseries is anomalous if the Z score is greater than the Grubb's score.
    """

    series = scipy.array([x[1] for x in timeseries])
    stdDev = scipy.std(series)
    mean = np.mean(series)
    tail_average = tail_avg(timeseries)
    z_score = (tail_average - mean) / stdDev
    len_series = len(series)
    threshold = scipy.stats.t.isf(.05 / (2 * len_series) , len_series - 2)
    threshold_squared = threshold * threshold
    grubbs_score = ((len_series - 1) / np.sqrt(len_series)) * np.sqrt(threshold_squared / (len_series - 2 + threshold_squared))

    return z_score > grubbs_score

def first_hour_average(timeseries):
    """
    Calcuate the simple average over one hour, FULL_DURATION seconds ago.
    A timeseries is anomalous if the average of the last three datapoints
    are outside of three standard deviations of this value.
    """
    last_hour_threshold = time() - (FULL_DURATION - 3600)
    series = pandas.Series([x[1] for x in timeseries if x[0] < last_hour_threshold])
    mean = (series).mean()
    stdDev = (series).std()
    t = tail_avg(timeseries)

    return abs(t - mean) > 3 * stdDev

def simple_stddev_from_moving_average(timeseries):
    """
    A timeseries is anomalous if the absolute value of the average of the latest
    three datapoint minus the moving average is greater than one standard
    deviation of the average. This does not exponentially weight the MA and so
    is better for detecting anomalies with respect to the entire series.
    """
    series = pandas.Series([x[1] for x in timeseries])
    mean = series.mean()
    stdDev = series.std()
    t = tail_avg(timeseries)

    return abs(t - mean) > 3 * stdDev

def stddev_from_moving_average(timeseries):
    """
    A timeseries is anomalous if the absolute value of the average of the latest
    three datapoint minus the moving average is greater than one standard
    deviation of the moving average. This is better for finding anomalies with
    respect to the short term trends.
    """
    series = pandas.Series([x[1] for x in timeseries])
    expAverage = pandas.stats.moments.ewma(series, com=50)
    stdDev = pandas.stats.moments.ewmstd(series, com=50)

    return abs(series.iget(-1) - expAverage.iget(-1)) > 3 * stdDev.iget(-1)

def mean_subtraction_cumulation(timeseries):
    """
    A timeseries is anomalous if the value of the next datapoint in the
    series is farther than a standard deviation out in cumulative terms
    after subtracting the mean from each data point.
    """

    series = pandas.Series([x[1] if x[1] else 0 for x in timeseries])
    series = series - series[0:len(series) - 1].mean()
    stdDev = series[0:len(series) - 1].std()
    expAverage = pandas.stats.moments.ewma(series, com=15)

    return abs(series.iget(-1)) > 3 * stdDev

def least_squares(timeseries):
    """
    A timeseries is anomalous if the average of the last three datapoints
    on a projected least squares model is greater than three sigma.
    """

    x = np.array([t[0] for t in timeseries])
    y = np.array([t[1] for t in timeseries])
    A = np.vstack([x, np.ones(len(x))]).T
    results = np.linalg.lstsq(A, y)
    residual = results[1]
    m, c = np.linalg.lstsq(A, y)[0]
    errors = []
    for i, value in enumerate(y):
    	projected = m * x[i] + c
    	error = value - projected
    	errors.append(error)

    if len(errors) < 3:
    	return False

    std_dev = scipy.std(errors)
    t = (errors[-1] + errors[-2] + errors[-3]) / 3

    return abs(t) > std_dev * 3 and round(std_dev) != 0 and round(t) != 0

def histogram_bins(timeseries):
    """
    A timeseries is anomalous if the average of the last three datapoints falls
    into a histogram bin with less than 20 other datapoints (you'll need to tweak
    that number depending on your data)

    Returns: the size of the bin which contains the tail_avg. Smaller bin size
    means more anomalous.
    """

    series = scipy.array([x[1] for x in timeseries])
    t = tail_avg(timeseries)
    h = np.histogram(series, bins=15)
    bins = h[1]
    for index, bin_size in enumerate(h[0]):
        if bin_size <= 20:
            # Is it in the first bin?
            if index == 0:
                if t <= bins[0]:
                    return True
            # Is it in the current bin?
            elif t >= bins[index] and t < bins[index + 1]:
                    return True

    return False


def run_selected_algorithm(timeseries):
    """
    Filter timeseries and run selected algorithm.
    """
    # Get rid of short series
    if len(timeseries) < MIN_TOLERABLE_LENGTH:
        raise TooShort()

    # Get rid of stale series
    if time() - timeseries[-1][0] > STALE_PERIOD:
        raise Stale()

    # Get rid of incomplete series
    duration = timeseries[-1][0] - timeseries[0][0]
    if duration < FULL_DURATION:
        raise Incomplete()

    # Get rid of boring series
    if len(set(item[1] for item in timeseries[-MAX_TOLERABLE_BOREDOM:])) == 1:
        raise Boring()

    try:
        ensemble = [globals()[algorithm](timeseries) for algorithm in ALGORITHMS]
        threshold = len(ensemble) - CONSENSUS
        if ensemble.count(False) <= threshold:
            return True, ensemble, tail_avg(timeseries)

        return False, ensemble, timeseries[-1][1]
    except:
        logging.error("Algorithm error: " + traceback.format_exc())
        return False, [], 1
