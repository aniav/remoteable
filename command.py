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

from remoteable.response import ErrorResponse # TODO

class GetCommand(Command):
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
	def getter(cls, obj, name):
		raise NotImplementedError(cls)

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
			result = self.getter(obj, resolved_name)
		except Exception, ex: # TODO
			return ErrorResponse(ex)
		id = actual.store(result)
		return HandleResponse(id)


class GetAttributeCommand(GetCommand):
	serial = 'attribute-get'

	@classmethod
	def getter(cls, obj, name):
		return getattr(obj, name)

class GetItemCommand(GetCommand):
	serial = 'item-get'

	@classmethod
	def getter(cls, obj, name):
		return obj.__getitem__(name)

class SetCommand(Command):
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
	def setter(cls, obj, name, value):
		raise NotImplementedError(cls)

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
			self.setter(obj, resolved_name, resolved_value)
		except Exception, ex: # TODO
			return ErrorResponse(ex)
		return EmptyResponse()

class SetAttributeCommand(SetCommand):
	serial = 'attribute-set'

	@classmethod
	def setter(cls, obj, name, value):
		setattr(obj, name, value)

class SetItemCommand(SetCommand):
	serial = 'item-set'

	@classmethod
	def setter(cls, obj, name, value):
		obj.__setitem__(name, value)

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
		return {
			'id': self._id.hex,
			'args': self._args.serialized(),
			'kwargs': self._kwargs.serialized(),
		}

	@classmethod
	def build(cls, data):
		wrapped_args = Capsule.construct(data['args'])
		wrapped_kwargs = Capsule.construct(data['kwargs'])
		return cls(uuid.UUID(hex = data['id']), wrapped_args, wrapped_kwargs)

	def execute(self, actual):
		try:
			obj = actual.access(self._id)
		except KeyError, ex:
			return AccessErrorResponse(ex)
		unwrapped_args = self._args.actual_value(actual)
		unwrapped_kwargs = self._kwargs.actual_value(actual)
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
GetItemCommand.register()
SetItemCommand.register()
OperatorCommand.register()
ExecuteCommand.register()
EvaluateCommand.register()
ReleaseCommand.register()
