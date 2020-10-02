from bge import types
from math import pi
from scripts import game

class Tracker(types.KX_GameObject):
	
	def __init__(self, own):
		pass
		
	def update(self):
		
		if game.target is None:
			return
			
		eul = self.localOrientation.to_euler()
		eul.y = 0
		if eul.x < 0:
			eul.rotate_axis("Z", pi)
		self.localOrientation = eul
		vec = self.worldPosition - game.target.focus.worldPosition
		if vec.magnitude:
			vec.normalize()
			self.alignAxisToVect(vec, 2)
	
def init(cont):
	if not cont.sensors[0].positive:
		return
	game.tracker = game.utils.mutate(cont, Tracker)
	
def update(cont):
	cont.owner.update()
	