from bge import types
from scripts import game

class CustomObject(types.KX_GameObject):
    
    def __init__(self, own):
        pass
        
    def update(self):
        pass
        
def init(cont):
    if not cont.sensors[0].positive:
        return
    game.utils.mutate(cont, CustomObject)
    
def update(cont):
    cont.owner.update()
    