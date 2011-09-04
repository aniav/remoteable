import uuid

from remoteable.response import Response
from remoteable.serializable import Serializable

class Command(Serializable):
	_registry = {}

	def execute(self, actual):
		raise NotImplementedError(self)

	def push(self, proxy):
		result = proxy.request(self.serialized())
		return Response.construct(result)

from remoteable.response import AccessErrorResponse, HandleResponse

class FetchCommand(Command):
	serial = 'fetch'

	def __init__(self, name):
		Command.__init__(self)
		self._name = name

	@classmethod
	def build(cls, data):
		return cls(data['name'])

	def data(self):
		return {'name': self._name}
	
	def execute(self, actual):
		try:
			id = actual.fetch(self._name)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		return HandleResponse(id)

from remoteable.capsule import Capsule

class StoreCommand(Command):
	serial = 'store'

	def __init__(self, obj):
		Command.__init__(self)
		self._obj = obj

	@classmethod
	def build(cls, data):
		return cls(Capsule.construct(data['data']))

	def data(self):
		return {'data': self._obj.serialized()}
	
	def execute(self, actual):
		try:
			id = actual.store(self._obj.actual_value(actual))
		except KeyError, ex:
			return AccessErrorResponse(ex)
		return HandleResponse(id)

from remoteable.response import AttributeErrorResponse

class GetAttributeCommand(Command):
	serial = 'get'

	def __init__(self, id, name):
		Command.__init__(self)
		self._id = id
		self._name = name

	def data(self):
		return {
			'id': self._id.hex,
			'name': self._name.serialized(),
		}

	@classmethod
	def build(cls, data):
		return cls(uuid.UUID(hex = data['id']), Capsule.construct(data['name']))

	def execute(self, actual):
		try:
			obj = actual.access(self._id)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		try:
			resolved_name = self._name.actual_value(actual)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		try:
			result = getattr(obj, resolved_name)
		except AttributeError, ex:
			return AttributeErrorResponse(ex)
		id = actual.store(result)
		return HandleResponse(id)

class SetAttributeCommand(Command):
	serial = 'set'

	def __init__(self, id, name, value):
		Command.__init__(self)
		self._id = id
		self._name = name
		self._value = value

	def data(self):
		return {
			'id': self._id.hex,
			'name': self._name.serialized(),
			'value': self._value.serialized(),
		}

	@classmethod
	def build(cls, data):
		return cls(uuid.UUID(hex = data['id']), Capsule.construct(data['name']), Capsule.construct(data['value']))

	def execute(self, actual):
		try:
			obj = actual.access(self._id)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		try:
			resolved_name = self._name.actual_value(actual)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		try:
			resolved_value = self._value.actual_value(actual)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		try:
			setattr(obj, resolved_name, resolved_value)
		except AttributeError, ex:
			return AttributeErrorResponse(ex)
		return EmptyResponse()

from remoteable.response import OperationErrorResponse

class OperatorCommand(Command):
	serial = 'operator'

	operators = {
		'equals': lambda this, other: this == other,
		'addition': lambda this, other: this + other,
	}

	def __init__(self, id, other, variant):
		Command.__init__(self)
		self._id = id
		self._other = other
		self._variant = variant

	def data(self):
		return {
			'id': self._id.hex,
			'other': self._other.serialized(),
			'variant': self._variant,
		}

	@classmethod
	def build(cls, data):
		return cls(uuid.UUID(hex = data['id']), Capsule.construct(data['other']), data['variant'])

	def execute(self, actual):
		try:
			obj = actual.access(self._id)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		try:
			resolved_other = self._other.actual_value(actual)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		try:
			operator = self.operators[self._variant]
		except KeyError, ex:
			return OperationErrorResponse(ex)
		try:
			result = operator(obj, resolved_other)
		#pylint: disable=W0703
		# all exception should be caught and returned to client
		except Exception as ex:
			return ExecutionErrorResponse(ex)
		id = actual.store(result)
		return HandleResponse(id)

from remoteable.response import ExecutionErrorResponse

class ExecuteCommand(Command):
	serial = 'execute'

	def __init__(self, id, args, kwargs):
		Command.__init__(self)
		self._id = id
		self._args = args
		self._kwargs = kwargs

	def data(self):
		prepared_args = [arg.serialized() for arg in self._args]
		prepared_kwargs = {}
		for key, value in self._kwargs.iteritems():
			prepared_kwargs[key] = value.serialized()
		return {
			'id': self._id.hex,
			'args': prepared_args,
			'kwargs': prepared_kwargs,
		}

	@classmethod
	def build(cls, data):
		wrapped_args = [Capsule.construct(arg) for arg in data['args']]
		wrapped_kwargs = {}
		for key, value in data['kwargs']:
			wrapped_kwargs[key] = Capsule.construct(value)
		return cls(uuid.UUID(hex = data['id']), wrapped_args, wrapped_kwargs)

	def execute(self, actual):
		try:
			obj = actual.access(self._id)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		unwrapped_args = [arg.actual_value(actual) for arg in self._args]
		unwrapped_kwargs = {}
		for key, value in self._kwargs:
			unwrapped_kwargs[key] = value.actual_value(actual)
		try:
			result = obj(*unwrapped_args, **unwrapped_kwargs)
		#pylint: disable=W0703
		# all exception should be caught and returned to client
		except Exception as ex:
			return ExecutionErrorResponse(ex)
		id = actual.store(result)
		return HandleResponse(id)

from remoteable.response import EvaluationResponse

class EvaluateCommand(Command):
	serial = 'evaluate'

	def __init__(self, id, variant):
		Command.__init__(self)
		self._id = id
		self._variant = variant

	def data(self):
		return {
			'id': self._id.hex,
			'variant': self._variant
		}

	@classmethod
	def build(cls, data):
		return cls(uuid.UUID(hex = data['id']), data['variant'])

	def execute(self, actual):
		try:
			obj = actual.access(self._id)
		except KeyError as ex:
			return AccessErrorResponse(ex)
		return EvaluationResponse(Capsule.wrap(obj), self._variant)

from remoteable.response import EmptyResponse

class ReleaseCommand(Command):
	serial = 'release'

	def __init__(self, id):
		Command.__init__(self)
		self._id = id

	def data(self):
		return {
			'id': self._id.hex,
		}

	@classmethod
	def build(cls, data):
		return cls(uuid.UUID(hex = data['id']))

	def execute(self, actual):
		try:
			actual.release(self._id)
		except KeyError as ex:
			return AccessErrorResponse(ex)
		return EmptyResponse()

FetchCommand.register()
StoreCommand.register()
GetAttributeCommand.register()
SetAttributeCommand.register()
OperatorCommand.register()
ExecuteCommand.register()
EvaluateCommand.register()
ReleaseCommand.register()
