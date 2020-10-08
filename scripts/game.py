from bge import types, events, logic, render
from collections import OrderedDict
from mathutils import Matrix, Vector
from errno import ENOENT
import pickle
import os
import re

BLEND_FILE_EXT = ".blend"
TXT_EXT = ".txt"
OBJECTS_FOLDER = "objects"
PLAYERS_FILE_NAME = "Players"
SAVE_FILE_NAME = "Save"

PLAYER = "player"
AREA = "area"
PROGRESS = "progress"
SAVE_DATA_EMPTY = OrderedDict(
	{
		AREA : "Area_A",
		PLAYER : "Player_A",
		PROGRESS : "{}"
	}
)
HUD = "Hud"
SCENE = "Scene"

TICK_RATE = 60

loaded_libs = OrderedDict()
loading_progress = None
loading_status = None
players_data = None
save_data = None

hud = None
scene = None

area = None
terrain = None
sky = None
portals = []
player = None
lighting = None
follower = None
tracker = None
camera = None
target = None

class Utils:
	
	def add_attr(self, ob, module):
		setattr(module, ob.name.lower().lstrip("_"), ob)
		
	def remove_attr(self, ob, module):
		delattr(module, ob.name.lower().lstrip("_"))
		
	def get_class_name(ob):
		return ob.__class__.__name__
		
	def get_module(mod_path):
		components = mod_path.split('.')
		mod = __import__(components[0])
		for comp in components[1:]:
			mod = getattr(mod, comp)
		return mod
		
	def mutate(self, cont, cls, *args):
		ob = cont.owner
		mutated_obj = cls(ob, *args)
		assert(ob is not mutated_obj)
		assert(ob.invalid)
		assert(mutated_obj is cont.owner)
		return mutated_obj
		
	def get_obj_by_name(self, objects, name):
		try:
			return objects[name]
		except KeyError:
			return None
		
	def get_obj_by_property(self, objects, prop):
		for ob in objects:
			if prop in ob:
				return ob
		return None
		
	def get_obj_by_class(self, objects, cls):
		for ob in objects:
			if isinstance(ob, cls):
				return ob
		return None
		
	def get_group_parents(self, inst):
		if inst.groupMembers is None:
			return None
		l = []
		for ob in inst.groupMembers:
			if ob.parent is None:
				l.append(ob)
		return l
		
	def get_all_objects(self, sce):
		d = {}
		for ob in sce.objects:
			d[ob.name] = ob
		for ob in sce.objectsInactive:
			d[ob.name] = ob
		return d
		
	def get_objects_in_frustum(self, objects, camera):
		out = []
		for ob in objects:
			if not ob.meshes:
				continue
			box = self.get_box_points(*self.get_median_point_and_dimensions(ob), ob.worldTransform)
			if (camera.boxInsideFrustum(box) != camera.OUTSIDE):
				out.append(ob)
		return out
		
	def get_active_lights(self, sce):
		return [lit for lit in sce.objects if isinstance(lit, types.KX_LightObject) and (1&lit.layer)]
		
	def get_inactive_lights(self, sce):
		return [lit for lit in sce.objectsInactive if isinstance(lit, types.KX_LightObject) and not (1&lit.layer)]
		
	def get_data_from_object(self, ob, group_member_name=None):
		ob_data = {}
		ob_data["group_member"] = group_member_name
		ob_data["name"] = ob.name
		ob_data["properties"] = {n: ob[n] for n in ob.getPropertyNames()}
		ob_data["transform"] = [list(v) for v in ob.worldTransform]
		ob_data["velocities"] = [list(ob.worldLinearVelocity), list(ob.worldAngularVelocity)] if group_member_name is None and ob.getPhysicsId() else None
		ob_data["children"] = [o.name for o in ob.children]
		ob_data["parent"] = ob.parent.name if ob.parent is not None else None
		ob_data["visible"] = ob.visible
		return ob_data
		
	def get_data_from_objects(self, scene, instances_only=False):
		data = {}
		for ob in scene.objects:
			group_member_name = None
			if ob.groupMembers:
				group_member_name = [o for o in ob.groupMembers if o.parent is None][0].name
			elif instances_only or not ob.meshes:
				continue
			data[ob.name] = utils.get_data_from_object(ob, group_member_name)
		return data
		
	def add_object_from_data(self, scene, ob_data):
		group_member_name = ob_data["group_member"]
		name = ob_data["name"] if group_member_name is None else group_member_name
		ob = scene.addObject(name)
		
		for k, v in ob_data["properties"].items():
			ob[k] = v
			
		parent_name = ob_data["parent"]
		if parent_name is not None:
			ob.setParent(scene.objects[parent_name], False, False)
		ob.worldTransform = ob_data["transform"]
		
		if ob_data["group_member"] is None:
			velocities = ob_data["velocities"]
			if velocities is not None:
				ob.worldLinearVelocity, ob.worldAngularVelocity = velocities
			ob.visible = ob_data["visible"]
			
		return ob
		
	def add_objects_from_data(self, scene, data):
		d = data.copy()
		parents = [ob_name for ob_name, ob_data in data.items() if ob_data["parent"] is None]
		
		for parent_name in parents:
			parent_data = data[parent_name]
			self.add_object_from_data(scene, parent_data)
			del d[parent_name]
			
			for child_name in parent_data["children"]:
				child_name = data[child_name]
				child = self.add_object_from_data(scene, child_name)
				del d[child_name]
				
		for ob_name, ob_data in d.items():
			self.add_object_from_data(scene, ob_data)
			
	def add_scene(self, scene_name, overlay=1):
		i = overlay + len(logic.getSceneList()) - 1
		logic.addScene(scene_name, overlay)
		return logic.getSceneList()[i]
		
	def get_median_point_and_dimensions(self, ob):
		mesh = ob.meshes[0]
		nl = [[], [], []]
		for mat_index in range(mesh.numMaterials):
			for vert_index in range(mesh.getVertexArrayLength(mat_index)):
				v = mesh.getVertex(mat_index, vert_index).XYZ
				[nl[i].append(v[i]) for i in range(3)]
				
		if not len(nl[1]):
			return Vector(), Vector()
			
		median_point = Vector([sum(axis) / len(axis) for axis in nl])
		dimensions = Vector([abs(max(axis)) + abs(min(axis)) for axis in nl])
		
		return median_point, dimensions
		
	def get_box_points(self, dimensions, median_point=Vector(), transform=None, velocity=None):
		v = dimensions.copy()
		
		if median_point is not None:
			v -= median_point
		v *= 0.5
		
		if transform is not None:
			v = transform * v
			
		if velocity is not None:
			v += velocity / TICK_RATE
			
		nl = []
		for i in range(3):
			nl.append([round(-v[i] + median_point[i], 6), round(v[i] + median_point[i], 6)])
			
		box_points = []
		for j in range(2):
			for k in range(2):
				for l in range(2):
					box_points.append(Vector([nl[0][j], nl[1][k], nl[2][l]]))
					
		return box_points
		
	def draw_line(self, v0, v1, color=(1, 1, 1)):
		render.drawLine(v0, v1, color)
		
	def draw_box(self, box_points, transform=None, velocity=None, color=(1, 1, 1)):
		bp = box_points.copy()
		
		if transform is not None:
			for i in range(len(bp)):
				bp[i] = transform * bp[i]
				
		if velocity is not None:
			v = velocity / TICK_RATE
			for i in range(len(bp)):
				bp[i] += v
				
		self.draw_line(bp[1], bp[0], color)
		self.draw_line(bp[1], bp[3], color)
		self.draw_line(bp[1], bp[5], color)
		self.draw_line(bp[2], bp[0], color)
		self.draw_line(bp[2], bp[3], color)
		self.draw_line(bp[2], bp[6], color)
		self.draw_line(bp[4], bp[0], color)
		self.draw_line(bp[4], bp[5], color)
		self.draw_line(bp[4], bp[6], color)
		self.draw_line(bp[7], bp[3], color)
		self.draw_line(bp[7], bp[5], color)
		self.draw_line(bp[7], bp[6], color)
		
