============
 remoteable
============

This library provides remoting in python-friendly way. It allows user to create a server, which holds and manages objects, and a client, which can remotely act upon these objects.

**Warning** this is still work-in-progress, but no API changes are foreseen.

How to use it?
--------------

Consider following simple tree-building class::

	class Node(object):
		def __init__(self, value, parent = None):
			self.value = value
			self.parent = parent
			self._children = []
		
		def child(self, index):
			return self._children[index]
		
		def add_child(self, node):
			if node.parent is not None:
				node.parent.remove_child(node)
			node.parent = self
			self._children.append(node)
		
		def remove_node(self, node):
			self._children.remove(node)

First, we need to setup a *server*, a remoting provider, where all the objects will exist::

	from remoteable.server import RemotingServer
	server = RemotingServer(('localhost', 3000))
	
Server will immediately bind and listen on specified host/port pair, but it won't accept connections. It needs to be started::

	server.run()
	
This call will block. Other threads can stop the server by calling ``server.stop``. If you want a background server, use ThreadedRemotingServer, which inherits Thread.

Let us create some class instances::

	root = Node(1)
	child = Node(2)
	root.add_child(child)

We can export those instances with ``server.export``. Remote name is arbitrary, this is a string that clients will send to gain access to exported object::

	server.export(root, remote_name = 'root')
	server.export(child, remote_name = 'child')
	
Any kind of object can be exported::

	server.export(Node, remote_name = 'Node')
	server.export(5, remote_name = 'five')

Next step to use these objects is to setup client::

	from remoteable.client import RemotingClient
	client = RemotingClient(('localhost', 3000))

Client will immediately connect and will be ready to fetch handles::

	>>> client_root = client.fetch('root')
	>>> client_root
	<RemoteHandle (d0d7177e-22f6-4476-9ed9-cec060fc7c79)> # may vary

Fetched handle is a simple, pythonic object which delegates all operations to a remote instance. There is a lot of implemented operations which can be simply done like:

- dereferencing an attribute
	>>> client_value = client_root.value
	>>> client_value
	<RemoteHandle (bd8c80ab-b183-401a-b7c2-9e3ee5c82d9a)> # may vary

- casting to simple types
	>>> int(client_value)
	1
	>>> str(client_value)
	'1'

- setting attribute
	>>> client_root.value = 4
	>>> int(client_root.value)
	4

- calling function (method)
	>>> child = client_root.child(0)
	>>> child
	<RemoteHandle (3ba4ba04-a6ec-41d7-818d-60d8a5388c74)> # may vary
	>>> int(child.value)
	2
	
- basic two argument operations
	>>> int(child.value + 4)
	6

- comparation
	>>> result = (child == client_root.child(0))
	>>> result
	<RemoteHandle (2a33e675-a18e-4acb-b360-dcad69858638)>
	>>> bool(result)
	True

...and more.

Client can also store values on server::

	>>> reference = client.store(5)
	>>> reference
	<RemoteHandle (ded685b6-3d3f-4fd9-96be-7d72b09a9a22)>
	>>> int(reference)
	5

Handles can be provided as an argument for operations with other handles::

	>>> client_root.value = reference
	>>> int(client_root.value)
	5



