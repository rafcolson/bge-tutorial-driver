from bge import types
import utils

class CustomObject(types.KX_GameObject):
    
    def __init__(self, own):
        pass
        
    def update(self):
        pass
        
def mutate(cont):
    utils.mutate(cont, CustomObject)
    
def update(cont):
    cont.owner.update()
    