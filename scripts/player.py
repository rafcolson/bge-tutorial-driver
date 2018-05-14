from bge import types
from mathutils import Vector
import utils

class Player(types.KX_GameObject):
    
    def __init__(self, own):
        
        # GET CONSTANTS FROM PROPERTIES
        
        self.WALK_SPEED = self["WALK_SPEED"]
        self.RUN_SPEED = self["RUN_SPEED"]
        self.JUMP_SPEED = self["JUMP_SPEED"]
        self.TURN_SPEED = self["TURN_SPEED"]
        self.LERP = self["LERP"]
        
        # INITIALIZE VARIABLES
        
        self.vel = Vector()
        self.rot = Vector()
        
        # INITIALIZE STATE
        
        self.update = self.active
        
    def active(self):
        
        # GET INPUT
        
        ground = self.sensors["ground"]
        forward = self.sensors["forward"]
        backward = self.sensors["backward"]
        turn_left = self.sensors["turn_left"]
        turn_right = self.sensors["turn_right"]
        jump = self.sensors["jump"]
        run = self.sensors["run"]
        
        # GET VELOCITY AND ROTATION
        
        if not ground.positive:
            self.vel.y = self.localLinearVelocity.y * self.LERP
        else:
            dir = forward.positive - backward.positive
            if dir:
                self.vel.y = dir * self.RUN_SPEED if run.positive else dir * self.WALK_SPEED
            else:
                self.vel.y = 0
            
        self.vel.z = jump.positive * ground.positive
        if self.vel.z:
            self.vel.z *= self.JUMP_SPEED
        else:
            self.vel.z = self.localLinearVelocity.z
            
        self.rot.z = (turn_left.positive - turn_right.positive) * self.TURN_SPEED
        
        # APPLY VELOCITY AND ROTATION
        
        self.localLinearVelocity = self.vel
        self.applyRotation(self.rot, True)
        
    def inactive(self):
        pass
        
def mutate(cont):
    utils.mutate(cont, Player)
    
def update(cont):
    cont.owner.update()
    