utils = Utils()

def add(ob):
	utils.add_attr(ob, __import__(__name__).game)
	
def remove(ob):
	utils.remove_attr(ob, __import__(__name__).game)

"""

Contains input mappings. Each mapping value is a dictionary of descriptors per input device; "k" for keyboard, "m" for mouse and "g0, g1, ..." for gamepads.

Keys: "a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z, zero, one, two, three, four, five, six, seven, eight, nine, capslock, leftctrl, leftalt, rightalt, rightctrl, rightshift, leftshiftarrow keys, leftarrow, downarrow, rightarrow, uparrow, pad0, pad1, pad2, pad3, pad4, pad5, pad6, pad7, pad8, pad9, padperiod, padslash, padaster, padminus, padenter, padplus, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, accentgrave, backslash, backspace, comma, del, end, equal, esc, home, insert, leftbracket, linefeed, minus, pagedown, pageup, pause, period, quote, rightbracket, enter, semicolon, slash, space, tab"

Mouse buttons: "left, middle, right, wheelup, wheeldown, x, y"

Gamepad buttons: "btn-0, btn-1, btn-2, ..."
Gamepad hats: "hat-up, hat-right, hat-up-right, hat-down, hat-down-right, hat-left, hat-up-left, hat-down-left"
Gamepad axis: "axis0-left, axis0-right, axis0-up, axis0-down, axis1-left, axis1-right, axis1-up, axis1-down"

Example:
	
	import game
	
	game.input["jump"] = {"k": ["space", "enter"], "m": ["left"], "g0": ["btn-0", "btn-1"]}
	
	def main(cont):
		if game.input.hit("jump"):
			cont.owner.applyForce((0, 0, 100))
			
Run in foreground scene so input is updated before anything else.

"""

