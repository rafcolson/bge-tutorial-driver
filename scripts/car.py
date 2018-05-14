from bge import types, constraints
from collections import OrderedDict
from mathutils import Matrix
import math, utils

# SET FINAL CONSTANTS

BRAND_PROP_NAME             = "BRAND"
STEERING_WHEEL_PROP_NAME    = "STEERING_WHEEL"
WHEEL_PROP_NAME             = "WHEEL"

WHEELS_DOWN_DIR             = (0.0, 0.0, -1.0)
WHEELS_AXLE_DIR             = (-1.0, 0.0, 0.0)
WHEELS_HAS_STEERING         = (True, True, False, False)

FRONT_WHEEL_DRIVE           = 0
REAR_WHEEL_DRIVE            = 1
FOUR_WHEEL_DRIVE            = 2

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
        
        # initialize variables
        
        self.constraint = None
        self.steering_val = 0
        
        # set initial state
        
        self.update = self.drive
        
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
        
    # STATES
    
    def start(self):
        self.update = self.drive
        
    def drive(self):
        
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
        
    def idle(self):
        pass
        
def mutate(cont):
    utils.mutate(cont, Car)
    
def update(cont):
    cont.owner.update()
    