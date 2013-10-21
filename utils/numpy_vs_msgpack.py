import time
import timeit
import msgpack
import numpy
import random

"""
Numpy decoding achieves faster results because of the reshape function.
It might be worth it to use Numpy encoding/decoding instead of MessagePack
at some point, for a sacrifice in operability.
"""

array = [[random.randint(1, 1000), random.randint(1, 1000)] for x in range(1, 8000)]
numpy_list = numpy.array(array).tostring()
msg_list = msgpack.packb(array)


def msgpack_decode():
    unpacker = msgpack.Unpacker()
    unpacker.feed(msg_list)
    timeseries = [unpacked for unpacked in unpacker]


def numpy_decode():
    raw = numpy.fromstring(numpy_list)
    s = raw.size
    timeseries = raw.reshape((s / 2, 2))


if __name__ == '__main__':
    import timeit
    print("MessagePack: " + str(timeit.timeit("msgpack_decode()", setup="from __main__ import msgpack_decode", number=3000)))
    print("Numpy: " + str(timeit.timeit("numpy_decode()", setup="from __main__ import numpy_decode", number=3000)))
