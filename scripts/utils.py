
def mutate(cont, cls, *args):
    obj = cont.owner
    mutated_obj = cls(obj, *args)
    assert(obj is not mutated_obj)
    assert(obj.invalid)
    assert(mutated_obj is cont.owner)
    
def get_obj_by_property(objects, prop):
    for obj in objects:
        if prop in obj:
            return obj
    return None
    