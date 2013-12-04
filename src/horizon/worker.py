from os import kill, system
from redis import StrictRedis, WatchError
from multiprocessing import Process
from Queue import Empty
from msgpack import packb
from time import time, sleep

import logging
import socket
import settings

logger = logging.getLogger("HorizonLog")


class Worker(Process):
    """
    The worker processes chunks from the queue and appends
    the latest datapoints to their respective timesteps in Redis.
    """
    def __init__(self, queue, parent_pid, skip_mini, canary=False):
        super(Worker, self).__init__()
        self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
        self.q = queue
        self.parent_pid = parent_pid
        self.daemon = True
        self.canary = canary
        self.skip_mini = skip_mini

    def check_if_parent_is_alive(self):
        """
        Self explanatory.
        """
        try:
            kill(self.parent_pid, 0)
        except:
            exit(0)

    def in_skip_list(self, metric_name):
        """
        Check if the metric is in SKIP_LIST.
        """
        for to_skip in settings.SKIP_LIST:
            if to_skip in metric_name:
                return True

        return False

    def send_graphite_metric(self, name, value):
        if settings.GRAPHITE_HOST != '':
            sock = socket.socket()
            sock.connect((settings.GRAPHITE_HOST, settings.CARBON_PORT))
            sock.sendall('%s %s %i\n' % (name, value, time()))
            sock.close()
            return True

        return False

    def run(self):
        """
        Called when the process intializes.
        """
        logger.info('started worker')

        FULL_NAMESPACE = settings.FULL_NAMESPACE
        MINI_NAMESPACE = settings.MINI_NAMESPACE
        MAX_RESOLUTION = settings.MAX_RESOLUTION
        full_uniques = FULL_NAMESPACE + 'unique_metrics'
        mini_uniques = MINI_NAMESPACE + 'unique_metrics'
        pipe = self.redis_conn.pipeline()

        while 1:

            # Make sure Redis is up
            try:
                self.redis_conn.ping()
            except:
                logger.error('worker can\'t connect to redis at socket path %s' % settings.REDIS_SOCKET_PATH)
                sleep(10)
                self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
                pipe = self.redis_conn.pipeline()
                continue

            try:
                # Get a chunk from the queue with a 15 second timeout
                chunk = self.q.get(True, 15)
                now = time()

                for metric in chunk:

                    # Check if we should skip it
                    if self.in_skip_list(metric[0]):
                        continue

                    # Bad data coming in
                    if metric[1][0] < now - MAX_RESOLUTION:
                        continue

                    # Append to messagepack main namespace
                    key = ''.join((FULL_NAMESPACE, metric[0]))
                    pipe.append(key, packb(metric[1]))
                    pipe.sadd(full_uniques, key)

                    if not self.skip_mini:
                        # Append to mini namespace
                        mini_key = ''.join((MINI_NAMESPACE, metric[0]))
                        pipe.append(mini_key, packb(metric[1]))
                        pipe.sadd(mini_uniques, mini_key)

                    pipe.execute()

                # Log progress
                if self.canary:
                    logger.info('queue size at %d' % self.q.qsize())
                    self.send_graphite_metric('skyline.horizon.queue_size', self.q.qsize())

            except Empty:
                logger.info('worker queue is empty and timed out')
            except WatchError:
                logger.error(key)
            except NotImplementedError:
                pass
            except Exception as e:
                logger.error("worker error: " + str(e))
