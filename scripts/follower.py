from bge import types
from mathutils import Vector, Euler, Matrix
from math import pi
from scripts import game

LERP_PROP_NAME  	 = "LERP"
MIN_PROP_NAME   	 = "MIN"
MAX_PROP_NAME   	 = "MAX"
HEIGHT_PROP_NAME	 = "HEIGHT"
ROT_SPEED_PROP_NAME  = "ROT_SPEED"
FADE_START_PROP_NAME = "FADE_START"
FADE_STOP_PROP_NAME  = "FADE_STOP"

TICK_RATE = 60
	
class Follower(types.KX_GameObject):
	
	def __init__(self, own):
		self.lerp = self[LERP_PROP_NAME]
		self.min = self[MIN_PROP_NAME]
		self.max = self[MAX_PROP_NAME]
		self.height = self[HEIGHT_PROP_NAME]
		self.rotation_speed = self[ROT_SPEED_PROP_NAME]
		self.rotation = Euler((0, 0, 0), "XYZ")
		self.__gravity_per_tick = self.scene.gravity / TICK_RATE
		self.__threshold = 0.01
		
		self.target = None
		self.target_radius = 0
		self.target_focus_height = 0
		self.just_hit = False
		
		# add input mappings for rotation
		
		game.input["f_rotate_right"] = {"k": ["m"], "g0": ["axis1-right"]}
		game.input["f_rotate_left"] = {"k": ["k"], "g0": ["axis1-left"]}
		game.input["f_rotate_up"] = {"k": ["l"], "g0": ["axis1-up"]}
		game.input["f_rotate_down"] = {"k": ["o"], "g0": ["axis1-down"]}
		
	def disable_rotation():
		pass
		
	def enable_rotation():
		pass
		
	def update(self):
		
		if game.target is None:
			return
			
		if self.target is not game.target:
			
			# update target information
		
			if self.target is not None:
				self.target.color.w = 1.0
				
			self.target = game.target
			self.target_radius = max(self.target.dimensions.x, self.target.dimensions.y) / 2
			self.min = self.target_radius + self[MIN_PROP_NAME]
			self.max = self.target_radius + self[MAX_PROP_NAME]
			
		# update position
		
		vec = self.target.focus.worldPosition
		
		dir_x = game.input.down("f_rotate_up") - game.input.down("f_rotate_down")
		dir_z = game.input.down("f_rotate_right") - game.input.down("f_rotate_left")
		if dir_x or dir_z:
			if dir_x:
				self.rotation.x += dir_x * self.rotation_speed
				self.rotation.x = min(max(self.rotation.x, -pi/8), pi/8)
			if dir_z:
				self.rotation.z += dir_z * self.rotation_speed
				
		ori = self.target.worldOrientation.copy()
		ori.rotate(self.rotation)
		off = Vector((0, -self.min, self.height))
		vec += ori * off
		
		dif = vec - self.worldPosition
		if dif.magnitude > self.max:
			dif.magnitude = self.max * (1 - self.lerp)
			vec -= dif
		else:
			vec = self.worldPosition.lerp(vec, self.lerp)
			
		foc_pos = self.target.focus.worldPosition
		hit_pos = self.rayCast(vec, foc_pos, 0, "", 0, 1, 0, 1)[1]
		if hit_pos:
			hit_dist = (hit_pos - foc_pos).length
			if hit_dist < self.target_radius * 2:
				hit_pos.z = foc_pos.z + self.__threshold
			vec = hit_pos
			self.height = self.__threshold
			self.just_hit = True
		elif self.just_hit:
			self.height = self[HEIGHT_PROP_NAME]
			self.just_hit = False
			
		self.worldPosition = vec
		
		# update target transparency
		
		fade_start = self[FADE_START_PROP_NAME]
		fade_stop = self[FADE_STOP_PROP_NAME]
		f = fade_stop - fade_start
		dist = (vec - foc_pos).length - f
		if dist < fade_stop:
			self.target.color.w = (dist - fade_stop + 1) / f - 1 if dist > fade_start else 0
		elif self.target.color.w < 1:
			self.target.color.w = 1
			
def init(cont):
	if not cont.sensors[0].positive:
		return
	game.follower = game.utils.mutate(cont, Follower)
	
def update(cont):
	cont.owner.update()
	