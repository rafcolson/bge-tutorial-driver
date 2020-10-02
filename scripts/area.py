from bge import types, logic
from scripts import game

class Area(types.KX_GameObject):
	
	def __init__(self, own):
		self.dynamic_objects = []
		
	def init(self):
		self.state = logic.KX_STATE2
		
	def suspend(self):
		for ob in self.children:
			gpl = game.utils.get_group_parents(ob)
			if gpl is None:
				continue
			for gp in gpl:
				if gp.getPhysicsId():
					self.dynamic_objects.append(gp)
					gp.suspendDynamics()
		self.state = logic.KX_STATE3
		
	def restore(self):
		if game.terrain.loading_progress != 1.0:
			return
		for ob in self.dynamic_objects:
			ob.restoreDynamics()
		self.state = logic.KX_STATE4
		
	def update(self):
		pass
		
def init(cont):
	if not cont.sensors[0].positive:
		return
	game.area = game.utils.mutate(cont, Area)
	cont.owner.init()
	
def suspend(cont):
	if not cont.sensors[0].positive:
		return
	cont.owner.suspend()
	
def restore(cont):
	cont.owner.restore()
	
def update(cont):
	cont.owner.update()
	