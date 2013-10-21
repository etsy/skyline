import socket
from os import kill, getpid
from Queue import Full
from multiprocessing import Process
from struct import Struct, unpack
from msgpack import unpackb
from cPickle import loads

import logging
import settings

logger = logging.getLogger("HorizonLog")


class Listen(Process):
    """
    The listener is responsible for listening on a port.
    """
    def __init__(self, port, queue, parent_pid, type="pickle"):
        super(Listen, self).__init__()
        try:
            self.ip = settings.HORIZON_IP
        except AttributeError:
            # Default for backwards compatibility
            self.ip = socket.gethostname()
        self.port = port
        self.q = queue
        self.daemon = True
        self.parent_pid = parent_pid
        self.current_pid = getpid()
        self.type = type

    def gen_unpickle(self, infile):
        """
        Generate a pickle from a stream
        """
        try:
            bunch = loads(infile)
            yield bunch
        except EOFError:
            return

    def read_all(self, sock, n):
        """
        Read n bytes from a stream
        """
        data = ''
        while n > 0:
            buf = sock.recv(n)
            n -= len(buf)
            data += buf
        return data

    def check_if_parent_is_alive(self):
        """
        Self explanatory
        """
        try:
            kill(self.current_pid, 0)
            kill(self.parent_pid, 0)
        except:
            exit(0)

    def listen_pickle(self):
        """
        Listen for pickles over tcp
        """
        while 1:
            try:
                # Set up the TCP listening socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.ip, self.port))
                s.setblocking(1)
                s.listen(5)
                logger.info('listening over tcp for pickles on %s' % self.port)

                (conn, address) = s.accept()
                logger.info('connection from %s:%s' % (address[0], self.port))

                chunk = []
                while 1:
                    self.check_if_parent_is_alive()
                    try:
                        length = Struct('!I').unpack(self.read_all(conn, 4))
                        body = self.read_all(conn, length[0])

                        # Iterate and chunk each individual datapoint
                        for bunch in self.gen_unpickle(body):
                            for metric in bunch:
                                chunk.append(metric)

                                # Queue the chunk and empty the variable
                                if len(chunk) > settings.CHUNK_SIZE:
                                    try:
                                        self.q.put(list(chunk), block=False)
                                        chunk[:] = []

                                    # Drop chunk if queue is full
                                    except Full:
                                        logger.info('queue is full, dropping datapoints')
                                        chunk[:] = []

                    except Exception as e:
                        logger.info(e)
                        logger.info('incoming connection dropped, attempting to reconnect')
                        break

            except Exception as e:
                logger.info('can\'t connect to socket: ' + str(e))
                break

    def listen_udp(self):
        """
        Listen over udp for MessagePack strings
        """
        while 1:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind((self.ip, self.port))
                logger.info('listening over udp for messagepack on %s' % self.port)

                chunk = []
                while 1:
                    self.check_if_parent_is_alive()
                    data, addr = s.recvfrom(1024)
                    metric = unpackb(data)
                    chunk.append(metric)

                    # Queue the chunk and empty the variable
                    if len(chunk) > settings.CHUNK_SIZE:
                        try:
                            self.q.put(list(chunk), block=False)
                            chunk[:] = []

                        # Drop chunk if queue is full
                        except Full:
                            logger.info('queue is full, dropping datapoints')
                            chunk[:] = []

            except Exception as e:
                logger.info('can\'t connect to socket: ' + str(e))
                break

    def run(self):
        """
        Called when process intializes.
        """
        logger.info('started listener')

        if self.type == 'pickle':
            self.listen_pickle()
        elif self.type == 'udp':
            self.listen_udp()
        else:
            logging.error('unknown listener format')
