from bge import types, logic, constraints
from collections import OrderedDict
from mathutils import Matrix, Vector
from scripts.player import Player
from scripts import game
from math import pi

#constraints.setDebugMode(constraints.DBG_DRAWWIREFRAME)
constraints.setContactBreakingTreshold(0.005)

# SET FINAL CONSTANTS

BRAND_PROP_NAME 			= "BRAND"
STEERING_WHEEL_PROP_NAME	= "STEERING_WHEEL"
COLLISION_WHEEL_PROP_NAME   = "COLLISION_WHEEL"
WHEEL_PROP_NAME 			= "WHEEL"
VISUAL_PROP_NAME			= "VISUAL"
DRIVER_SEAT_PROP_NAME   	= "DRIVER_SEAT"
DOOR_SENSOR_PROP_NAME   	= "DOOR_SENSOR"
FOCUS_PROP_NAME 			= "FOCUS"

WHEELS_DOWN_DIR 			= (0.0, 0.0, -1.0)
WHEELS_AXLE_DIR 			= (-1.0, 0.0, 0.0)
WHEELS_HAS_STEERING 		= (True, True, False, False)

FRONT_WHEEL_DRIVE   		= 0
REAR_WHEEL_DRIVE			= 1
FOUR_WHEEL_DRIVE			= 2

VELOCITY_MIN				= 0.5
RAY_OFFSET  				= 0.5
SETTLE_TIME 				= 120

# DEFINE BRANDS

BRANDS = {
	"DEFAULT": {
		"WHEELS_SUSP_REST_LEN_F":   0.05,
		"WHEELS_SUSP_REST_LEN_R":   0.05,
		"FRICTION_VAL": 			1.0,
		"DAMPING_VAL":  			5.0,
		"COMPRESSION_VAL":  		5.0,
		"STIFFNESS_VAL":			50.0,
		"ROLL_VAL": 				0.5,
		"BRAKE_VAL":				10.0,
		"HAND_BRAKE_VAL":   		500.0,
		"FORWARD_VAL":  			500.0,
		"BACKWARD_VAL": 			250.0,
		"WHEEL_TURN_VAL":   		0.1,
		"WHEEL_TURN_FAC_MAX":   	0.25,
		"STEERING_WHEEL_TURN_FAC":  2.0,
		"LINEAR_VELOCITY_MAX":  	18.0,
		"WHEEL_DRIVE_MODE": 		0,
		"BODY_COLOR":   			(0.4, 0.0, 0.01, 1.0)
	},
	"HOTROD": {
		"WHEELS_SUSP_REST_LEN_F":   0.25,
		"WHEELS_SUSP_REST_LEN_R":   0.25,
		"FRICTION_VAL": 			1.0,
		"DAMPING_VAL":  			2.5,
		"COMPRESSION_VAL":  		2.5,
		"STIFFNESS_VAL":			10.0,
		"ROLL_VAL": 				0.75,
		"BRAKE_VAL":				15.0,
		"HAND_BRAKE_VAL":   		750.0,
		"FORWARD_VAL":  			750.0,
		"BACKWARD_VAL": 			375.0,
		"WHEEL_TURN_VAL":   		0.1,
		"WHEEL_TURN_FAC_MAX":   	0.25,
		"STEERING_WHEEL_TURN_FAC":  1.0,
		"LINEAR_VELOCITY_MAX":  	20.0,
		"WHEEL_DRIVE_MODE": 		1,
		"BODY_COLOR":   			(0.5, 0.5, 1.0, 1.0)
	},
	"ROCKET": {
		"WHEELS_SUSP_REST_LEN_F":   0.1,
		"WHEELS_SUSP_REST_LEN_R":   0.1,
		"FRICTION_VAL": 			1.0,
		"DAMPING_VAL":  			3.5,
		"COMPRESSION_VAL":  		3.5,
		"STIFFNESS_VAL":			35.0,
		"ROLL_VAL": 				0.75,
		"BRAKE_VAL":				15.0,
		"HAND_BRAKE_VAL":   		1250.0,
		"FORWARD_VAL":  			1250.0,
		"BACKWARD_VAL": 			500.0,
		"WHEEL_TURN_VAL":   		0.1,
		"WHEEL_TURN_FAC_MAX":   	0.25,
		"STEERING_WHEEL_TURN_FAC":  1.0,
		"LINEAR_VELOCITY_MAX":  	50.0,
		"WHEEL_DRIVE_MODE": 		1,
		"BODY_COLOR":   			(1.0, 1.0, 0.5, 1.0)
	}
}

