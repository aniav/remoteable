class ConstructionError(Exception):
	pass


class UnknownSerialError(ConstructionError):
	pass


class Serializable(object):
	serial = None

	_registry = {} 
	# each immediate subclass should define its own registry

	@classmethod
	def register(cls):
		cls._registry[cls.serial] = cls

	@classmethod
	def build(cls, data):
		raise NotImplementedError(cls)

	def data(self):
		raise NotImplementedError(self)

	def serialized(self):
		return dict(self.data(), **{
			'serial': self.serial
		})

	@classmethod
	def construct(cls, data):
		if 'serial' not in data:
			raise UnknownSerialError(None)
		serial = data['serial']
		try:
			subclass = cls._registry[serial]
		except KeyError: 
			raise UnknownSerialError(data['serial'])
		return subclass.build(data)
