# python-jsoncodecs
provides easily customized de- and encoders for json and typecasting for json keys

##Usage
From here on I use the word 'codec' to describe a encoder/decoder pair. This may be inappropriate :P what do i know...

### Building a codec
```python
from jsoncodecs import build_codec, HexBytes
from datetime import date

encoder, decoder = build_codec('datetime', 'hex_bytes')

today = date.today()
hb = HexBytes(b'\x89')
d = {'some hex bytes': hb, 'what day is it?': today}

json_string = json.dumps(d, cls=encoder)
loaded_json = json.loads(json_string, cls=decoder)
```

`build_codec` takes as arguments the names of the handlers to be used *in the order that the should be applied*.
To see the handlers available with the library you can import `jsoncodecs.HANDLERS`
You can also provide your own handler classes as arguments.
`encoder, decoder = build_codec('datetime', MyOwnHandler)`
Handlers are applied left to right.

## Handlers
A handler is a class that implements de- and encoding of specific type of object. A codec can contain multiple handlers, which are applied in a in the order that they were built into the codec. If a handler doesn't know how to handle the object it will forward the object up through the handler chain. 
If no handlers handles the *encoding* of a object, the encoder will fall back to the default json encoder `json.JSONEncoder`. Depending of the object, this may raise an error.
If no handlers handles the *decoding* of a object, the decoder will fall back to returning the encoded json string

The handler must override the two methods of `BaseCodecHandler`:
```python
class BaseCodecHandler(object):
    def dict_to_object(self, _type, d):
        return super(BaseCodecHandler, self).dict_to_object(_type, d)

    def encode_obj(self, obj):
        return super(BaseCodecHandler, self).encode_obj(obj)
```

* `encode_obj(obj)` the method that encodes your object type.
* `dict_to_object(self, _type, d)` the method that decodes your object type
Both methods *must* call the super method as seen in `BaseCodecHandler` if it can't handle what it's been given

### Encoding
The encoded object should be a `dict` where the field `__type__` contains the name of the object type. This name can be arbitrary, but *must* correspond to the `_type` the handler looks for in dict_to_object.
If any part of the encoded object in not json serializeable you will have a bad time...

### Decoding
your method should check for the object type provided in `_type`. If found you should reconstruct the object using the dictionary `d`. `d` will *not* contain the key/val `__type__` 
