import redis
import msgpack
import sys
import json
import socket
import time
import pickle
from struct import Struct, pack
from os.path import dirname, abspath
from multiprocessing import Process, Manager, log_to_stderr

# add the shared settings file to namespace
sys.path.insert(0, ''.join((dirname(dirname(abspath(__file__))), "/src" )))
import settings

if __name__ == "__main__":
    print "Connecting to Redis..."
    r = redis.StrictRedis(unix_socket_path=settings.REDIS_SOCKET_PATH)
    time.sleep(5)

    print 'Loading data over UDP via Horizon...'
    metric = 'horizon.test.udp'
    initial = int(time.time()) - settings.MAX_RESOLUTION

    with open('data.json', 'r') as f:
      data = json.loads(f.read())
      series = data['results']
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

      for datapoint in series:
        datapoint[0] = initial
        initial += 1
        packet = msgpack.packb((metric, datapoint))
        sock.sendto(packet, (socket.gethostname(), settings.UDP_PORT))

    time.sleep(5)
    try:
        x = r.smembers('metrics.unique_metrics')
        if x == None:
        	raise Exception
        x = r.smembers('mini.unique_metrics')
        if x == None:
        	raise Exception
        x = r.get('metrics.horizon.test.udp')
        if x == None:
        	raise Exception
        x = r.get('mini.horizon.test.udp')
        if x == None:
        	raise Exception

        print "Congratulations! The data made it in. The Horizon pipeline seems to be working."
    except:
        print "Woops, looks like the metrics didn't make it into Horizon. Try again?"
