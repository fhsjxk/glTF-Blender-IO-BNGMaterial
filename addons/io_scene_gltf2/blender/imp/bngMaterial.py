from ...io.com.gltf2_io import TextureInfo
from .texture import texture
from .material_utils import MaterialHelper, scalar_factor_and_texture, color_factor_and_texture, normal_map

class BngMaterialImportError(RuntimeError):
    pass

def bng_material(mh: MaterialHelper):
    """Creates node tree for BNG materials."""
    pbr_node = mh.nodes.new('ShaderNodeBsdfPrincipled')
    out_node = mh.nodes.new('ShaderNodeOutputMaterial')
    mh.links.new(pbr_node.outputs['BSDF'], out_node.inputs['Surface'])

    bng_material = mh.pymat.extras['bngMaterial']

    if bng_material.get('version') != 1.5:
        return
    
    active_layers = bng_material.get('activeLayers') or 1

    sockets = {'baseColor': pbr_node.inputs['Base Color'],
               'metallic': pbr_node.inputs['Metallic'],
               'roughness': pbr_node.inputs['Roughness'],
               'opacity': pbr_node.inputs['Alpha'],
               'normal': pbr_node.inputs['Normal'],
               'clearCoat': pbr_node.inputs['Coat Weight'],
               'clearCoatRoughness': pbr_node.inputs['Coat Roughness'],
               'clearCoatNormal': pbr_node.inputs['Coat Normal'],
               'emissive': pbr_node.inputs['Emission Color']}
    
    for layer in range(active_layers):
        sockets['baseColor'] = apply_layer_and_prop(mh, "baseColor", sockets['baseColor'], layer, False, True, False, False, False)
        sockets['metallic'] = apply_layer_and_prop(mh, "metallic", sockets['metallic'], layer, False, True, False, True, False)
        sockets['roughness'] = apply_layer_and_prop(mh, "roughness", sockets['roughness'], layer, False, True, False, True, False)
        sockets['opacity'] = apply_layer_and_prop(mh, "opacity", sockets['opacity'], layer, False, True, False, True, False)
        sockets['normal'] = apply_layer_and_prop(mh, "normal", sockets['normal'], layer, False, True, False, True, True)
        break

    mh.mat.use_backface_culling = (int(bng_material.get('doubleSided')) != True)
    mh.mat.use_backface_culling_shadow = (int(bng_material.get('doubleSided')) != True)
    mh.mat.surface_render_method = 'BLENDED'


def get_prop(bng_material, prop, layer):
    p2 = bng_material.get(prop)
    if p2:
        if type(p2) == list:
            if layer < len(p2):
                return p2[layer]
            else:
                return None
        elif type(p2) == dict:
            p3 = p2.get(str(f"{layer+1}"))
            if p3:
                return p3
            else:
                return None
    return None

def apply_layer_and_prop(mh: MaterialHelper, prop, socket, layer, mix, use_texture, use_factor, is_data, is_normal):
    bng_material = mh.pymat.extras['bngMaterial']
    index = get_prop(bng_material, f'{prop}MapIndex', layer)
    factor = get_prop(bng_material, f'{prop}Factor', layer)

    if is_normal and layer == 0:
        node = mh.nodes.new('ShaderNodeNormalMap')
        #node.inputs['Strength'] == get_prop(bng_material, f'')
        mh.links.new(socket, node.outputs['Normal'])
        socket = node.inputs['Color']

    elif factor != None and index != None and is_data and not is_normal:
        node = mh.node_tree.nodes.new('ShaderNodeMath')
        mh.node_tree.links.new(socket, node.outputs[0])
        node.operation = 'MULTIPLY'
        socket = node.inputs[0]
        node.inputs[1].default_value = factor

    elif factor != None and index != None and not is_data and not is_normal:
        node = mh.node_tree.nodes.new('ShaderNodeMix')
        node.data_type = "RGBA"
        node.blend_type = 'MULTIPLY'
        mh.node_tree.links.new(socket, node.outputs[2])
        node.inputs['Factor'].default_value = 1.0
        socket = node.inputs[6]
        node.inputs[7].default_value = [factor, factor, factor, 1]

    elif factor != None and is_data and not is_normal and not mix:
        socket.default_value = factor

    elif factor != None and not is_data and not is_normal and not mix:
        socket.default_value = [factor, factor, factor, 1]

    if use_texture and index != None:
        print(socket)
        tex_info = TextureInfo(
            extensions=None,
            extras=None,
            index=index,
            tex_coord=0
            )
        texture(
            mh,
            tex_info=tex_info,
            label=f'{prop}Map',
            location=(0, 0),
            is_data=is_data,
            color_socket=socket,
        )

    return None