class Input(OrderedDict):
	
	class Keyboard(OrderedDict):
		
		def __init__(self, *arg, **kw):
			super(OrderedDict, self).__init__(*arg, **kw)
			for code in logic.keyboard.events:
				try:
					self[events.EventToString(code).replace("KEY", "").lower()] = code
				except ValueError:
					pass
					
		def get_clipboard():
			return logic.keyboard.getClipboard()
			
		def set_clipboard(s):
			return logic.keyboard.setClipboard(s)
			
		def all(self):
			return {s : logic.keyboard.events[code] for s, code in self.items()}
			
		def active(self):
			d = logic.keyboard.active_events
			return {s : d[code] for s, code in self.items() if code in d}
			
		def none(self, s):
			if logic.keyboard.events[self[s]] == logic.KX_INPUT_NONE:
				return True
			return False
			
		def hit(self, s):
			if logic.keyboard.events[self[s]] == logic.KX_INPUT_JUST_ACTIVATED:
				return True
			return False
			
		def down(self, s):
			if logic.keyboard.events[self[s]] == logic.KX_INPUT_ACTIVE:
				return True
			return False
			
		def up(self, s):
			if logic.keyboard.events[self[s]] == logic.KX_INPUT_JUST_RELEASED:
				return True
			return False
			
	class Mouse(OrderedDict):
		
		def __init__(self, *arg, **kw):
			super(OrderedDict, self).__init__(*arg, **kw)
			for code in logic.mouse.events:
				try:
					self[events.EventToString(code).replace("MOUSE", "").lower()] = code
				except ValueError:
					pass
					
		def get_position(self):
			return tuple(logic.mouse.position)
			
		def set_position(self, t):
			logic.mouse.position = t
			
		def visible(self):
			return logic.mouse.visible
			
		def show(self):
			logic.mouse.visible = True
			
		def hide(self):
			logic.mouse.visible = False
			
		def all(self):
			return {s : logic.mouse.events[code] for s, code in self.items()}
			
		def active(self):
			d = logic.mouse.active_events
			return {s : d[code] for s, code in self.items() if code in d}
			
		def none(self, s):
			if logic.mouse.events[self[s]] == logic.KX_INPUT_NONE:
				return True
			return False
			
		def hit(self, s):
			if logic.mouse.events[self[s]] == logic.KX_INPUT_JUST_ACTIVATED:
				return True
			return False
			
		def down(self, s):
			if logic.mouse.events[self[s]] == logic.KX_INPUT_ACTIVE:
				return True
			return False
			
		def up(self, s):
			if logic.mouse.events[self[s]] == logic.KX_INPUT_JUST_RELEASED:
				return True
			return False
			
	class Gamepad(OrderedDict):
		
		AXIS_DEAD_ZONE_DEFAULT = 0.1
		
		HAT = {1:"up", 2:"right", 4:"down", 8:"left", 3:"up-right", 6:"down-right", 12:"down-left", 9:"up-left"}
		AXIS = [["0-left", "0-right"], ["0-up", "0-down"], None, ["1-left", "1-right"], ["1-up", "1-down"], None]
		
		def __init__(self, index, *arg, **kw):
			super(OrderedDict, self).__init__(*arg, **kw)
			self.index = index
			gamepad = logic.joysticks[self.index]
			for code in range(gamepad.numButtons):
				self["btn-" + str(code)] = code
			for code, s in self.HAT.items():
				self["hat-" + s] = code
			idx = 20
			for i, l in enumerate(self.AXIS):
				if l is None:
					continue
				for j in range(2):
					self["axis" + l[j]] = idx
					idx += 1
			self.axis_dead_zone = self.AXIS_DEAD_ZONE_DEFAULT
			self.hit_down_set = set()
			self.down_set = set()
			self.hit_set = set()
			self.up_set = set()
			
		def name(self):
			return logic.joysticks[self.index].name
			
		def update(self):
			gamepad = logic.joysticks[self.index]
			new_hit_down_set = set()
			for code in gamepad.activeButtons:
				new_hit_down_set.add("btn-" + str(code))
			for code, s in self.HAT.items():
				if code in gamepad.hatValues:
					new_hit_down_set.add("hat-" + s)
			for i, axis in enumerate(gamepad.axisValues):
				l = self.AXIS[i]
				if l is None:
					continue
				axis_abs = abs(axis)
				if axis_abs > self.axis_dead_zone:
					new_hit_down_set.add("axis" + l[1 if axis / axis_abs == 1 else 0])
			self.up_set = self.hit_down_set - new_hit_down_set
			self.hit_set = new_hit_down_set - self.hit_down_set
			self.down_set = new_hit_down_set - self.hit_set
			self.hit_down_set = new_hit_down_set
			
		def all(self):
			d = self.active()
			for s in self:
				if s not in d:
					d[s] = 0
			return
			
		def active(self):
			return {s : i + 1 for i, set in enumerate((self.hit_set, self.down_set, self.up_set)) for s in set}
			
		def none(self, s):
			if s not in self.active():
				return True
			return False
			
		def hit(self, s):
			if s in self.hit_set:
				return True
			return False
			
		def down(self, s):
			if s in self.down_set:
				return True
			return False
			
		def up(self, s):
			if s in self.up_set:
				return True
			return False
			
	def __init__(self, *arg, **kw):
		super(Input, self).__init__(*arg, **kw)
		self.keyboard = Input.Keyboard()
		self.mouse = Input.Mouse()
		self.gamepads = [Input.Gamepad(i) for i, j in enumerate(logic.joysticks) if j is not None]
		self.devices = {"k" : self.keyboard, "m" : self.mouse}
		for gamepad in self.gamepads:
			self.devices["g" + str(gamepad.index)] = gamepad
			
	def none(self, s):
		for k, v in self[s].items():
			if k in self.devices:
				for d in v:
					if not self.devices[k].none(d):
						return False
		return True
		
	def hit(self, s):
		for k, v in self[s].items():
			if k in self.devices:
				for d in v:
					if self.devices[k].hit(d):
						return True
		return False
		
	def down(self, s):
		for k, v in self[s].items():
			if k in self.devices:
				for d in v:
					if self.devices[k].down(d):
						return True
		return False
		
	def up(self, s):
		for k, v in self[s].items():
			if k in self.devices:
				for d in v:
					if self.devices[k].up(d):
						return True
		return False
	
	def all(self):
		d = {}
		for s in self:
			for status, func in enumerate((self.none, self.hit, self.down, self.up)):
				if func(s):
					d[s] = status
					break
		return d
		
	def active(self):
		d = {}
		for s in self:
			for i, func in enumerate((self.hit, self.down, self.up)):
				if func(s):
					d[s] = i + 1
					break
		return d
		
	def update(self):
		for gamepad in self.gamepads:
			gamepad.update()
			