class Car(types.KX_GameObject):
	
	# INPUT MAPPINGS
	
	def add_input_mappings(self):
		game.input["c_forward"] = {"k": ["uparrow", "z", "w"], "g0": ["btn-0"]}
		game.input["c_backward"] = {"k": ["downarrow", "s"], "g0": ["btn-3"]}
		game.input["c_turn_left"] = {"k": ["leftarrow", "a", "q"], "g0": ["axis0-left", "hat-left", "hat-up-left", "hat-down-left"]}
		game.input["c_turn_right"] = {"k": ["rightarrow", "d"], "g0": ["axis0-right", "hat-right", "hat-up-right", "hat-down-right"]}
		game.input["c_brake"] = {"k": ["space"], "g0": ["btn-2"]}
		game.input["c_handbrake"] = {"k": ["leftctrl", "rightctrl"], "g0": ["btn-1"]}
		
	def remove_input_mappings(self):
		for k in ("c_forward", "c_backward", "c_turn_left", "c_turn_right", "c_brake", "c_handbrake"):
			del game.input[k]
	
	# OVERRIDES
	
	def endObject(self):
		self.remove_driver()
		self.remove_constraint()
		super(Car, self).endObject()
		
	def suspendDynamics(self, *args):
		if self.isSuspendDynamics:
			return
		self.timer = 0
		self.worldLinearVelocity.zero()
		self.worldAngularVelocity.zero()
		self.collisionCallbacks.clear()
		self.remove_constraint()
		super(Car, self).suspendDynamics(*args)
		self.add_collision_wheels()
		self.update = self.idle
		
	def restoreDynamics(self):
		if not self.isSuspendDynamics:
			return
		
		self.timer = 0
		self.remove_collision_wheels()
		super(Car, self).restoreDynamics()
		self.add_constraint()
		if self.driver is None:
			self.collisionCallbacks.append(self.body_sensor_cb)
			self.update = self.settle
			
	# INITIALIZATION
	
	def __init__(self, own):
		
		# get constants from brand
		
		brand_prop_ob = self if self.groupObject is None else self.groupObject
		brand = BRANDS[brand_prop_ob[BRAND_PROP_NAME] if BRAND_PROP_NAME in brand_prop_ob else list(BRANDS.keys())[0]]
		
		self.WHEELS_SUSP_REST_LEN = [brand["WHEELS_SUSP_REST_LEN_F"]] * 2 + [brand["WHEELS_SUSP_REST_LEN_R"]] * 2
		self.FRICTION_VAL = brand["FRICTION_VAL"]
		self.DAMPING_VAL = brand["DAMPING_VAL"]
		self.COMPRESSION_VAL = brand["COMPRESSION_VAL"]
		self.STIFFNESS_VAL = brand["STIFFNESS_VAL"]
		self.ROLL_VAL = brand["ROLL_VAL"]
		self.BRAKE_VAL = brand["BRAKE_VAL"]
		self.HAND_BRAKE_VAL = brand["HAND_BRAKE_VAL"]
		self.FORWARD_VAL = brand["FORWARD_VAL"]
		self.BACKWARD_VAL = brand["BACKWARD_VAL"]
		self.WHEEL_TURN_VAL = brand["WHEEL_TURN_VAL"]
		self.WHEEL_TURN_FAC_MAX = brand["WHEEL_TURN_FAC_MAX"]
		self.STEERING_WHEEL_TURN_FAC = brand["STEERING_WHEEL_TURN_FAC"]
		self.LINEAR_VELOCITY_MAX = brand["LINEAR_VELOCITY_MAX"]
		self.WHEEL_DRIVE_MODE = brand["WHEEL_DRIVE_MODE"]
		self.BODY_COLOR = brand["BODY_COLOR"]
		
		# get and store wheels, collision wheel name, steering wheel and target
		
		wheels = {}
		for obj in (self.children if self.groupObject is None else self.groupObject.groupMembers):
			if STEERING_WHEEL_PROP_NAME in obj:
				self.steering_wheel = obj
			elif COLLISION_WHEEL_PROP_NAME in obj:
				self.col_wheel_name = obj.name
				obj.endObject() # optional
			elif WHEEL_PROP_NAME in obj:
				wheels[obj] = None
			elif VISUAL_PROP_NAME in obj:
				self.visual = obj
				
		for i, wheel in enumerate(wheels):
			wheel.worldPosition.z -= self.WHEELS_SUSP_REST_LEN[i]
			wheels[wheel] = wheel.localPosition.xyz
			
		self.wheels = OrderedDict(sorted(wheels.items(), key=lambda item: item[0][WHEEL_PROP_NAME]))
		
		# get and store driver seat and door sensor
		
		self.driver_seat = game.utils.get_obj_by_property(self.children, DRIVER_SEAT_PROP_NAME)
		self.door_sensor = game.utils.get_obj_by_property(self.children, DOOR_SENSOR_PROP_NAME)
		
		# get focus
		
		self.focus = game.utils.get_obj_by_property(self.children, FOCUS_PROP_NAME)
		
		# initialize variables
		
		self.median_point, self.dimensions = game.utils.get_median_point_and_dimensions(self)
		self.box_points = game.utils.get_box_points(self.dimensions, self.median_point)
		self.constraint = None
		self.driver = None
		self.steering_val = 0
		self.timer = 0
		
		# apply body color
		
		self.visual.color = self.BODY_COLOR
		
		# set max linear velocity
		
		self.linVelocityMax = self.LINEAR_VELOCITY_MAX
		
		# add collision callbacks
		
		self.door_sensor.collisionCallbacks.append(self.door_sensor_cb)
		self.collisionCallbacks.append(self.body_sensor_cb)
		
		# add constraint
		
		self.add_constraint()
		
		# set initial state
		
		self.update = self.settle
		
		# set logic state
		
		self.state = logic.KX_STATE2
		
	# CONSTRAINT
		
	def add_constraint(self):
		
		if self.constraint is not None:
			return
			
		# create and store vehicle constraint
		
		constraint = constraints.createConstraint(self.getPhysicsId(), 0, constraints.VEHICLE_CONSTRAINT)
		self.constraint = constraints.getVehicleConstraint(constraint.getConstraintId())
		
		# move wheels to vehicle constraint and set values (and remove collision objects)
		
		for i, wheel in enumerate(self.wheels):
			wheel.removeParent()
			
			susp_rest_len = self.WHEELS_SUSP_REST_LEN[i]
			attach_pos = self.wheels[wheel].xyz
			attach_pos.z += susp_rest_len
			down_dir = WHEELS_DOWN_DIR
			axle_dir = WHEELS_AXLE_DIR
			wheel_dim = game.utils.get_median_point_and_dimensions(wheel)[1]
			radius = (wheel_dim.z * wheel.localScale.z) * 0.5
			has_steering = WHEELS_HAS_STEERING[i]
			
			self.constraint.addWheel(wheel, attach_pos, down_dir, axle_dir, susp_rest_len, radius, has_steering)
			
			self.constraint.setTyreFriction(self.FRICTION_VAL, i)
			self.constraint.setSuspensionDamping(self.DAMPING_VAL, i)
			self.constraint.setSuspensionCompression(self.COMPRESSION_VAL, i)
			self.constraint.setSuspensionStiffness(self.STIFFNESS_VAL, i)
			self.constraint.setRollInfluence(self.ROLL_VAL, i)
			
		# apply steering value
		
		self.constraint.setSteeringValue(self.steering_val, 0)
		self.constraint.setSteeringValue(self.steering_val, 1)
		
	def remove_constraint(self):
		
		if self.constraint is None:
			return
			
		# parent wheels and add collision objects
		
		ori = Matrix.Rotation(self.steering_val, 3, "Z")
		for i, wheel in enumerate(self.wheels):
			wheel.setParent(self)
			wheel.worldPosition = self.constraint.getWheelPosition(i)
			if i < 2:
				wheel.localOrientation = ori
				
		# remove vehicle constraint
		
		constraints.removeConstraint(self.constraint.getConstraintId())
		self.constraint = None
		
	# CAR
	
	def slowdown(self):
		for i in range(self.constraint.getNumWheels()):
			self.constraint.applyEngineForce(0, i)
			self.constraint.applyBraking(self.BRAKE_VAL, i)
			
	def remove_collision_wheels(self):
		for wheel in self.wheels:
			for obj in wheel.children:
				if COLLISION_WHEEL_PROP_NAME in obj:
					obj.endObject()
					
	def add_collision_wheels(self):
		mat_rot = Matrix.Rotation(pi * 0.5, 3, "Y")
		for wheel in self.wheels:
			col_wheel = self.scene.addObject(self.col_wheel_name)
			col_wheel.visible = False
			col_wheel.setParent(wheel)
			col_wheel.worldTransform = wheel.worldTransform
			col_wheel.localOrientation = mat_rot
			
	# DRIVER
	
	def add_driver(self, player):
		self.door_sensor.collisionCallbacks.clear()
		self.add_input_mappings()
		self.update = self.start
		self.collisionGroup = 2
		
		# deactivate player
		
		player.collisionGroup = 2
		player.suspendDynamics(True)
		player.setParent(self.driver_seat)
		player.worldTransform = self.driver_seat.worldTransform
		player.update = player.inactive
		self.driver = player
		
		# switch target
		
		game.target = self
		
	def remove_driver(self, position):
		self.door_sensor.collisionCallbacks.append(self.door_sensor_cb)
		self.remove_input_mappings()
		self.update = self.idle
		self.collisionGroup = 1
		
		# activate player
		
		player = self.driver
		player.collisionGroup = 1
		player.removeParent()
		player.restoreDynamics()
		player.worldLinearVelocity.zero()
		player.worldAngularVelocity.zero()
		player.alignAxisToVect((0, 0, 1), 2)
		player.worldPosition = position
		player.update = player.active
		self.driver = None
		
		# switch target
		
		game.target = player
		
	def exit_driver(self):
		driv_pos = self.driver.worldPosition
		driv_dim = self.driver.dimensions
		sens_pos = self.door_sensor.worldPosition
		sens_dim = game.utils.get_median_point_and_dimensions(self.door_sensor)[1]
		sens_axx = self.door_sensor.getAxisVect((1, 0, 0))
		worl_axz = Vector((0, 0, 1))
		
		for dir in (-1, 1):
			driv_edg = sens_pos + sens_axx * dir * (sens_dim.x + driv_dim.x) * 0.5
			
			#game.utils.draw_line(driv_pos, driv_edg)
			
			hit_obj, _, _ = self.rayCast(driv_edg, driv_pos)
			if hit_obj is None:
				driv_cen = sens_pos + sens_axx * dir * sens_dim.x * 0.5
				driv_off_pos = worl_axz * driv_dim.z * 0.5
				driv_off_neg = worl_axz * (driv_dim.z * 0.5 + RAY_OFFSET)
				driv_top = driv_cen + driv_off_pos
				driv_bot = driv_cen - driv_off_neg
				
				#game.utils.draw_line(driv_top, driv_bot)
				
				_, hit_pos, _ = self.rayCast(driv_bot, driv_top)
				if hit_pos is not None:
					self.remove_driver(hit_pos + driv_off_pos)
					return True
					
		return False
		
	# CALLBACKS
	
	def door_sensor_cb(self, hit_obj):
		if not isinstance(hit_obj, Player):
			return
		
		player = hit_obj
		if not player.action_hit():
			return
		
		if self.driver is None:
			if player.update == player.active:
				self.add_driver(player)
				self.restoreDynamics()
				
	def body_sensor_cb(self, hit_obj):
		if hit_obj in self.children:
			return
			
		hit_car = None
		if COLLISION_WHEEL_PROP_NAME in hit_obj:
			hit_car = hit_obj.parent.parent
		elif isinstance(hit_obj, Car):
			hit_car = hit_obj
			
		if hit_car is not None and hit_car.driver is None:
			hit_car.restoreDynamics()
			
	# STATES
	
	def start(self):
		self.update = self.drive
		
	def drive(self):
		
		if self.driver.action_hit():
			self.update = self.park
			return
		
		# get values from input
		
		front_brake_val = 0
		rear_brake_val = 0
		if game.input.down("c_handbrake"):
			if game.input.down("c_brake"):
				front_brake_val = self.BRAKE_VAL
			rear_brake_val = self.HAND_BRAKE_VAL
		elif game.input.down("c_brake"):
			front_brake_val = self.BRAKE_VAL
			rear_brake_val = self.BRAKE_VAL
			
		engine_force = 0
		wheel_drive_fac = 2 if self.WHEEL_DRIVE_MODE != FOUR_WHEEL_DRIVE else 1
		if game.input.down("c_backward"):
			engine_force = self.BACKWARD_VAL * wheel_drive_fac
		elif game.input.down("c_forward"):
			engine_force = -self.FORWARD_VAL * wheel_drive_fac
			
		dir = game.input.down("c_turn_left") - game.input.down("c_turn_right")
		if dir:
			angle_max = pi * self.WHEEL_TURN_FAC_MAX
			self.steering_val = max(min(self.steering_val + dir * self.WHEEL_TURN_VAL, angle_max), -angle_max)
		elif self.steering_val:
			dir = -self.steering_val / abs(self.steering_val)
			if dir == 1:
				self.steering_val = min(self.steering_val + dir * self.WHEEL_TURN_VAL, 0)
			else:
				self.steering_val = max(self.steering_val + dir * self.WHEEL_TURN_VAL, 0)
				
		# apply values to vehicle constraint
		
		self.constraint.applyBraking(front_brake_val, 0)
		self.constraint.applyBraking(front_brake_val, 1)
		self.constraint.applyBraking(rear_brake_val, 2)
		self.constraint.applyBraking(rear_brake_val, 3)
		
		if self.WHEEL_DRIVE_MODE == FRONT_WHEEL_DRIVE:
			for i in range(0, 2):
				self.constraint.applyEngineForce(engine_force, i)
		elif self.WHEEL_DRIVE_MODE == REAR_WHEEL_DRIVE:
			for i in range(2, 4):
				self.constraint.applyEngineForce(engine_force, i)
		elif self.WHEEL_DRIVE_MODE == FOUR_WHEEL_DRIVE:
			for i in range(0, 4):
				self.constraint.applyEngineForce(engine_force, i)
				
		self.constraint.setSteeringValue(self.steering_val, 0)
		self.constraint.setSteeringValue(self.steering_val, 1)
		
		# apply orientation of steering wheel
		
		ori = Matrix.Rotation(-self.steering_val * self.STEERING_WHEEL_TURN_FAC, 3, "Y")
		self.steering_wheel.localOrientation = ori
		
	def park(self):
		if self.worldLinearVelocity.length + self.worldAngularVelocity.length < VELOCITY_MIN:
			if self.exit_driver():
				self.update = self.settle
			else:
				self.update = self.drive
		else:
			self.slowdown()
			
	def settle(self):
		if self.timer == SETTLE_TIME:
			self.suspendDynamics()
			return
			
		self.slowdown()
		self.timer += 1
		
	def idle(self):
		pass
		
def init(cont):
	if not cont.sensors[0].positive:
		return
	game.utils.mutate(cont, Car)
	
def update(cont):
	cont.owner.update()
	