from bge import types
from scripts import game

class Camera(types.KX_GameObject):
	
	def __init__(self, own):
		pass
		
	def update(self):
		pass
		
def init(cont):
	if not cont.sensors[0].positive:
		return
	game.camera	= game.utils.mutate(cont, Camera)
	
def update(cont):
	actu = cont.actuators[0]
	if game.target is not None and game.target is not actu.object:
		actu.object = game.target
		cont.activate(actu)
		print(actu.object)
	cont.owner.update()
	