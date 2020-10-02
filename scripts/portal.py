from bge import types
from scripts import game

class Portal(types.KX_GameObject):
    
    def __init__(self, own):
        pass
        
    def update(self):
        pass
        
def init(cont):
    if not cont.sensors[0].positive:
        return
    game.portals.append(game.utils.mutate(cont, Portal))
    
def update(cont):
    cont.owner.update()
    