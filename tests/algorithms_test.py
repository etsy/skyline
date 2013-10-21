import unittest2 as unittest
from mock import Mock, patch
from time import time

import sys
from os.path import dirname, abspath

sys.path.insert(0, dirname(dirname(abspath(__file__))) + '/src')
sys.path.insert(0, dirname(dirname(abspath(__file__))) + '/src/analyzer')

import algorithms
import settings


class TestAlgorithms(unittest.TestCase):
    """
    Test all algorithms with a common, simple/known anomalous data set
    """

    def _addSkip(self, test, reason):
        print reason

    def data(self, ts):
        """
        Mostly ones (1), with a final value of 1000
        """
        timeseries = map(list, zip(map(float, range(int(ts) - 86400, int(ts) + 1)), [1] * 86401))
        timeseries[-1][1] = 1000
        timeseries[-2][1] = 1
        timeseries[-3][1] = 1
        return ts, timeseries

    def test_tail_avg(self):
        _, timeseries = self.data(time())
        self.assertEqual(algorithms.tail_avg(timeseries), 334)

    def test_grubbs(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.grubbs(timeseries))

    @patch.object(algorithms, 'time')
    def test_first_hour_average(self, timeMock):
        timeMock.return_value, timeseries = self.data(time())
        self.assertTrue(algorithms.first_hour_average(timeseries))

    def test_stddev_from_average(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.stddev_from_average(timeseries))

    def test_stddev_from_moving_average(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.stddev_from_moving_average(timeseries))

    def test_mean_subtraction_cumulation(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.mean_subtraction_cumulation(timeseries))

    @patch.object(algorithms, 'time')
    def test_least_squares(self, timeMock):
        timeMock.return_value, timeseries = self.data(time())
        self.assertTrue(algorithms.least_squares(timeseries))

    def test_histogram_bins(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.histogram_bins(timeseries))

    @patch.object(algorithms, 'time')
    def test_run_selected_algorithm(self, timeMock):
        timeMock.return_value, timeseries = self.data(time())
        result, ensemble, datapoint = algorithms.run_selected_algorithm(timeseries, "test.metric")
        self.assertTrue(result)
        self.assertTrue(len(filter(None, ensemble)) >= settings.CONSENSUS)
        self.assertEqual(datapoint, 1000)

    @unittest.skip('Fails inexplicable in certain environments.')
    @patch.object(algorithms, 'CONSENSUS')
    @patch.object(algorithms, 'ALGORITHMS')
    @patch.object(algorithms, 'time')
    def test_run_selected_algorithm_runs_novel_algorithm(self, timeMock,
                                                         algorithmsListMock, consensusMock):
        """
        Assert that a user can add their own custom algorithm.

        This mocks out settings.ALGORITHMS and settings.CONSENSUS to use only a
        single custom-defined function (alwaysTrue)
        """
        algorithmsListMock.__iter__.return_value = ['alwaysTrue']
        consensusMock = 1
        timeMock.return_value, timeseries = self.data(time())

        alwaysTrue = Mock(return_value=True)
        with patch.dict(algorithms.__dict__, {'alwaysTrue': alwaysTrue}):
            result, ensemble, tail_avg = algorithms.run_selected_algorithm(timeseries)

        alwaysTrue.assert_called_with(timeseries)
        self.assertTrue(result)
        self.assertEqual(ensemble, [True])
        self.assertEqual(tail_avg, 334)


if __name__ == '__main__':
    unittest.main()
