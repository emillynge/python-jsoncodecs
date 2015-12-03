from __future__ import (unicode_literals, absolute_import, print_function)
__author__ = 'emil'
from jsoncodecs import (build_codec, HANDLERS, HexBytes, KEYTYPECASTS, TYPECAST2TYPENAME)
from datetime import datetime, date
import json
from itertools import product, permutations
from pprint import pformat
import numpy as np
import sys
hb = HexBytes(b'\x89')
d = {'handler_tests': {'hex_bytes': hb,
                       'datetime': [datetime.now(),  date.today()],
                       'numpy': [np.array([0], dtype=float), np.matrix([[1]]), np.matrix([[complex(1, 2)]], dtype=np.complex)],
                       'complex': [complex(1.5+1j), complex(1.5j)]},
    'typecast_tests': {1: ('int', 'float_all'), 2.2: ('float', 'float_all'), 2.: ('float_all',), .2: ('float_all',)}}

if sys.version_info.major == 2:
    from openpyxl import Workbook
    from openpyxl.writer.excel import save_virtual_workbook
    d['handler_tests']['excel'] = Workbook()
else:
    basestring = str


try:
    import pandas as pd
    d['handler_tests']['data_frame'] = pd.DataFrame(data=np.matrix([[1, 2], [3, 4]]), index=['id1', 3], columns=['col1', 4])
except ImportError:
    pass
from copy import deepcopy, copy

     
print('Original dict: \n{d}'.format(d=pformat(d)))

def trunc(obj):
    if isinstance(obj, dict):
        return dict((key, trunc(val)) for key, val in obj.items())

    if isinstance(obj, list):
        return list(trunc(e) for e in obj)

    if isinstance(obj, tuple):
        return tuple(trunc(e) for e in obj)

    if isinstance(obj, (basestring, bytearray)):
        if len(obj) > 70:
            return obj[:30] + '...' + obj[-30:]
        return obj
    return obj

b'0x69'
def combinations(iterable):
    for combination in product(*zip(iterable, [None] * len(iterable))):
        _c = [c for c in combination if c]
        if len(_c) > 3:
            continue
        for per in permutations(_c):
            yield per
failures = list()
print('\n--- Tests ---')

def handler_cmp(obj, _obj, handler):
    if _obj is None:
        return False
    if handler == 'excel':
        bools = [save_virtual_workbook(obj) == save_virtual_workbook(obj) for i in range(3)]
        return sum(bools) > 1
    if handler == 'data_frame':
        res = obj.index.values == _obj.index.values
        if  res is False or False in res:
            return False

        res = obj.columns.values == _obj.columns.values
        if res is False or False in res:
            return False

        res = obj.values == _obj.values
        if res is False or False in res:
            return False

        return True
    return obj == _obj

for handlers in combinations(HANDLERS):
    if len(failures) > 5:
        break
    _d = copy(d)
    unused_handlers = list()

    for key in list(d['handler_tests'].keys()):
        if key not in handlers:
            unused_handlers.append((key, _d['handler_tests'].pop(key)))

    typecast2key = dict((val, key) for key, val in _d['typecast_tests'].items())
    for typecasts in combinations(KEYTYPECASTS):
        en, de = build_codec('Test', *handlers)
        _dump = None
        loaded = None
        try:
            _dump = json.dumps(_d, cls=en)
            loaded = json.loads(_dump, cls=de, key_typecasts=typecasts)
            dump = json.loads(_dump)
        except Exception as e:
            failures.append(failures.append({'Exception': {' typecasts': typecasts,
                                                                    ' handlers': handlers,
                                                                    'orig': _d, 'dump': trunc(_dump), 'load': trunc(loaded),
                                                                    '  error': trunc(str(e))}}))
            continue
        #print("Handlers: {0}\nKey typecasts: {2}\n\torig dict: {4}\n\tjson dump: {1}\n\tload dict: {3}\n------".format(handlers,
        #                                                                                     dump,
        #                                                                                     typecasts, loaded, _d))
        for key, _typecasts in loaded['typecast_tests'].items():
            if key in _d['typecast_tests']:
                ok_types = [TYPECAST2TYPENAME[_typecast] for _typecast in _typecasts]
                if type(key).__name__ not in ok_types:
                    failures.append({'typecast {0}'.format(_typecasts): {'typecasts': typecasts,
                                                      'handlers': handlers,
                                                     'orig': _d, 'dump': trunc(dump), 'load': trunc(loaded),
                                                        ' expect': ok_types, ' found': type(key).__name__ }})
            elif any(_typecast in typecasts for _typecast in _typecasts):
                failures.append({'typecast {0}'.format(_typecasts): {'typecasts': typecasts,
                                                                'handlers': handlers,
                                                                     'orig': _d, 'dump': trunc(dump), 'load': trunc(loaded),
                                                                     ' expect': typecast2key[_typecasts],
                                                                     ' found': trunc(key)}})

        for handler, val in loaded['handler_tests'].items():
            if not handler_cmp(_d['handler_tests'][handler], val, handler):
                failures.append({'handler ' + handler: {' typecasts': typecasts,
                                                      ' handlers': handlers,
                                                        'orig': _d, 'dump': trunc(dump), 'load': trunc(loaded),
                                                        '  expect': _d['handler_tests'][handler],
                                                        '  found': trunc(val)}})
    while unused_handlers:
        _d['handler_tests'].update(dict([unused_handlers.pop()]))

if failures:
    raise Exception(pformat([''] + failures))
else:
    print("SUCCESS")


