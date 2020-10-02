from bge import types, logic
from scripts import game

class Lighting(types.KX_GameObject):
	
	def __init__(self, own):
		pass
		
	def update(self):
		if game.target is None:
			return
		vec = game.target.worldPosition.xyz
		vec.x = (4 * (vec.x + 0.5)) // 4
		vec.y = (4 * (vec.y + 0.5)) // 4
		vec.z = (4 * (vec.z + 0.5)) // 4
		self.worldPosition = vec
		
def init(cont):
	if not cont.sensors[0].positive:
		return
	game.lighting = game.utils.mutate(cont, Lighting)

def update(cont):
	cont.owner.update()
	