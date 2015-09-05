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
import imp
__all__ = ['HANDLERS', 'build_codecs', 'HexBytes', 'KEYTYPECASTS', 'TYPECAST2TYPENAME']

class DecodeFailedException(Exception):
    pass

class EncodeFailedException(Exception):
    pass

class _BaseEncoder:
    @staticmethod
    def encode_obj(obj):
        raise EncodeFailedException

class BaseEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(BaseEncoder, self).encode_obj(obj)
        except EncodeFailedException:
            return super(BaseEncoder, self).default(obj)


class _BaseDecoder:
    @staticmethod
    def dict_to_object(_type, d):
        raise DecodeFailedException()

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
        regx = re.compile('^\d+\.?\d*$')
        return regx.match, float, 'float'


KEYTYPECASTS = KeyTypecaster.available_types()
TYPECAST2TYPENAME = dict((tc, KeyTypecaster(tc).typecasts[0][2]) for tc in KEYTYPECASTS)

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

_HANDLERS = {'datetime': DateTimeHandler,
            'hex_bytes': HexBytesHandler}
HANDLERS = tuple(_HANDLERS.keys())

def build_codecs(name, *handlers):
    module = imp.new_module('JsonCodecs')
    module.__dict__['BaseEncoder'] = BaseEncoder
    module.__dict__['BaseDecoder'] = BaseDecoder
    module.__dict__['_BaseEncoder'] = _BaseEncoder
    module.__dict__['_BaseDecoder'] = _BaseDecoder

    encoder = "class {name}Encoder(BaseEncoder,\n".format(name=name)
    decoder = "class {name}Decoder(BaseDecoder,\n".format(name=name)
    for handler in handlers:
        if isinstance(handler, basestring) and handler in _HANDLERS:
            _handler = _HANDLERS[handler]
        elif issubclass(handler, BaseCodecHandler):
            _handler = handler
        else:
            raise Exception('Unknown handler {0}'.format(handler))
        handler_name = _handler.__name__
        module.__dict__[handler_name] = _handler
        encoder += handler_name + ',\n'
        decoder += handler_name + ',\n'
    encoder += '_BaseEncoder):\n    pass'
    decoder += '_BaseDecoder):\n    pass'

    exec encoder in module.__dict__
    exec decoder in module.__dict__
    return getattr(module, name + 'Encoder'), getattr(module, name + 'Decoder')

