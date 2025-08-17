import bpy
from mathutils import Vector
import bmesh

# ===== 기본 세팅 =====
image_path = "C:/Users/lovec/Desktop/goods/q.png"
fbx_path   = "C:/Users/lovec/Desktop/export.fbx"

# 기존 큐브 삭제 (있으면)
if "Cube" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)

# ===== 1) 좌표 불러오기 =====
coords = []
with open("contour_coords.txt") as f:
    for line in f:
        x, y = map(float, line.strip().split())
        coords.append((x, y, 0))  # 평면 Z=0

# ===== 2) 메시 생성 (가운데 판) =====
mesh = bpy.data.meshes.new(name="PNGContourMesh")
obj_mid = bpy.data.objects.new("PNGContour_MID", mesh)
bpy.context.collection.objects.link(obj_mid)

verts = coords
edges = [(i, i + 1) for i in range(len(coords) - 1)] + [(len(coords) - 1, 0)]
faces = [list(range(len(coords)))] if len(coords) >= 3 else []

mesh.from_pydata(verts, edges, faces)
mesh.update()

# ===== 3) 머티리얼 생성 =====
# (A) PNG 이미지 (가운데 면 전용)
mat_image = bpy.data.materials.new(name="ImageMaterial")
mat_image.use_nodes = True
bsdf_img = mat_image.node_tree.nodes.get("Principled BSDF")
tex_image = mat_image.node_tree.nodes.new("ShaderNodeTexImage")
tex_image.image = bpy.data.images.load(image_path)

mat_image.node_tree.links.new(bsdf_img.inputs['Base Color'], tex_image.outputs['Color'])
# 알파도 연결해 PNG 투명영역 살림 (필요시 주석 해제)
mat_image.node_tree.links.new(bsdf_img.inputs['Alpha'], tex_image.outputs['Alpha'])

# Blender 4.x 투명 모드
mat_image.blend_method = 'CLIP'          # 투명 영역을 깔끔히 자르고 싶으면 'CLIP'
mat_image.use_backface_culling = False

# (B) 반투명 흰색 (옆면 + 맨위/맨아래)
mat_white = bpy.data.materials.new(name="WhiteMaterial90")
mat_white.use_nodes = True
bsdf_white = mat_white.node_tree.nodes.get("Principled BSDF")
bsdf_white.inputs['Base Color'].default_value = (1, 1, 1, 1)
bsdf_white.inputs['Alpha'].default_value = 0.1
mat_white.blend_method = 'BLEND'
mat_white.use_backface_culling = False

# ===== 4) 가운데 판에 PNG 머티리얼 할당 & UV 지정 =====
obj_mid.data.materials.append(mat_image)

bm = bmesh.new()
bm.from_mesh(mesh)
uv_layer = bm.loops.layers.uv.new("UVMap")
for face in bm.faces:
    for loop in face.loops:
        vx, vy, _ = loop.vert.co
        loop[uv_layer].uv = (vx, vy)
bm.to_mesh(mesh)
bm.free()

# ===== 5) 위/아래 판 복제해서 총 3장 만들기 =====
bpy.context.view_layer.objects.active = obj_mid
obj_mid.select_set(True)

obj_top = obj_mid.copy()
obj_top.data = obj_mid.data.copy()
obj_top.name = "PNGContour_TOP"
bpy.context.collection.objects.link(obj_top)

obj_bot = obj_mid.copy()
obj_bot.data = obj_mid.data.copy()
obj_bot.name = "PNGContour_BOT"
bpy.context.collection.objects.link(obj_bot)

#scale_factor = 1.1

#for obj in [obj_top, obj_bot]:
#    obj.scale = (obj.scale[0] * scale_factor,
#                 obj.scale[1] * scale_factor,
#                 obj.scale[2] * scale_factor)

# Z 오프셋 (두께 느낌)
thickness = 0.07
obj_top.location.z =  thickness
obj_bot.location.z = -thickness

# 위/아래 판은 흰 반투명만 쓸 거라 재질 교체
for o in (obj_top, obj_bot):
    o.data.materials.clear()
    o.data.materials.append(mat_white)

# ===== 6) 세 오브젝트 합치기 (Join) =====
bpy.ops.object.select_all(action='DESELECT')
obj_mid.select_set(True)
obj_top.select_set(True)
obj_bot.select_set(True)
bpy.context.view_layer.objects.active = obj_mid
bpy.ops.object.join()
joined = bpy.context.active_object
joined.name = "PNGContour_JOINED"

# 머티리얼 슬롯 정리: [0]=ImageMaterial, [1]=WhiteMaterial90 로 강제
joined.data.materials.clear()
joined.data.materials.append(mat_image)  # slot 0
joined.data.materials.append(mat_white)  # slot 1

# ===== 7) 사이드(옆면) 생성: 세 장의 경계 브리지 =====
bm = bmesh.new()
bm.from_mesh(joined.data)

# 현재는 겹친 3장의 경계 엣지 루프가 있음 → 전부 브릿지해서 옆면 생성
boundary_edges = [e for e in bm.edges if e.is_boundary]
bmesh.ops.bridge_loops(bm, edges=boundary_edges)  # 가운데-위, 가운데-아래 사이드를 생성

bm.to_mesh(joined.data)
bm.free()

# ===== 8) 면별로 재질 배정 (정중앙=PNG, 옆면+위/아래=흰반투명) =====
bm = bmesh.new()
bm.from_mesh(joined.data)

# 세 레벨 Z값 판정용
z_mid = 0.0
z_top = thickness
z_bot = -thickness
eps  = thickness * 0.25  # 오차 허용

for f in bm.faces:
    # 면 중심 높이와 노멀로 판정
    c = f.calc_center_median()
    nz = f.normal.z

    if abs(nz) > 0.9:
        # 수평면(위/아래/가운데 중 하나)
        if abs(c.z - z_mid) <= eps:
            # 정중앙 면 → PNG
            f.material_index = 0
        else:
            # 위/아래 면 → 흰반투명
            f.material_index = 1
    else:
        # 수직면(옆면) → 흰반투명
        f.material_index = 1

bm.to_mesh(joined.data)
bm.free()

# ===== 9) 내보내기 (FBX) =====
bpy.ops.object.select_all(action='DESELECT')
joined.select_set(True)
bpy.context.view_layer.objects.active = joined
bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True)

print("DONE: 3판 생성/옆면 생성 및 재질 배정, FBX 내보냄 ->", fbx_path)