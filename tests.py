from __future__ import (unicode_literals, absolute_import, print_function)
__author__ = 'emil'
from jsoncodecs import (build_codec, HANDLERS, HexBytes, KEYTYPECASTS, TYPECAST2TYPENAME)
from datetime import datetime, date
import json
from itertools import product, permutations
from pprint import pformat
import numpy as np
from openpyxl import Workbook
from copy import deepcopy
hb = HexBytes(b'\x89')
d = {'handler_tests': {'hex_bytes': hb,
                       'datetime': [datetime.now(),  date.today()],
                       'numpy': [np.array([0], dtype=float), np.matrix([[1]])],
                       'excel': Workbook()},
     'typecast_tests': {1: ('int', 'float_all'), 2.2: ('float', 'float_all'), 2.: ('float_all',), .2: ('float_all',)}}
print('Original dict: \n{d}'.format(d=pformat(d)))

b'0x69'
def combinations(iterable):
    for combination in product(*zip(iterable, [None] * len(iterable))):
        for per in permutations([c for c in combination if c]):
            yield per
failures = list()
print('\n--- Tests ---')
for handlers in combinations(HANDLERS):
    _d = d
    unused_handlers = list()

    for key in d['handler_tests'].keys():
        if key not in handlers:
            unused_handlers.append((key, _d['handler_tests'].pop(key)))

    typecast2key = dict((val, key) for key, val in _d['typecast_tests'].iteritems())
    for typecasts in combinations(KEYTYPECASTS):
        en, de = build_codec('Test', *handlers)
        dump = json.dumps(_d, cls=en)
        loaded = json.loads(dump, cls=de, key_typecasts=typecasts)

        print("Handlers: {0}\nKey typecasts: {2}\n\torig dict: {4}\n\tjson dump: {1}\n\tload dict: {3}\n------".format(handlers,
                                                                                             dump,
                                                                                             typecasts, loaded, _d))
        for key, _typecasts in loaded['typecast_tests'].iteritems():
            if key in _d['typecast_tests']:
                ok_types = [TYPECAST2TYPENAME[_typecast] for _typecast in _typecasts]
                if type(key).__name__ not in ok_types:
                    failures.append({'typecast {0}'.format(_typecasts): {'typecasts': typecasts,
                                                      'handlers': handlers,
                                                      'orig': _d, 'dump': dump, 'load': loaded,
                                                        ' expect': ok_types, ' found': type(key).__name__ }})
            elif any(_typecast in typecasts for _typecast in _typecasts):
                failures.append({'typecast {0}'.format(_typecasts): {'typecasts': typecasts,
                                                                'handlers': handlers,
                                                                'orig': _d, 'dump': dump, 'load': loaded,
                                                                     ' expect': typecast2key[_typecasts],
                                                                     ' found': key}})

        for handler, val in loaded['handler_tests'].iteritems():
            if _d['handler_tests'][handler] != val:
                failures.append({'handler ' + handler: {'typecasts': typecasts,
                                                      'handlers': handlers,
                                                      'orig': _d, 'dump': dump, 'load': loaded,
                                                        ' expect': _d['handler_tests'][handler],
                                                        ' found': val}})
    while unused_handlers:
        _d['handler_tests'].update(dict([unused_handlers.pop()]))

if failures:
    raise Exception(pformat([''] + failures))
else:
    print("SUCCESS")


