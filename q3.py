import bpy
import bmesh
from mathutils import Vector

# 이미지 경로 설정
image_path = "C:/Users/lovec/Desktop/goods/q.png"

# 좌표 불러오기
coords = []
with open("contour_coords.txt") as f:
    for line in f:
        x, y = map(float, line.strip().split())
        coords.append((x, y, 0))


# 메시 생성
mesh = bpy.data.meshes.new(name="PNGContourMesh")
obj = bpy.data.objects.new("PNGContour", mesh)
bpy.context.collection.objects.link(obj)

# 정점/면 생성
verts = coords
edges = [(i, i + 1) for i in range(len(coords) - 1)] + [(len(coords) - 1, 0)]
faces = [list(range(len(coords)))] if len(coords) >= 3 else []

mesh.from_pydata(verts, edges, faces)
mesh.update()

bm = bmesh.new()
bm.from_mesh(mesh)
bm.to_mesh(mesh)
bm.free()

# 기존 큐브 삭제
if "Cube" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)

# 메시 확장 (extrude)
bm = bmesh.new()
bm.from_mesh(mesh)
bm.faces.ensure_lookup_table()
base_face = bm.faces[0]
ret = bmesh.ops.extrude_face_region(bm, geom=[base_face])
geom_extruded = ret['geom']
verts_extruded = [e for e in geom_extruded if isinstance(e, bmesh.types.BMVert)]
bmesh.ops.translate(bm, verts=verts_extruded, vec=(0, 0, 0.03))
bm.to_mesh(mesh)
bm.free()

# 머티리얼 생성
mat_image = bpy.data.materials.new(name="ImageMaterial")
mat_image.use_nodes = True
bsdf = mat_image.node_tree.nodes.get("Principled BSDF")
tex_image = mat_image.node_tree.nodes.new("ShaderNodeTexImage")
tex_image.image = bpy.data.images.load(image_path)
mat_image.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])

mat_white = bpy.data.materials.new(name="WhiteMaterial")
mat_white.diffuse_color = (1.0, 1.0, 1.0, 1.0)

# 머티리얼 할당
obj.data.materials.append(mat_image)  # index 0
obj.data.materials.append(mat_white)  # index 1

# 면에 따라 머티리얼 적용
bm = bmesh.new()
bm.from_mesh(mesh)
for face in bm.faces:
    if abs(face.normal.z) > 0.9:
        face.material_index = 0
    else:
        face.material_index = 1

# UV 좌표
uv_layer = bm.loops.layers.uv.new("UVMap")
for face in bm.faces:
    if abs(face.normal.z) > 0.9:
        for loop in face.loops:
            vx, vy, _ = loop.vert.co
            loop[uv_layer].uv = (vx, vy)

# Bisect 면 분할
# Bisect: 위/아래 0.5로 한 번 나누기
# Bisect 면 분할
top_faces = [f for f in bm.faces if abs(f.normal.z) > 0.9]
top_bounds = [v.co for f in top_faces for v in f.verts]
min_x = min(v.x for v in top_bounds)
max_x = max(v.x for v in top_bounds)
min_y = min(v.y for v in top_bounds)
max_y = max(v.y for v in top_bounds)
step = 0.08

x = min_x + step
while x < max_x:
    bmesh.ops.bisect_plane(bm, geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
                           plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    x += step

y = min_y + step
while y < max_y:
    bmesh.ops.bisect_plane(bm, geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
                           plane_co=(0, y, 0), plane_no=(0, 1, 0))
    y += step
# 옆면 가로 Bisect (Z축 중간에서)
side_faces = [f for f in bm.faces if abs(f.normal.z) <= 0.9]
side_bounds = [v.co for f in side_faces for v in f.verts]
min_z = min(v.z for v in side_bounds)
max_z = max(v.z for v in side_bounds)
mid_z = (min_z + max_z) / 2

bmesh.ops.bisect_plane(
    bm,
    geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
    plane_co=(0, 0, mid_z),
    plane_no=(0, 0, 1)
)
bm.to_mesh(mesh)
bm.free()

# Cloth 설정 추가
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_add(type='CLOTH')
cloth = obj.modifiers['Cloth']

# Cloth 설정 조정
cloth.settings.use_pressure = True
cloth.settings.uniform_pressure_force = 5.0

cloth.settings.effector_weights.gravity = 0.0
cloth.collision_settings.use_self_collision = True
cloth.collision_settings.self_distance_min = 0
cloth.collision_settings.self_friction = 0



# FBX로 저장
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.fbx(filepath="C:/Users/lovec/Desktop/export.fbx", use_selection=True)