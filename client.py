
from remoteable.capsule import Capsule
from remoteable.command import FetchCommand, StoreCommand

import socket
import logging
import json

from remoteable.command import ExecuteCommand, GetAttributeCommand, SetAttributeCommand, GetItemCommand, SetItemCommand, OperatorCommand, EvaluateCommand, ReleaseCommand 


class RemoteHandle(object):
	__slots__ = ('_proxy', '_id')

	def __init__(self, proxy, id):
		self._proxy = proxy
		self._id = id

	def __iter__(self):
		command = EvaluateCommand(self._id, 'list')
		response = command.push(self._proxy)
		return iter(response.interpret(self._proxy))

	def __int__(self):
		command = EvaluateCommand(self._id, 'int')
		response = command.push(self._proxy)
		return int(response.interpret(self._proxy))

	def __bool__(self):
		command = EvaluateCommand(self._id, 'bool')
		response = command.push(self._proxy)
		return bool(response.interpret(self._proxy))

	__nonzero__ = __bool__	

	def __str__(self):
		command = EvaluateCommand(self._id, 'str')
		response = command.push(self._proxy)
		return str(response.interpret(self._proxy))

	def __unicode__(self):
		command = EvaluateCommand(self._id, 'unicode')
		response = command.push(self._proxy)
		return str(response.interpret(self._proxy))

	def __eq__(self, other):
		command = OperatorCommand(self._id, Capsule.wrap(other), 'equals')
		response = command.push(self._proxy)
		return response.interpret(self._proxy)

	def __add__(self, other):
		command = OperatorCommand(self._id, Capsule.wrap(other), 'addition')
		response = command.push(self._proxy)
		return response.interpret(self._proxy)

	def __call__(self, *args, **kwargs):
		command = ExecuteCommand(self._id, Capsule.wrap(args),
								 Capsule.wrap(kwargs))
		response = command.push(self._proxy)
		return response.interpret(self._proxy)

	def __getitem__(self, key):
		command = GetItemCommand(self._id, Capsule.wrap(key))
		response = command.push(self._proxy)
		return response.interpret(self._proxy)

	def __setitem__(self, key, value):
		command = SetItemCommand(self._id, Capsule.wrap(key),
								 Capsule.wrap(value))
		response = command.push(self._proxy)
		return response.interpret(self._proxy)

	def __getattr__(self, name):
		command = GetAttributeCommand(self._id, Capsule.wrap(name))
		response = command.push(self._proxy)
		return response.interpret(self._proxy)

	def __setattr__(self, name, value):
		if name in ['_id', '_proxy']:
			return object.__setattr__(self, name, value)
		command = SetAttributeCommand(self._id, Capsule.wrap(name),
									  Capsule.wrap(value))
		response = command.push(self._proxy)
		return response.interpret(self._proxy)

	def __del__(self):
		command = ReleaseCommand(self._id)
		response = command.push(self._proxy)
		return response.interpret(self._proxy)

	def __repr__(self):
		return "<RemoteHandle (%s)>" % (self._id,)


class RemotingProxy(object):
	def fetch(self, name):
		command = FetchCommand(name)
		response = command.push(self)
		return response.interpret(self)

	def store(self, obj):
		command = StoreCommand(Capsule.wrap(obj))
		response = command.push(self)
		return response.interpret(self)

	def handle(self, id):
		return RemoteHandle(self, id)

	def request(self, data):
		self.send(data)
		result = self.receive()
		return result

	def send(self, data):
		raise NotImplementedError(self)

	def receive(self):
		raise NotImplementedError(self)

	def __repr__(self):
		return "<%s>" % (self.__class__.__name__)


class RemotingClient(RemotingProxy):
	def __init__(self, server_address):
		RemotingProxy.__init__(self)
		self._logger = logging.getLogger('client.%s:%s' % server_address)
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._socket.connect(server_address)

	def send(self, data):
		self._logger.debug("sending %s", data)
		self._socket.send(json.dumps(data))

	def receive(self):
		result = json.loads(self._socket.recv(65535))
		self._logger.debug("received %s", result)
		return result

	def __repr__(self):
		return "<%s socket(%s)>" % (self.__class__.__name__, self._socket)
