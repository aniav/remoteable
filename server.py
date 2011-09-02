
import json
import logging
import uuid

from command import Command

from threading import Thread

class RemoteHandler(Thread):
	def __init__(self, server, client_socket, client_address):
		Thread.__init__(self, name = 'RemoteHandler-%s:%s' % client_address)
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
				self._logger.debug("received: %s", data)
				command = Command.construct(data)
				response = command.execute(self._server)
				serialized = response.serialized()
				self._logger.debug("response: %s", serialized)
				self._socket.send(json.dumps(serialized))
		except Exception:
			self._logger.info("Stopping: Unhandled exception", exc_info = True)
			raise

	def stop(self):
		self._socket.close()

import socket

class RemotingServer(object):
	def __init__(self, server_address):
		self._logger = logging.getLogger("remoting.server.%s:%s" % server_address)
		self._exports = {}
		self._references = {}
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._socket.bind(server_address)
		self._socket.listen(1)
		self._handlers = []

	def export(self, obj, remote_name):
		assert '.' not in remote_name
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

	def start(self):
		self._logger.info("Starting")
		try:
			while True:
				connected_socket, connected_address = self._socket.accept()
				handler = RemoteHandler(self, connected_socket, connected_address)
				handler.start()
				self._handlers.append(handler)
		except Exception:
			self._logger.info("Stopping due to exception", exc_info = True)
			for handler in self._handlers:
				handler.stop()		
			raise
	
	def stop(self):
		return self._socket.close()
