from os import kill
from redis import StrictRedis, WatchError
from multiprocessing import Process
from threading import Thread
from msgpack import Unpacker, packb
from types import TupleType
from time import time, sleep

import logging
import settings

logger = logging.getLogger("HorizonLog")


class Roomba(Thread):
    """
    The Roomba is responsible for deleting keys older than DURATION.
    """
    def __init__(self, parent_pid, skip_mini):
        super(Roomba, self).__init__()
        self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
        self.daemon = True
        self.parent_pid = parent_pid
        self.skip_mini = skip_mini

    def check_if_parent_is_alive(self):
        """
        Self explanatory.
        """
        try:
            kill(self.parent_pid, 0)
        except:
            exit(0)

    def vacuum(self, i, namespace, duration):
        """
        Trim metrics that are older than settings.FULL_DURATION and
        purge old metrics.
        """
        begin = time()

        # Discover assigned metrics
        unique_metrics = list(self.redis_conn.smembers(namespace + 'unique_metrics'))
        keys_per_processor = len(unique_metrics) / settings.ROOMBA_PROCESSES
        assigned_max = i * keys_per_processor
        assigned_min = assigned_max - keys_per_processor
        assigned_keys = range(assigned_min, assigned_max)

        # Compile assigned metrics
        assigned_metrics = [unique_metrics[index] for index in assigned_keys]

        euthanized = 0
        blocked = 0
        for i in xrange(len(assigned_metrics)):
            self.check_if_parent_is_alive()

            pipe = self.redis_conn.pipeline()
            now = time()
            key = assigned_metrics[i]

            try:
                # WATCH the key
                pipe.watch(key)

                # Everything below NEEDS to happen before another datapoint
                # comes in. If your data has a very small resolution (<.1s),
                # this technique may not suit you.
                raw_series = pipe.get(key)
                unpacker = Unpacker(use_list = False)
                unpacker.feed(raw_series)
                timeseries = sorted([unpacked for unpacked in unpacker])

                # Put pipe back in multi mode
                pipe.multi()

                # There's one value. Purge if it's too old
                try:
                    if not isinstance(timeseries[0], TupleType):
                        if timeseries[0] < now - duration:
                            pipe.delete(key)
                            pipe.srem(namespace + 'unique_metrics', key)
                            pipe.execute()
                            euthanized += 1
                        continue
                except IndexError:
                    continue

                # Check if the last value is too old and purge
                if timeseries[-1][0] < now - duration:
                    pipe.delete(key)
                    pipe.srem(namespace + 'unique_metrics', key)
                    pipe.execute()
                    euthanized += 1
                    continue

                # Remove old datapoints and duplicates from timeseries
                temp = set()
                temp_add = temp.add
                delta = now - duration
                trimmed = [
                    tuple for tuple in timeseries
                    if tuple[0] > delta
                    and tuple[0] not in temp
                    and not temp_add(tuple[0])
                ]

                # Purge if everything was deleted, set key otherwise
                if len(trimmed) > 0:
                    # Serialize and turn key back into not-an-array
                    btrimmed = packb(trimmed)
                    if len(trimmed) <= 15:
                        value = btrimmed[1:]
                    elif len(trimmed) <= 65535:
                        value = btrimmed[3:]
                    else:
                        value = btrimmed[5:]
                    pipe.set(key, value)
                else:
                    pipe.delete(key)
                    pipe.srem(namespace + 'unique_metrics', key)
                    euthanized += 1

                pipe.execute()

            except WatchError:
                blocked += 1
                assigned_metrics.append(key)
            except Exception as e:
                # If something bad happens, zap the key and hope it goes away
                pipe.delete(key)
                pipe.srem(namespace + 'unique_metrics', key)
                pipe.execute()
                euthanized += 1
                logger.info(e)
                logger.info("Euthanizing " + key)
            finally:
                pipe.reset()

        logger.info('operated on %s in %f seconds' % (namespace, time() - begin))
        logger.info('%s keyspace is %d' % (namespace, (len(assigned_metrics) - euthanized)))
        logger.info('blocked %d times' % blocked)
        logger.info('euthanized %d geriatric keys' % euthanized)

        if (time() - begin < 30):
            logger.info('sleeping due to low run time...')
            sleep(10)

    def run(self):
        """
        Called when process initializes.
        """
        logger.info('started roomba')

        while 1:
            now = time()

            # Make sure Redis is up
            try:
                self.redis_conn.ping()
            except:
                logger.error('roomba can\'t connect to redis at socket path %s' % settings.REDIS_SOCKET_PATH)
                sleep(10)
                self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
                continue

            # Spawn processes
            pids = []
            for i in range(1, settings.ROOMBA_PROCESSES + 1):
                if not self.skip_mini:
                    p = Process(target=self.vacuum, args=(i, settings.MINI_NAMESPACE, settings.MINI_DURATION + settings.ROOMBA_GRACE_TIME))
                    pids.append(p)
                    p.start()

                p = Process(target=self.vacuum, args=(i, settings.FULL_NAMESPACE, settings.FULL_DURATION + settings.ROOMBA_GRACE_TIME))
                pids.append(p)
                p.start()

            # Send wait signal to zombie processes
            for p in pids:
                p.join()
