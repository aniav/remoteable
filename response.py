import uuid
import importlib

from remoteable.capsule import Capsule
from remoteable.serializable import Serializable

class Response(Serializable):
	_registry = {}

	def interpret(self, proxy):
		raise NotImplementedError(self)

class HandleResponse(Response):
	serial = 'handle'
	
	def __init__(self, id):
		Response.__init__(self)
		self._id = id
	
	@classmethod
	def build(cls, data):
		return cls(uuid.UUID(hex = data['id']))

	def data(self):
		return {'id': self._id.hex}

	def interpret(self, proxy):
		return proxy.handle(self._id)



class EvaluationResponse(Response):
	serial = 'evaluation'

	def __init__(self, value, variant):
		Response.__init__(self)
		self._value = value
		self._variant = variant
	
	@classmethod
	def build(cls, data):
		variant = data['variant']
		value = Capsule.construct(data['data'])
		return cls(value, variant)

	def data(self):
		return {
			'data': self._value.serialized(),
			'variant': self._variant 
		}

	def interpret(self, proxy):
		return self._value.proxy_value(proxy)

class EmptyResponse(Response):
	serial = 'empty'

	@classmethod
	def build(cls, _data):
		# pylint: disable=R0801
		# same as remoteable.response.EmptyResponse, but these are not related
		return cls()

	def data(self):
		return {}

	def interpret(self, _proxy):
		return None

class ErrorResponse(Response):
	serial = 'error'
	
	def __init__(self, exception):
		Response.__init__(self)
		self._exception = exception
	
	@classmethod
	def build(cls, data):
		package_name, exception_class_name = data['class'].rsplit('.', 1) 
		package = importlib.import_module(package_name)
		exception_class = getattr(package, exception_class_name)
		return cls(exception_class(data['text']))

	def data(self):
		return {
			'class': self._exception.__class__.__module__ + '.' + self._exception.__class__.__name__,
			'text': str(self._exception),
		}

	def interpret(self, _proxy):
		raise self._exception

class OperationErrorResponse(ErrorResponse):
	serial = 'error-operation'

class AccessErrorResponse(ErrorResponse):
	serial = 'error-access'

class AttributeErrorResponse(ErrorResponse):
	serial = 'error-attribute'

class ExecutionErrorResponse(ErrorResponse):
	serial = 'error-execution'

HandleResponse.register()
EvaluationResponse.register()
EmptyResponse.register()
ErrorResponse.register()
OperationErrorResponse.register()
AccessErrorResponse.register()
AttributeErrorResponse.register()
ExecutionErrorResponse.register()
