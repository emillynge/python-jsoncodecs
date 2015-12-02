from __future__ import (absolute_import, unicode_literals, print_function)
__author__ = 'emil'

# -*- coding: utf-8 -*-
"""
Created on Wed Sep 10 15:03:37 2014

@author: emil
"""

from datetime import datetime, date
import json
import abc
import re
from io import BytesIO
import imp
import sys
if sys.version_info.major >= 3:
    basestring = str
    
__all__ = ['HANDLERS', 'BaseCodecHandler', 'build_codec', 'HexBytes', 'KEYTYPECASTS', 'TYPECAST2TYPENAME']

class DecodeFailedException(Exception):
    pass

class EncodeFailedException(Exception):
    pass

class KeyTypecaster(object):
    def __init__(self, *types):
        self.typecasts = [getattr(self, t)() if isinstance(t, basestring) else t for t in types]

    @classmethod
    def available_types(cls):
        return [m for m in cls.__dict__.keys() if m[0] != '_' and m != 'available_types']

    @staticmethod
    def int():
        def isdigit(key):
            return key.isdigit()
        return isdigit, int, 'int'

    @staticmethod
    def float():
        regx = re.compile('^\d+\.\d+$')
        return regx.match, float, 'float'

    @staticmethod
    def float_all():
        regx = re.compile('^(\-\d+)|(\d+\.?\d*)$')
        return regx.match, float, 'float'


KEYTYPECASTS = KeyTypecaster.available_types()
TYPECAST2TYPENAME = dict((tc, KeyTypecaster(tc).typecasts[0][2]) for tc in KEYTYPECASTS)


class _BaseEncoder:
    @staticmethod
    def encode_obj(obj):
        raise EncodeFailedException


class _BaseDecoder:
    @staticmethod
    def dict_to_object(_type, d):
        raise DecodeFailedException()


class BaseEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(BaseEncoder, self).encode_obj(obj)
        except EncodeFailedException:
            return super(BaseEncoder, self).default(obj)


class BaseDecoder(json.JSONDecoder):
    def __init__(self, *args, **kargs):
        typecasts = kargs.pop('key_typecasts', list())
        self.key_typecasts = KeyTypecaster(*typecasts).typecasts

        super(BaseDecoder, self).__init__(*args, object_hook=self.check_for_type, **kargs)

    def check_for_type(self, d):
        if '__type__' not in d:
            if self.key_typecasts:
                for key in [k for k in d.keys()]:
                    for type_check, typecast, type_name in self.key_typecasts:
                        if type_check(key):
                            val = d.pop(key)
                            d[typecast(key)] = val
                            break
            return d

        _type = d.pop('__type__')
        try:
            return super(BaseDecoder, self).dict_to_object(_type, d)
        except DecodeFailedException:
            d['__type__'] = _type
            return d


class BaseCodecHandler(object):
    def dict_to_object(self, _type, d):
        return super(BaseCodecHandler, self).dict_to_object(_type, d)

    def encode_obj(self, obj):
        return super(BaseCodecHandler, self).encode_obj(obj)


class DateTimeHandler(BaseCodecHandler):
    def dict_to_object(self, _type, d):
        if _type == 'datetime':
            date_obj = datetime(**d)
            return date_obj
        if _type == 'date':
            date_obj = date(**d)
            return date_obj
        return super(DateTimeHandler, self).dict_to_object(_type, d)

    def encode_obj(self, obj):
        if isinstance(obj, datetime):
            return {
                '__type__' : 'datetime',
                'year' : obj.year,
                'month' : obj.month,
                'day' : obj.day,
                'hour' : obj.hour,
                'minute' : obj.minute,
                'second' : obj.second,
                'microsecond' : obj.microsecond,
            }
        if isinstance(obj, date):
            return {
                '__type__' : 'date',
                'year' : obj.year,
                'month' : obj.month,
                'day' : obj.day,
            }
        return super(DateTimeHandler, self).encode_obj(obj)

