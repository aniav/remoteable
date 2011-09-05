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
	handled = object
	# need definition in subclasses
	
	@classmethod
	def can_wrap(cls, object_class):
		return issubclass(object_class, cls.handled)

	@classmethod
	def wrap(cls, obj):
		return cls(obj)

	def __init__(self, value):
		Capsule.__init__(self)
		self._value = value

	@classmethod
	def build(cls, data):
		value = cls.handled(data['data'])
		return cls(value)

	def data(self):
		return {
			'data': self.handled(self._value),
		}

	def proxy_value(self, _proxy):
		return self._value
	
	def actual_value(self, _actual):
		return self._value


class IntegerCapsule(RawCapsule):
	serial = 'integer'
	handled = int

class StringCapsule(RawCapsule):
	serial = 'string'
	handled = str

class UnicodeCapsule(RawCapsule):
	serial = 'unicode'
	handled = unicode

class BooleanCapsule(RawCapsule):
	serial = 'boolean'
	handled = bool

class IterativeCapsule(RawCapsule):
	@classmethod
	def build(cls, data):
		value = cls.handled([Capsule.construct(i) for i in data['data']])
		return cls(value)

	def data(self):
		return {
			'data': [Capsule.wrap(i).serialized() for i in self._value],
		}

	def proxy_value(self, proxy):
		return self.handled([i.proxy_value(proxy) for i in self._value])
	
	def actual_value(self, actual):
		return self.handled([i.actual_value(actual) for i in self._value])

class ListCapsule(IterativeCapsule):
	serial = 'list'
	handled = list

class TupleCapsule(IterativeCapsule):
	serial = 'tuple'
	handled = tuple

class SetCapsule(IterativeCapsule):
	serial = 'set'
	handled = set

class DictionaryCapsule(RawCapsule):
	serial = 'dictionary'
	handled = dict

	@classmethod
	def build(cls, data):
		built = cls.handled()
		for key, value in data['data'].iteritems():
			built[key] = Capsule.construct(value)
		return cls(built)

	def data(self):
		data = {}
		for key, value in self._value.iteritems():
			data[key] = Capsule.wrap(value).serialized()
		return {
			'data': data,
		}

	def proxy_value(self, proxy):
		evaluated = self.handled()
		for key, value in self._value.iteritems():
			evaluated[key] = value.proxy_value(proxy)
		return evaluated
	
	def actual_value(self, actual):
		evaluated = self.handled()
		for key, value in self._value.iteritems():
			evaluated[key] = value.actual_value(actual)
		return evaluated

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
IntegerCapsule.register()
BooleanCapsule.register()
StringCapsule.register()
UnicodeCapsule.register()
ListCapsule.register()
TupleCapsule.register()
SetCapsule.register()
DictionaryCapsule.register()
NoneCapsule.register()
