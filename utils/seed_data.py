#!/usr/bin/env python

import json
import os
import pickle
import socket
import sys
import time
from os.path import dirname, join, realpath
from multiprocessing import Manager, Process, log_to_stderr
from struct import Struct, pack

import redis
import msgpack

# Get the current working directory of this file.
# http://stackoverflow.com/a/4060259/120999
__location__ = realpath(join(os.getcwd(), dirname(__file__)))

# Add the shared settings file to namespace.
sys.path.insert(0, join(__location__, '..', 'src'))
import settings


class NoDataException(Exception):
    pass


def seed():
    print 'Loading data over UDP via Horizon...'
    metric = 'horizon.test.udp'
    metric_set = 'unique_metrics'
    initial = int(time.time()) - settings.MAX_RESOLUTION

    with open(join(__location__, 'data.json'), 'r') as f:
        data = json.loads(f.read())
        series = data['results']
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for datapoint in series:
            datapoint[0] = initial
            initial += 1
            packet = msgpack.packb((metric, datapoint))
            sock.sendto(packet, (socket.gethostname(), settings.UDP_PORT))

    print "Connecting to Redis..."
    r = redis.StrictRedis(unix_socket_path=settings.REDIS_SOCKET_PATH)
    time.sleep(5)

    try:
        x = r.smembers(settings.FULL_NAMESPACE + metric_set)
        if x is None:
            raise NoDataException

        x = r.get(settings.FULL_NAMESPACE + metric)
        if x is None:
            raise NoDataException

        #Ignore the mini namespace if OCULUS_HOST isn't set.
        if settings.OCULUS_HOST != "":
            x = r.smembers(settings.MINI_NAMESPACE + metric_set)
            if x is None:
                raise NoDataException

            x = r.get(settings.MINI_NAMESPACE + metric)
            if x is None:
                raise NoDataException

        print "Congratulations! The data made it in. The Horizon pipeline seems to be working."

    except NoDataException:
        print "Woops, looks like the metrics didn't make it into Horizon. Try again?"

if __name__ == "__main__":
    seed()
