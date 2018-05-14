from bge import types, constraints
from collections import OrderedDict
from mathutils import Matrix, Vector
from player import Player
import math, utils

#constraints.setDebugMode(constraints.DBG_DRAWWIREFRAME)
constraints.setContactBreakingTreshold(0.005)

# SET FINAL CONSTANTS

BRAND_PROP_NAME             = "BRAND"
STEERING_WHEEL_PROP_NAME    = "STEERING_WHEEL"
WHEEL_PROP_NAME             = "WHEEL"
VISUAL_PROP_NAME            = "VISUAL"
DRIVER_SEAT_PROP_NAME       = "DRIVER_SEAT"
DOOR_SENSOR_PROP_NAME       = "DOOR_SENSOR"

WHEELS_DOWN_DIR             = (0.0, 0.0, -1.0)
WHEELS_AXLE_DIR             = (-1.0, 0.0, 0.0)
WHEELS_HAS_STEERING         = (True, True, False, False)

FRONT_WHEEL_DRIVE           = 0
REAR_WHEEL_DRIVE            = 1
FOUR_WHEEL_DRIVE            = 2

VELOCITY_MIN                = 0.5
RAY_OFFSET                  = 0.5
SETTLE_TIME                 = 120

# DEFINE BRANDS

BRANDS = {
    "DEFAULT": {
        "WHEELS_SUSP_REST_LEN_F":   0.2,
        "WHEELS_SUSP_REST_LEN_R":   0.2,
        "FRICTION_VAL":             1.0,
        "DAMPING_VAL":              5.0,
        "COMPRESSION_VAL":          5.0,
        "STIFFNESS_VAL":            50.0,
        "ROLL_VAL":                 0.5,
        "BRAKE_VAL":                10.0,
        "HAND_BRAKE_VAL":           500.0,
        "FORWARD_VAL":              500.0,
        "BACKWARD_VAL":             250.0,
        "WHEEL_TURN_VAL":           0.1,
        "WHEEL_TURN_FAC_MAX":       0.25,
        "STEERING_WHEEL_TURN_FAC":  2.0,
        "LINEAR_VELOCITY_MAX":      18.0,
        "WHEEL_DRIVE_MODE":         0
    },
    "HOTROD": {
        "WHEELS_SUSP_REST_LEN_F":   0.5,
        "WHEELS_SUSP_REST_LEN_R":   0.5,
        "FRICTION_VAL":             1.0,
        "DAMPING_VAL":              2.5,
        "COMPRESSION_VAL":          2.5,
        "STIFFNESS_VAL":            10.0,
        "ROLL_VAL":                 0.75,
        "BRAKE_VAL":                15.0,
        "HAND_BRAKE_VAL":           750.0,
        "FORWARD_VAL":              750.0,
        "BACKWARD_VAL":             375.0,
        "WHEEL_TURN_VAL":           0.1,
        "WHEEL_TURN_FAC_MAX":       0.25,
        "STEERING_WHEEL_TURN_FAC":  1.0,
        "LINEAR_VELOCITY_MAX":      20.0,
        "WHEEL_DRIVE_MODE":         1
    }
}