class HexBytes(bytearray):
    pass

class HexBytesHandler(BaseCodecHandler):
    def encode_obj(self, obj):
        if isinstance(obj, HexBytes):
            return {'__type__': 'hex_bytes', 'bytes': str(obj).encode('hex')}
        return super(HexBytesHandler, self).encode_obj(obj)

    def dict_to_object(self, _type, d):
        if _type == 'hex_bytes':
            return HexBytes(d['bytes'].decode('hex'))
        return super(HexBytesHandler, self).dict_to_object(_type, d)


class NumpyHandler(BaseCodecHandler):
    def dict_to_object(self, _type, d):
        if _type[:3] == 'np.':
            import numpy as np
            if _type == 'np.array':
                tp = np.array

            if _type == 'np.matrix':
                tp = np.matrix

            return tp(d.pop('array'), **d)

        return super(NumpyHandler, self).dict_to_object(_type, d)

    def encode_obj(self, obj):
        import numpy as np
        if isinstance(obj, np.matrix):
            return {'__type__': 'np.matrix', 'array': obj.tolist(), 'dtype': obj.dtype.name}

        if isinstance(obj, np.ndarray):
            return {'__type__': 'np.array', 'array': obj.tolist(), 'dtype': obj.dtype.name}

        return super(NumpyHandler, self).encode_obj(obj)



class ExcelHandler(BaseCodecHandler):
    def dict_to_object(self, _type, d):
        if _type[:9] == 'openpyxl.':
            from openpyxl.reader.excel import load_workbook
            if _type == 'openpyxl.wb':
                fp = BytesIO(d['data'])
                fp.seek(0)
                wb = load_workbook(fp)
                return wb
        return super(ExcelHandler, self).dict_to_object(_type, d)

    def encode_obj(self, obj):
        from openpyxl.workbook import Workbook
        if isinstance(obj, Workbook):
            from openpyxl.writer.excel import save_virtual_workbook
            return {'__type__': 'openpyxl.wb', 'data': HexBytes(save_virtual_workbook(obj))}

        return super(ExcelHandler, self).encode_obj(obj)

_HANDLERS = {'datetime': [DateTimeHandler],
            'hex_bytes': [HexBytesHandler],
             'numpy': [NumpyHandler],
             'excel': [ExcelHandler, HexBytesHandler]}  # We need Hexbytes to serialize zipped excel files

HANDLERS = tuple(_HANDLERS.keys())

def build_codec(name, *handlers):
    module = imp.new_module('JsonCodecs')
    module.__dict__['BaseEncoder'] = BaseEncoder
    module.__dict__['BaseDecoder'] = BaseDecoder
    module.__dict__['_BaseEncoder'] = _BaseEncoder
    module.__dict__['_BaseDecoder'] = _BaseDecoder

    encoder = "class {name}Encoder(BaseEncoder,\n".format(name=name)
    decoder = "class {name}Decoder(BaseDecoder,\n".format(name=name)
    handler_set = set()

    for handler in handlers:
        if isinstance(handler, basestring) and handler in _HANDLERS:
            _handlers = _HANDLERS[handler]
        elif issubclass(handler, BaseCodecHandler):
            _handlers = [handler]
        else:
            raise Exception('Unknown handler {0}'.format(handler))
        for _handler in _handlers:
            if _handler in handler_set:
                continue
            handler_set.add(_handler)
            handler_name = _handler.__name__
            module.__dict__[handler_name] = _handler
            encoder += handler_name + ',\n'
            decoder += handler_name + ',\n'
    encoder += '_BaseEncoder):\n    pass'
    decoder += '_BaseDecoder):\n    pass'

    exec(encoder, module.__dict__)
    exec(decoder, module.__dict__)
    return getattr(module, name + 'Encoder'), getattr(module, name + 'Decoder')

