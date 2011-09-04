import uuid

from types import NoneType

from remoteable.serializable import Serializable

class Capsule(Serializable):
	_registry = {} 

	@classmethod
	def can_wrap(cls, object_class):
		raise NotImplementedError(cls)
	
	@classmethod
	def wrap(cls, obj):
		for _serial, subclass in cls._registry.iteritems():
			if subclass.can_wrap(obj.__class__):
				return subclass.wrap(obj)
		raise TypeError(obj.__class__)
		
	def proxy_value(self, proxy):
		raise NotImplementedError(self)
	
	def actual_value(self, actual):
		raise NotImplementedError(self)

class HandleCapsule(Capsule):
	serial = 'handle'
	
	def __init__(self, id):
		Capsule.__init__(self)
		self._id = id
	
	@classmethod
	def can_wrap(cls, object_class):
		from remoteable.client import RemoteHandle
		return issubclass(object_class, RemoteHandle)
	
	@classmethod
	def wrap(cls, obj):
		# pylint: disable=W0212
		# HandleCapsule is priviledged to access RemoteHandle _id
		return HandleCapsule(obj._id)
	
	@classmethod
	def build(cls, data):
		return cls(uuid.UUID(hex = data['id']))

	def data(self):
		return {'id': self._id.hex}

	def proxy_value(self, proxy):
		return proxy.handle(self._id)
	
	def actual_value(self, actual):
		return actual.access(self._id)

class RawCapsule(Capsule):
	serial = 'raw'

	serializator = {
		'int': int,
		'str': str,
		'bool': bool,
	}

	def __init__(self, value, variant):
		Capsule.__init__(self)
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

	def proxy_value(self, _proxy):
		return self._value
	
	def actual_value(self, _actual):
		return self._value

class NoneCapsule(Capsule):
	serial = 'none'

	@classmethod
	def can_wrap(cls, object_class):
		return issubclass(object_class, NoneType)
	
	@classmethod
	def wrap(cls, _obj):
		return NoneCapsule()
	
	# pylint: disable=R0801
	# same as remoteable.response.EmptyResponse, but these are not related
	@classmethod
	def build(cls, _data):
		return cls()
	
	def data(self):
		return {}
	
	def proxy_value(self, _proxy):
		return None
	
	def actual_value(self, _actual):
		return None

HandleCapsule.register()
RawCapsule.register()
NoneCapsule.register()
