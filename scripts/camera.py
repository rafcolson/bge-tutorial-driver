from bge import types
from scripts import game

class Camera(types.KX_Camera):
	
	def __init__(self, own):
		pass
		
	def update(self):
		pass
		
def init(cont):
	if not cont.sensors[0].positive:
		return
	cont.owner.scene.active_camera = game.camera = game.utils.mutate(cont, Camera)
	
def update(cont):
	cont.owner.update()
	