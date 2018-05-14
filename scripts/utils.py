from mathutils import Vector

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
    
def get_dimensions(obj):
    mesh = obj.meshes[0]
    col_xyz = [[], [], []]
    for mat_index in range(mesh.numMaterials):
        for vert_index in range(mesh.getVertexArrayLength(mat_index)):
            vert_XYZ = mesh.getVertex(mat_index, vert_index).XYZ
            [col_xyz[i].append(vert_XYZ[i]) for i in range(3)]
    return Vector([abs(max(axis)) + abs(min(axis)) for axis in col_xyz])
