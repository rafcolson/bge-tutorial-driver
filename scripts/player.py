from bge import types
from mathutils import Vector
from scripts import game

WALK_SPEED_PROP_NAME = "WALK_SPEED"
RUN_SPEED_PROP_NAME  = "RUN_SPEED"
JUMP_SPEED_PROP_NAME = "JUMP_SPEED"
TURN_SPEED_PROP_NAME = "TURN_SPEED"
LERP_PROP_NAME  	 = "LERP"
FOCUS_PROP_NAME 	 = "FOCUS"

class Player(types.KX_GameObject):
	
	# INPUT MAPPINGS
	
	def add_input_mappings(self):
		if self.has_input_mappings:
			return
			
		game.input["p_forward"] = {"k": ["uparrow", "z", "w"], "g0": ["axis0-up", "hat-up", "hat-up-right", "hat-up-left"]}
		game.input["p_backward"] = {"k": ["downarrow", "s"], "g0": ["axis0-down", "hat-down", "hat-down-right", "hat-down-left"]}
		game.input["p_turn_left"] = {"k": ["leftarrow", "a", "q"], "g0": ["axis0-left", "hat-left", "hat-up-left", "hat-down-left"]}
		game.input["p_turn_right"] = {"k": ["rightarrow", "d"], "g0": ["axis0-right", "hat-right", "hat-up-right", "hat-down-right"]}
		game.input["p_jump"] = {"k": ["space"], "g0": ["btn-0"]}
		game.input["p_run"] = {"k": ["leftctrl"], "g0": ["btn-4"]}
		self.has_input_mappings = True
	
	def remove_input_mappings(self):
		if not self.has_input_mappings:
			return
			
		for k in ("p_forward", "p_backward", "p_turn_left", "p_turn_right", "p_jump", "p_run"):
			del game.input[k]
		self.has_input_mappings = False
		
	def action_hit(self):
		return game.input.hit("p_action")
		
	# OVERRIDES
	
	def endObject(self):
		self.remove_input_mappings()
		del game.input["p_action"]
		super(Player, self).endObject()
		
	# INITIALIZATION
	
	def __init__(self, own):
		
		# get constants
		
		self.WALK_SPEED = self[WALK_SPEED_PROP_NAME]
		self.RUN_SPEED = self[RUN_SPEED_PROP_NAME]
		self.JUMP_SPEED = self[JUMP_SPEED_PROP_NAME]
		self.TURN_SPEED = self[TURN_SPEED_PROP_NAME]
		self.LERP = self[LERP_PROP_NAME]
		
		# get focus
		
		self.focus = game.utils.get_obj_by_property(self.children, FOCUS_PROP_NAME)
		
		# initialize variables
		
		self.median_point, self.dimensions = game.utils.get_median_point_and_dimensions(self)
		self.box_points = game.utils.get_box_points(self.dimensions, self.median_point)
		self.vel = Vector()
		self.rot = Vector()
		self.has_input_mappings = False
		
		# add input mapping for action
		
		game.input["p_action"] = {"k": ["i"], "g0": ["btn-5"]}
		
		# set initial state
		
		self.update = self.active
		
	# STATES
	
	def active(self):
		
		# get input
		
		ground = self.sensors["ground"]
		self.add_input_mappings()
		
		# get velocity and rotation
		
		if not ground.positive:
			self.vel.y = self.localLinearVelocity.y * self.LERP
		else:
			dir = game.input.down("p_forward") - game.input.down("p_backward")
			if dir:
				self.vel.y = dir * self.RUN_SPEED if game.input.down("p_run") else dir * self.WALK_SPEED
			else:
				self.vel.y = 0
			
		self.vel.z = game.input.down("p_jump") * ground.positive
		if self.vel.z:
			self.vel.z *= self.JUMP_SPEED
		else:
			self.vel.z = self.localLinearVelocity.z
			
		self.rot.z = (game.input.down("p_turn_left") - game.input.down("p_turn_right")) * self.TURN_SPEED
		
		# apply velocity and rotation
		
		self.localLinearVelocity = self.vel
		self.applyRotation(self.rot, True)
		
	def inactive(self):
		self.remove_input_mappings()
		
def init(cont):
	if not cont.sensors[0].positive:
		return
	game.target = game.player = game.utils.mutate(cont, Player)
	
def update(cont):
	cont.owner.update()
	