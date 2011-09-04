
import json
import logging
import uuid

from remoteable.command import Command


class RemotingActual(object):
	def process(self, data):
		self._logger.debug("received: %s", data)
		command = Command.construct(data)
		response = command.execute(self)
		serialized = response.serialized()
		self._logger.debug("response: %s", serialized)
		return serialized

	def export(self, obj, remote_name):
		self._exports[remote_name] = obj

	def fetch(self, name):
		if name not in self._exports:
			raise KeyError(name)
		return self.store(self._exports[name])

	def store(self, value):
		id = uuid.uuid4()
		self._references[id] = value
		return id

	def access(self, id):
		return self._references[id]
	
	def release(self, id):
		del self._references[id]
		
from threading import Thread

class RemoteHandler(Thread):
	def __init__(self, server, client_socket, client_address):
		Thread.__init__(self)
		self._logger = logging.getLogger("remoting.handler.%s:%s" % client_address)
		self._server = server
		self._socket = client_socket
		self._logger.info("Starting")

	def run(self):
		try:
			while True:
				try:
					data = json.loads(self._socket.recv(65535))
				except ValueError:
					self._logger.info("Stopping: Invalid JSON received")
					break
				result = self._server.process(data)
				self._socket.send(json.dumps(result))
		except Exception:
			self._logger.info("Stopping: Unhandled exception", exc_info = True)
			self.stop()
			raise

	def stop(self):
		self._socket.close()

import socket

class RemotingServer(RemotingActual):
	def __init__(self, server_address):
		self._logger = logging.getLogger("remoting.server.%s:%s" % server_address)
		self._exports = {}
		self._references = {}
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._socket.bind(server_address)
		self._socket.listen(1)
		self._handlers = []

	def run(self):
		self._logger.info("Starting")
		try:
			while True:
				connected_socket, connected_address = self._socket.accept()
				handler = RemoteHandler(self, connected_socket, connected_address)
				handler.start()
				self._handlers.append(handler)
		except Exception:
			self._logger.info("Stopping: Unhandled exception", exc_info = True)
			self.stop()
			raise
	
	def stop(self):
		for handler in self._handlers:
			handler.stop()		
		return self._socket.close()

class ThreadedRemotingServer(RemotingServer, Thread):
	def __init__(self, server_address):
		Thread.__init__(self, name = 'RemotingServer')
		RemotingServer.__init__(self, server_address)
