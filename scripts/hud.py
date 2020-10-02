from bge import types, logic
from scripts import game

BAR_PROP_NAME = "BAR"

class Hud(types.KX_GameObject):
	
	STATE_RESET = logic.KX_STATE2
	STATE_UPDATE = logic.KX_STATE3
	STATE_LOAD = logic.KX_STATE4
	
	def __init__(self, own):
		self.bar = game.utils.get_obj_by_property(self.children, BAR_PROP_NAME)
		
	def init(self):
		self.reset()
		
	def reset(self):
		self.visible = False
		self.bar.visible = False
		self.bar.localScale.x = 0.0
		game.loading_status = None
		game.loading_progress = None
		self.state = self.STATE_UPDATE
		
	def load(self):
		self.bar.localScale.x = game.loading_progress
		if game.loading_progress == 1.0:
			self.state = self.STATE_RESET
			
	def update(self):
		if game.loading_progress is None:
			return
		self.visible = True
		self.bar.visible = True
		self.state = self.STATE_LOAD
		
def init(cont):
	if not cont.sensors[0].positive:
		return
	game.hud = game.utils.mutate(cont, Hud)
	cont.owner.init()
	
def reset(cont):
	if not cont.sensors[0].positive:
		return
	cont.owner.reset()
	
def load(cont):
	cont.owner.load()
		
def update(cont):
	cont.owner.update()
	