class Car(types.KX_GameObject):
    
    # OVERRIDES
    
    def endObject(self):
        self.remove_driver()
        self.remove_constraint()
        super(Car, self).endObject()
        
    def suspendDynamics(self, *args):
        self.worldLinearVelocity.zero()
        self.worldAngularVelocity.zero()
        super(Car, self).suspendDynamics(*args)
        
    # INITIALIZATION
    
    def __init__(self, own):
        
        # get constants from brand
        
        brand = BRANDS[self[BRAND_PROP_NAME]]
        
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
        
        # get references from input
        
        self.forward = self.sensors["forward"]
        self.backward = self.sensors["backward"]
        self.brake = self.sensors["brake"]
        self.hand_brake = self.sensors["hand_brake"]
        self.turn_left = self.sensors["turn_left"]
        self.turn_right = self.sensors["turn_right"]
        self.action = self.sensors["action"]
        
        # get and store wheels and steering wheel
        
        wheels = {}
        for obj in self.children:
            if STEERING_WHEEL_PROP_NAME in obj:
                self.steering_wheel = obj
            elif WHEEL_PROP_NAME in obj:
                wheels[obj] = obj.localPosition.xyz
        self.wheels = OrderedDict(sorted(wheels.items(), key=lambda item: item[0][WHEEL_PROP_NAME]))
        
        # get and store driver seat and door sensor
        
        self.driver_seat = utils.get_obj_by_property(self.children, DRIVER_SEAT_PROP_NAME)
        self.door_sensor = utils.get_obj_by_property(self.children, DOOR_SENSOR_PROP_NAME)
        
        # initialize variables
        
        self.constraint = None
        self.driver = None
        self.steering_val = 0
        self.timer = 0
        
        # set initial state
        
        self.door_sensor.collisionCallbacks.append(self.door_sensor_cb)
        self.update = self.settle
        
        # add vehicle constraint
        
        self.add_constraint()
        
        # set max linear velocity
        
        self.linVelocityMax = self.LINEAR_VELOCITY_MAX
        
    # CONSTRAINT
        
    def add_constraint(self):
        
        if self.constraint is not None:
            return
            
        # create and store vehicle constraint
        
        constraint = constraints.createConstraint(self.getPhysicsId(), 0, constraints.VEHICLE_CONSTRAINT)
        self.constraint = constraints.getVehicleConstraint(constraint.getConstraintId())
        
        # move wheels to vehicle constraint and set values
        
        for i, wheel in enumerate(self.wheels):
            wheel.removeParent()
            
            susp_rest_len = self.WHEELS_SUSP_REST_LEN[i]
            attach_pos = self.wheels[wheel].xyz
            attach_pos.z += susp_rest_len
            down_dir = WHEELS_DOWN_DIR
            axle_dir = WHEELS_AXLE_DIR
            radius = (utils.get_dimensions(wheel).z * wheel.localScale.z) * 0.5
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
            
        # parent wheels
        
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
            
    # DRIVER
    
    def add_driver(self, player):
        player.suspendDynamics(True)
        player.setParent(self.driver_seat)
        player.worldTransform = self.driver_seat.worldTransform
        player.update = player.inactive
        self.driver = player
        
        self.update = self.start
        self.door_sensor.collisionCallbacks.clear()
        
    def remove_driver(self):
        player = self.driver
        player.removeParent()
        player.restoreDynamics()
        player.worldLinearVelocity.zero()
        player.worldAngularVelocity.zero()
        player.alignAxisToVect((0, 0, 1), 2)
        player.update = player.active
        self.driver = None
        
        self.update = self.idle
        self.door_sensor.collisionCallbacks.append(self.door_sensor_cb)
        
    def exit_driver(self):
        driv_pos = self.driver.worldPosition
        driv_dim = utils.get_dimensions(self.driver)
        sens_pos = self.door_sensor.worldPosition
        sens_dim = utils.get_dimensions(self.door_sensor)
        sens_axx = self.door_sensor.getAxisVect((1, 0, 0))
        worl_axz = Vector((0, 0, 1))
        
        for dir in (-1, 1):
            driv_edg = sens_pos + sens_axx * dir * (sens_dim.x + driv_dim.x) * 0.5
            
            #utils.draw_line(driv_pos, driv_edg)
            
            hit_obj, _, _ = self.rayCast(driv_edg, driv_pos)
            if hit_obj is None:
                driv_cen = sens_pos + sens_axx * dir * sens_dim.x * 0.5
                driv_off_pos = worl_axz * driv_dim.z * 0.5
                driv_off_neg = worl_axz * (driv_dim.z * 0.5 + RAY_OFFSET)
                driv_top = driv_cen + driv_off_pos
                driv_bot = driv_cen - driv_off_neg
                
                #utils.draw_line(driv_top, driv_bot)
                
                _, hit_pos, _ = self.rayCast(driv_bot, driv_top)
                if hit_pos is not None:
                    self.driver.worldPosition = hit_pos + driv_off_pos
                    self.remove_driver()
                    return True
                    
        return False
        
    # CALLBACKS
    
    def door_sensor_cb(self, hit_obj):
        if not self.action.positive:
            return
        
        if self.driver is None and isinstance(hit_obj, Player):
            player = hit_obj
            if player.update == player.active:
                self.add_driver(player)
                self.update = self.start
                
                if self.isSuspendDynamics:
                    self.restoreDynamics()
                    
                if self.constraint is None:
                    self.add_constraint()
                    
    # STATES
    
    def start(self):
        self.update = self.drive
        
    def drive(self):
        
        if self.action.positive:
            self.update = self.park
            return
        
        # get values from input
        
        front_brake_val = 0
        rear_brake_val = 0
        if self.hand_brake.positive:
            if self.brake.positive:
                front_brake_val = self.BRAKE_VAL
            rear_brake_val = self.HAND_BRAKE_VAL
        elif self.brake.positive:
            front_brake_val = self.BRAKE_VAL
            rear_brake_val = self.BRAKE_VAL
            
        engine_force = 0
        wheel_drive_fac = 2 if self.WHEEL_DRIVE_MODE != FOUR_WHEEL_DRIVE else 1
        if self.backward.positive:
            engine_force = self.BACKWARD_VAL * wheel_drive_fac
        elif self.forward.positive:
            engine_force = -self.FORWARD_VAL * wheel_drive_fac
            
        dir = self.turn_left.positive - self.turn_right.positive
        if dir:
            angle_max = math.pi * self.WHEEL_TURN_FAC_MAX
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
            self.remove_constraint()
            self.update = self.idle
            self.timer = 0
            return
            
        self.slowdown()
        self.timer += 1
        
    def idle(self):
        pass
        
def mutate(cont):
    utils.mutate(cont, Car)
    
def update(cont):
    cont.owner.update()
    