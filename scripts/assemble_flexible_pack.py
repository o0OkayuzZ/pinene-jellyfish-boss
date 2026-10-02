"""Install generated v17 assets into the standalone pack; no world edits."""
import copy, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BP, RP = ROOT/'behavior_pack', ROOT/'resource_pack'
GEN = ROOT/'docs/bosses/jellyfish/generated'

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

near = load(GEN/'jellyfish_boss_v17.geo.json')
far = load(GEN/'jellyfish_boss_v17_far.geo.json')
near['minecraft:geometry'].extend(far['minecraft:geometry'])
save(RP/'models/entity/jellyfish_boss.geo.json',near)
for path in (GEN/'v17_textures').iterdir():
    if path.is_file():
        shutil.copy2(path,RP/'textures/entity/pinene'/path.name)

client = load(RP/'entity/jellyfish_boss.entity.json')
description = client['minecraft:client_entity']['description']
description['materials'] = {'shell':'entity_alphablend','tissue':'entity_alphatest'}
description['textures'] = {role:'textures/entity/pinene/jellyfish_boss_'+role for role in ('shell','tissue')}
description['geometry'] = {role:'geometry.pinene.jellyfish_boss.'+role for role in ('shell','tissue','shell_far','tissue_far')}
description['animations'] = {
    'idle':'animation.pinene.jellyfish_boss.idle',
    'distant':'animation.pinene.jellyfish_boss.distant',
    'pulse':'animation.pinene.jellyfish_boss.pulse',
    'lod':'controller.animation.pinene.jellyfish_boss.lod',
}
description['scripts'] = {
    'pre_animation':['variable.jellyfish_far = query.distance_from_camera > 80.0;'],
    'animate':['lod'],
}
description['render_controllers'] = ['controller.render.pinene.jellyfish_boss.'+r for r in ('shell','tissue')]
save(RP/'entity/jellyfish_boss.entity.json',client)
controllers = {}
for role in ('shell','tissue'):
    controllers['controller.render.pinene.jellyfish_boss.'+role] = {
        'geometry':f'variable.jellyfish_far ? Geometry.{role}_far : Geometry.{role}',
        'materials':[{'*':'Material.'+role}],
        'textures':['Texture.'+role],
    }
save(RP/'render_controllers/jellyfish_boss.render_controllers.json',
     {'format_version':'1.8.0','render_controllers':controllers})
animation = load(GEN/'jellyfish_boss_v17.animation.json')
save(RP/'animations/jellyfish_boss.animation.json',animation)
save(RP/'animation_controllers/jellyfish_boss.lod.json',{
    'format_version':'1.10.0','animation_controllers':{
        'controller.animation.pinene.jellyfish_boss.lod':{
            'initial_state':'near','states':{
                'near':{'animations':['idle','pulse'],'blend_transition':.3,
                        'transitions':[{'far':'variable.jellyfish_far'}]},
                'far':{'animations':['distant'],'blend_transition':.3,
                       'transitions':[{'near':'!variable.jellyfish_far'}]},
            }}}})

# Bake the giant size into mesh/pivots. Keep physical scale at 1, so an engine
# applying scale to collision boxes cannot inflate the 10.5x8 box to 99.75x76.
behavior = load(BP/'entities/jellyfish_boss.behavior.json')
behavior['minecraft:entity']['components']['minecraft:scale']['value'] = 1.0
save(BP/'entities/jellyfish_boss.behavior.json',behavior)
version = [0,1,2]
for folder in (BP,RP):
    manifest = load(folder/'manifest.json')
    manifest['header']['version'] = version
    for module in manifest['modules']:
        module['version'] = version
    for dependency in manifest.get('dependencies',[]):
        if 'uuid' in dependency:
            dependency['version'] = version
    save(folder/'manifest.json',manifest)

report = {'revision':'v17','runtime_scale':1.0,'baked_visual_scale':9.5,
          'render_layers':2,'lod_switch_blocks':80,'independent_tentacles':16,
          'measured_fps':None,'near_animated_bones':113,
          'near_joint_counts':{'outer':8,'inner':6},'tentacle_period_seconds':6,
          'geometries':{}}
for item in near['minecraft:geometry']:
    cubes = [c for b in item['bones'] for c in b.get('cubes',[])]
    report['geometries'][item['description']['identifier']] = {
        'cubes':len(cubes),'triangles':sum(len(c['uv'])*2 for c in cubes),
        'bones':len(item['bones'])}
save(GEN/'jellyfish_boss_v17_report.json',report)
rig_path = ROOT/'docs/bosses/jellyfish/rig-plan.json'
rig = load(rig_path)
rig['schema_version'] = 7
rig['status'] = 'v17_flexible_tentacles_runtime_test_pending'
rig['skeleton'].update(tentacle_bone_count=112,total_bone_count=114)
for chain in rig['skeleton']['tentacles']:
    joints = 8 if chain['class'] == 'outer' else 6
    chain['segments_per_tentacle'] = joints
    chain['bone_pattern'] = f"tentacle_{chain['class']}_{{01..08}}_{{01..{joints:02d}}}"
rig['idle_animation'] = {
    'identifier':'animation.pinene.jellyfish_boss.idle','duration_seconds':6.0,
    'key_interval_seconds':.125,'keyframes_per_channel':49,
    'animated_bone_count':112,'seamless_endpoint':True,
    'per_tentacle_phase_offset':True,'per_joint_amplitude_growth':True,
    'wave_direction':'root_to_tip','bell_pulse_identifier':'animation.pinene.jellyfish_boss.pulse',
    'bell_pulse_seconds':4.0,'total_near_animated_bones':113,
}
rig['continuity'].update(visual_cubes_per_main_segment=2,
    inner_companion_cubes_per_bone=.5,segment_length_overlap_ratio=1.18,
    secondary_ribbon_cuboids=24,curve='Catmull-Rom centerlines',
    near_joint_counts={'outer':8,'inner':6})
rig['continuity']['inner_frill_cubes_per_bone'] = 0
rig['bedrock_export'] = {'format_version':'1.12.0','shell_geometry_cuboids':384,
    'tissue_geometry_cuboids':142,'emissive_geometry_cuboids':0,
    'surface_panels':256,'open_ended_segments':248,'poly_mesh_used':False}
rig['material_export'].update(roles=['shell','tissue'],bell_uv_grid=[32,8],
    bell_panorama_pixels=[512,360],source_baked=True,normal_convention='DirectX',
    pbr_manifest_integration_staged=False)
rig['material_export'].pop('bell_uv_cell_pixels',None)
rig['performance_target'] = {'normal_encounter_boss_count':1,'tentacle_cuboids':248,
    'bell_cuboids':256,'inner_body_and_skirt_cuboids':22,'final_total_cuboids':526,
    'maximum_rendered_triangles':3272,'far_cuboids':174,'far_triangles':1096,
    'lod_switch_distance_blocks':80,'lod_switching_not_yet_wired':False,
    'texture_atlas':[512,512],'render_layers':2,'measured_fps':None}
save(rig_path,rig)
print('ASSEMBLED',json.dumps(report,ensure_ascii=False))
