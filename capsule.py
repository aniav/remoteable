
import uuid

from remoteable.serializable import Serializable

class Capsule(Serializable):
	_registry = {} 

	@classmethod
	def build(cls, data):
		raise NotImplementedError(cls)

	def data(self):
		raise NotImplementedError(self)
	
	@classmethod
	def can_wrap(self, object_class):
		raise NotImplementedError(self)
	
	@classmethod
	def wrap(cls, obj):
		for _serial, subclass in cls._registry.iteritems():
			if subclass.can_wrap(obj.__class__):
				return subclass.wrap(obj)
		raise TypeError(obj.__class__)
		
	def client_value(self, proxy):
		raise NotImplementedError(self)
	
	def server_value(self, server):
		raise NotImplementedError(cls)

class HandleCapsule(Capsule):
	serial = 'handle'
	
	def __init__(self, id):
		self._id = id
	
	@classmethod
	def can_wrap(cls, object_class):
		from remoteable.client import RemoteHandle
		return issubclass(object_class, RemoteHandle)
	
	@classmethod
	def wrap(cls, obj):
		return HandleCapsule(obj._id) # TODO Not exactly right 
	
	@classmethod
	def build(cls, data):
		return cls(uuid.UUID(hex = data['id']))

	def data(self):
		return {'id': self._id.hex}

	def client_value(self, proxy):
		return proxy.handle(self._id)
	
	def server_value(self, server):
		return server.access(self._id)

class RawCapsule(Capsule):
	serial = 'raw'

	serializator = {
		'int': int,
		'str': str,
		'bool': bool,
	}

	def __init__(self, value, variant):
		self._variant = variant
		self._value = value

	@classmethod
	def can_wrap(cls, object_class):
		return issubclass(object_class, tuple(cls.serializator.values()))
	
	@classmethod
	def wrap(cls, obj):
		for name, type in cls.serializator.iteritems():
			if isinstance(obj, type):
				return RawCapsule(obj, name)
	
	@classmethod
	def build(cls, data):
		variant = data['variant']
		deserialize = cls.serializator[variant]
		value = deserialize(data['data'])
		return cls(value, variant)

	def data(self):
		serialize = self.serializator[self._variant]
		return {
			'data': serialize(self._value),
			'variant': self._variant 
		}

	def client_value(self, _proxy):
		return self._value
	
	def server_value(self, _server):
		return self._value
	
class NoneCapsule(Capsule):
	serial = 'none'

	def __init__(self):
		pass

	@classmethod
	def can_wrap(cls, object_class):
		from types import NoneType
		return issubclass(object_class, NoneType)
	
	@classmethod
	def wrap(cls, obj):
		return NoneCapsule()
	
	@classmethod
	def build(cls, _data):
		return cls()
	
	def data(self):
		return {}
	
	def client_value(self, _proxy):
		return None
	
	def server_value(self, _server):
		return None

HandleCapsule.register()
RawCapsule.register()
NoneCapsule.register()
