from bge import types, logic
from scripts import game
import os

FOLLOWER = "Follower"
LIGHTING = "Lighting"

LOD_PROGRESS_PROP_NAME = "BGE_TOOLS_LOD_PROGRESS"

class Scene(types.KX_GameObject):
	
	NUM_LOADING_STEPS = 5
	
	STATE_LOAD = logic.KX_STATE2
	STATE_UPDATE = logic.KX_STATE3
	
	def __init__(self, own):
		self.loading_step = 0
		self.loading_step_finished = None
		
	def init(self):
		try:
			game.save_data = game.read_save_file(game.SAVE_FILE_NAME + game.TXT_EXT)
		except FileNotFoundError:
			game.save_data = game.SAVE_DATA_EMPTY
			game.write_save_file(game.save_data, game.SAVE_FILE_NAME + game.TXT_EXT)
			
		self.state = self.STATE_LOAD
		
	def load(self):
		
		def loading_step_next(status=None):
			if status is not None:
				game.loading_status = status
			self.loading_step = 0 if self.loading_step == self.NUM_LOADING_STEPS + 1 else self.loading_step + 1
			game.loading_progress = self.loading_step / self.NUM_LOADING_STEPS
			self.loading_step_finished = True
			print("Finished loading step", self.loading_step, "of", self.NUM_LOADING_STEPS)
			
		def load_players():
			self.loading_step_finished = False
			players_file_name, players_path = game.get_players_file_name_and_path()
			with open(players_path, "rb") as f:
				game.loading_status = logic.LibLoad(players_path, "Scene", f.read(), True, True, True, True)
				game.loading_status.onFinish = loading_step_next
				game.loaded_libs[players_file_name] = players_path
				
		def load_area():
			self.loading_step_finished = False
			area_file_name, area_path = game.get_area_file_name_and_path()
			game.loading_status = logic.LibLoad(area_path, "Scene", load_actions=False, verbose=True, load_scripts=True, async=True)
			game.loading_status.onFinish = loading_step_next
			game.loaded_libs[area_file_name] = area_path
			
		if self.loading_step_finished is None:
			load_players()
			
		elif self.loading_step_finished and self.loading_step == 1:
			load_area()
			
		elif self.loading_step == 2:
			
			if game.terrain is not None:
				terrain_loading_progress = game.terrain.loading_progress
				game.loading_progress = (terrain_loading_progress + self.loading_step) / self.NUM_LOADING_STEPS
				if terrain_loading_progress != 1.0:
					return
					
				game.portals.sort(key=lambda x: x.name)
				loading_step_next()
				
		elif self.loading_step == 3:
			player = self.scene.addObject(game.save_data[game.PLAYER])
			player.worldTransform = game.portals[0].worldTransform
			loading_step_next()
					
		elif self.loading_step == 4:
			#self.scene.addObject(FOLLOWER)
			self.scene.addObject(LIGHTING)
			loading_step_next()
			self.state = self.STATE_UPDATE
			
	def update(self):
		pass
		
def init(cont):
	game.scene = game.utils.mutate(cont, Scene)
	cont.owner.init()
	
def load(cont):
	cont.owner.load()
	
def update(cont):
	cont.owner.update()
	