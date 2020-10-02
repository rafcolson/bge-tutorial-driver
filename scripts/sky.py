from bge import types
from scripts import game

class Sky(types.KX_GameObject):
    
    def __init__(self, own):
        pass
        
    def update(self):
        pass
        
def init(cont):
    if not cont.sensors[0].positive:
        return
    game.sky = game.utils.mutate(cont, Sky)
    
def update(cont):
    cont.owner.update()
    