input = Input()

def get_players_file_name_and_path():
	return PLAYERS_FILE_NAME, os.path.join(logic.expandPath("//"), OBJECTS_FOLDER, PLAYERS_FILE_NAME + BLEND_FILE_EXT)
	
def get_area_file_name_and_path():
	area_file_name = save_data[AREA]
	area_path = os.path.join(logic.expandPath("//"), area_file_name + BLEND_FILE_EXT)
	return area_file_name, area_path
	
def read_save_file(file_name):
	file_path = os.path.join(logic.expandPath("//"), file_name)
	if os.path.exists(file_path):
		with open(file_path, "rb") as f:
			return OrderedDict(pickle.load(f))
	raise FileNotFoundError(ENOENT, os.strerror(ENOENT), file_path)
	
def write_save_file(data, file_name):
	file_path = os.path.join(logic.expandPath("//"), file_name)
	with open(file_path, "wb") as f:
		pickle.dump(data, f)

def free(*libs):
	if not len(libs):
		libs = loaded_libs.keys()
		
	for lib_name in libs:
		lib_path = loaded_libs[lib_name]
		logic.LibFree(lib_name)
		print('Freeing %s' % lib_name)
		
class Game(types.KX_GameObject):
	
	STATE_INIT = logic.KX_STATE1
	STATE_LOAD = logic.KX_STATE2
	STATE_UPDATE = logic.KX_STATE3
	STATE_RESTART = logic.KX_STATE4
	STATE_END = logic.KX_STATE5
	
	def __init__(self, own):
		input["game_restart"] = {"k": ["p"], "g0": ["btn-7"]}
		input["game_end"] = {"k": ["esc"], "g0": ["btn-6"]}
		
	def init(self):
		logic.addScene(SCENE)
		logic.addScene(HUD)
		self.state = self.STATE_LOAD
		
	def load(self):
		if loading_progress != 1.0:
			return
		self.scene.world.backgroundColor = scene.scene.world.backgroundColor
		self.scene.world.ambientColor = scene.scene.world.ambientColor
		self.scene.world.mistColor = scene.scene.world.mistColor
		self.state = self.STATE_UPDATE
		
	def update(self):
		if input.hit("game_restart"):
			self.state = self.STATE_RESTART
		elif input.hit("game_end"):
			self.state = self.STATE_END
			
def init(cont):
	if not cont.sensors[0].positive:
		return
	utils.mutate(cont, Game)
	cont.owner.init()
	
def load(cont):
	cont.owner.load()
	
def update(cont):
	input.update()
	cont.owner.update()
	
def restart(cont):
	if not cont.sensors[0].positive:
		return
	free()
	logic.restartGame()
		
def end(cont):
	if not cont.sensors[0].positive:
		return
	free()
	logic.endGame()
	