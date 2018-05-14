from car import BRANDS, BRAND_PROP_NAME, VISUAL_PROP_NAME, WHEEL_PROP_NAME

def main(cont):
    own = cont.owner
    
    for i, brand in enumerate(BRANDS):
        inst = own.scene.addObject("Car")
        inst[BRAND_PROP_NAME] = brand
        
        inst.worldPosition.z = 1
        if brand == "HOTROD":
            inst.worldPosition.x = 5
            for obj in inst.children:
                if VISUAL_PROP_NAME in obj:
                    obj.color = (0.5, 0.5, 1.0, 1.0)
                elif WHEEL_PROP_NAME in obj:
                    obj.worldPosition.z -= 0.3
                