# pylint: disable=C0103,R0904,W0201

import unittest

import logging
logging.basicConfig(level = logging.DEBUG)

from remoteable.server import ThreadedRemotingServer
from remoteable.client import RemotingClient


class TestClass(object):
	def __init__(self, value):
		self.value = value

	def get_value(self):
		return self.value

	def method(self, arg):
		self.value += arg
		return self.value


import random

class Test(unittest.TestCase):
	def setUp(self):
		address = ('localhost', random.randint(2000, 20000))
		self.server = ThreadedRemotingServer(address)
		self.server.start()
		self.client = RemotingClient(address)

	def tearDown(self):
		if self.server.isAlive():
			self.server.stop()

	def test_attribute(self):
		base = 20
		remote_name = 'obj'
		local_object = TestClass(base)
		self.server.export(local_object, remote_name = remote_name)
		remote_object = self.client.fetch(remote_name)
		result = remote_object.value # Meat
		self.assertEqual(local_object.value, int(result))

	def test_set_attribute(self):
		base = 20
		modified = 30
		remote_name = 'obj'
		local_object = TestClass(base)
		self.server.export(local_object, remote_name = remote_name)
		remote_object = self.client.fetch(remote_name)
		remote_object.value = modified  # Meat
		remote_object_2 = self.client.fetch(remote_name)
		self.assertEqual(local_object.value, int(remote_object.value))
		self.assertEqual(int(remote_object_2.value), int(remote_object.value))

	def test_attribute_remote_handle(self):
		base = 20
		remote_name = 'obj'
		local_object = TestClass(base)
		attribute_name = self.client.store('value')
		self.server.export(local_object, remote_name = remote_name)
		remote_object = self.client.fetch(remote_name)
		result = remote_object.__getattr__(attribute_name)
			# getattr(remote_object, attribute_name) requires attribute_name to be string
		self.assertEqual(local_object.value, int(result))

	def test_method(self):
		base = 20
		addition = 30
		remote_name = 'obj'
		local_object = TestClass(base)
		self.server.export(local_object, remote_name = remote_name)
		remote_object = self.client.fetch(remote_name)
		result = remote_object.method(addition) # Meat
		self.assertEqual(local_object.get_value(), int(result))

	def test_method_remote_handle(self):
		base = 20
		addition = self.client.store(30)
		remote_name = 'obj'
		local_object = TestClass(base)
		self.server.export(local_object, remote_name = remote_name)
		remote_object = self.client.fetch(remote_name)
		result = remote_object.method(addition) # Meat
		self.assertEqual(local_object.get_value(), int(result))
		self.assertEqual(result, local_object.get_value())

	def test_equality(self):
		value = 20
		first = self.client.store(value)
		second = self.client.store(value)
		self.assertEqual(first, second)

	def test_evaluation(self):
		base = 20
		remote_name = 'obj'
		local_object = TestClass(base)
		self.server.export(local_object, remote_name = remote_name)
		remote_object = self.client.fetch(remote_name)
		result = remote_object.get_value() # Meat
		self.assertEqual(int(result), base)
		self.assertEqual(str(result), str(base))

	def test_store(self):
		base = 30
		remote_object = self.client.store(base)
		self.assertEqual(int(remote_object), base)

	def test_store_list(self):
		base = [30, 40]
		remote_object = self.client.store(base)
		self.assertEqual(list(remote_object), base)

	def test_store_dict(self):
		base = {"qwe": 30, "asd": 40}
		remote_object = self.client.store(base)
		self.assertEqual(dict(**remote_object), base)

	def test_releasing(self):
		base = 20
		remote_name = 'obj'
		local_object = TestClass(base)
		self.server.export(local_object, remote_name = remote_name)
		remote_object = self.client.fetch(remote_name)
		#del remote_object
		remote_object.__del__()
		self.assertRaises(KeyError, remote_object)
		# test if server is wiped

if __name__ == "__main__":
	unittest.main()
