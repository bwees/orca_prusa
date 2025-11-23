"""
Mapping registries for converting PrusaSlicer settings to OrcaSlicer format.
"""
from converters.base import ConverterRegistry, ConversionResult


def create_print_registry():
    """Create registry for print profile settings."""
    registry = ConverterRegistry()
    
    # Layer height settings
    registry.register_simple("layer_height", "layer_height")
    registry.register_simple("first_layer_height", "initial_layer_print_height")
    registry.register_simple("min_layer_height", "min_layer_height")
    registry.register_simple("max_layer_height", "max_layer_height")
    
    # Perimeter/wall settings
    registry.register_simple("perimeters", "wall_loops")
    registry.register_simple("perimeter_speed", "inner_wall_speed")
    registry.register_simple("external_perimeter_speed", "outer_wall_speed")
    registry.register_simple("perimeter_acceleration", "inner_wall_acceleration")
    registry.register_simple("external_perimeter_acceleration", "outer_wall_acceleration")  
    
    # Infill settings
    registry.register_simple("fill_density", "sparse_infill_density")
    registry.register_simple("fill_pattern", "sparse_infill_pattern", 
                           lambda x: convert_fill_pattern(x))
    registry.register_simple("fill_angle", "infill_direction")
    registry.register_simple("infill_speed", "sparse_infill_speed")
    registry.register_simple("solid_infill_speed", "internal_solid_infill_speed")
    registry.register_simple("infill_acceleration", "sparse_infill_acceleration")
    registry.register_simple("solid_infill_acceleration", "internal_solid_infill_acceleration")
    registry.register_simple("infill_every_layers", "infill_combination", lambda x: "0" if x == "1" else "1")
    registry.register_simple("infill_only_where_needed", "minimum_sparse_infill_area",
                           lambda x: "15" if x == "1" else "0")
    registry.register_simple("infill_overlap", "infill_wall_overlap")
    
    # Top/bottom settings
    registry.register_simple("top_solid_layers", "top_shell_layers")
    registry.register_simple("bottom_solid_layers", "bottom_shell_layers")  
    registry.register_simple("top_solid_infill_speed", "top_surface_speed")
    registry.register_simple("top_solid_infill_acceleration", "top_surface_acceleration")
    registry.register_simple("top_fill_pattern", "top_surface_pattern",
                           lambda x: convert_top_pattern(x))
    registry.register_simple("bottom_fill_pattern", "bottom_surface_pattern",
                           lambda x: convert_bottom_pattern(x))
    registry.register_simple("top_solid_min_thickness", "top_shell_thickness")
    registry.register_simple("bottom_solid_min_thickness", "bottom_shell_thickness")
    
    # Speed settings
    registry.register_simple("travel_speed", "travel_speed")
    registry.register_simple("first_layer_speed", "initial_layer_speed")
    registry.register_simple("bridge_speed", "bridge_speed")
    registry.register_simple("gap_fill_speed", "gap_infill_speed")
    
    # Ignore settings without OrcaSlicer equivalents
    registry.register_ignore("max_print_speed")  # Not used in OrcaSlicer

    # non supported keys
    registry.register_ignore("print_settings_id")  
    registry.register_ignore("adaptive_layer_height")
    registry.register_ignore("tree_support_with_infill")
    registry.register_ignore("tree_support_branch_diameter_double_wall")
    
    # Acceleration settings
    registry.register_simple("default_acceleration", "default_acceleration")
    registry.register_simple("first_layer_acceleration", "initial_layer_acceleration")
    registry.register_simple("bridge_acceleration", "bridge_acceleration")
    registry.register_simple("travel_acceleration", "travel_acceleration")
    
    # Extrusion width settings
    registry.register_simple("extrusion_width", "line_width")
    registry.register_simple("first_layer_extrusion_width", "initial_layer_line_width")
    registry.register_simple("perimeter_extrusion_width", "inner_wall_line_width")
    registry.register_simple("external_perimeter_extrusion_width", "outer_wall_line_width")
    registry.register_simple("infill_extrusion_width", "sparse_infill_line_width")
    registry.register_simple("solid_infill_extrusion_width", "internal_solid_infill_line_width")
    registry.register_simple("top_infill_extrusion_width", "top_surface_line_width")
    
    # Support settings
    # NOTE: Prusa enables support by default, taking liberty here to disable it to match other profiles
    registry.register_simple("support_material", "enable_support", lambda _: "0") 
    registry.register_simple("support_material_speed", "support_speed")
    registry.register_simple("support_material_threshold", "support_threshold_angle")
    registry.register_simple("support_material_pattern", "support_base_pattern",
                           lambda x: convert_support_pattern(x))
    registry.register_simple("support_material_spacing", "support_base_pattern_spacing")
    registry.register_simple("support_material_angle", "support_angle")  
    registry.register_simple("support_material_interface_layers", "support_interface_top_layers")
    registry.register_simple("support_material_interface_spacing", "support_interface_spacing")
    registry.register_simple("support_material_interface_speed", "support_interface_speed")
    registry.register_simple("support_material_buildplate_only", "support_on_build_plate_only")
    registry.register_simple("support_material_xy_spacing", "support_object_xy_distance",
                           lambda x: convert_percentage_to_absolute(x, 0.35)) # TODO: use nozzle size
    registry.register_simple("support_material_contact_distance", "support_top_z_distance")
    registry.register_simple("support_material_contact_distance", "support_bottom_z_distance")
    registry.register_simple("raft_contact_distance", "raft_contact_distance") 
    registry.register_simple("support_material_extrusion_width", "support_line_width")
    
    # Ignore support settings without OrcaSlicer equivalents
    registry.register_ignore("support_material_synchronize_layers")  # Not used in OrcaSlicer
    
    # Skirt/brim settings
    registry.register_simple("skirts", "skirt_loops")
    registry.register_simple("skirt_distance", "skirt_distance")
    registry.register_simple("skirt_height", "skirt_height")
    registry.register_simple("min_skirt_length", "min_skirt_length")
    registry.register_simple("brim_width", "brim_width")
    registry.register_simple("brim_separation", "brim_object_gap")
    
    # Other settings
    registry.register_simple("seam_position", "seam_position")
    registry.register_simple("spiral_vase", "spiral_mode")
    registry.register_simple("gcode_resolution", "resolution")
    registry.register_simple("xy_size_compensation", "xy_contour_compensation")
    registry.register_simple("elefant_foot_compensation", "elefant_foot_compensation")
    registry.register_simple("overhangs", "detect_overhang_wall")
    registry.register_simple("thin_walls", "detect_thin_wall")
    registry.register_simple("thick_bridges", "thick_bridges")
    registry.register_simple("bridge_flow_ratio", "bridge_flow")
    registry.register_simple("raft_layers", "raft_layers")
    registry.register_simple("complete_objects", "print_sequence",
                           lambda x: "by object" if x == "1" else "by layer")
    registry.register_simple("output_filename_format", "filename_format")
    registry.register_simple("dont_support_bridges", "bridge_no_support")
    registry.register_simple("avoid_crossing_perimeters", "reduce_crossing_wall")
    registry.register_simple("arc_fitting", "enable_arc_fitting",
                           lambda x: "1" if x == "emit_center" else "0")
    
    # Wipe tower (prime tower) settings
    registry.register_simple("wipe_tower", "enable_prime_tower")
    registry.register_simple("wipe_tower_width", "prime_tower_width")
    registry.register_simple("wipe_tower_cone_angle", "wipe_tower_cone_angle")
    registry.register_simple("wipe_tower_extra_spacing", "wipe_tower_extra_spacing")
    registry.register_simple("wipe_tower_rotation_angle", "wipe_tower_rotation_angle")
    
    # Additional support settings
    registry.register_simple("support_material_bottom_interface_layers", "support_interface_bottom_layers")
    registry.register_simple("support_material_enforce_layers", "enforce_support_layers")
    registry.register_simple("support_material_style", "support_style",
                           lambda x: convert_support_style(x))
    registry.register_simple("support_material_interface_pattern", "support_interface_pattern",
                           lambda x: convert_support_pattern(x))
    registry.register_simple("support_tree_angle_slow", "tree_support_angle_slow")
    registry.register_simple("support_tree_branch_diameter_angle", "tree_support_branch_diameter_angle")
    registry.register_simple("support_tree_tip_diameter", "tree_support_tip_diameter")
    registry.register_simple("support_tree_top_rate", "tree_support_top_rate")
    
    # Advanced settings
    registry.register_simple("gcode_comments", "gcode_comments")
    registry.register_simple("gcode_label_objects", "gcode_label_objects", 
                           lambda x: "1" if x == "firmware" else "0")
    registry.register_simple("infill_anchor", "infill_anchor")
    registry.register_simple("infill_anchor_max", "infill_anchor_max")
    registry.register_simple("interface_shells", "interface_shells")
    registry.register_simple("ooze_prevention", "ooze_prevention")
    registry.register_simple("standby_temperature_delta", "standby_temperature_delta")
    registry.register_simple("external_perimeters_first", "is_infill_first",
                           lambda x: "0" if x == "1" else "1")
    registry.register_simple("only_retract_when_crossing_perimeters", "reduce_infill_retraction",
                           lambda x: "1" if x == "1" else "0")
    
    # Raft settings
    registry.register_simple("raft_first_layer_density", "raft_first_layer_density")
    registry.register_simple("raft_first_layer_expansion", "raft_first_layer_expansion")
    
    # Bridge settings  
    registry.register_simple("bridge_angle", "bridge_angle")
    
    # Speed modifiers
    registry.register_simple("first_layer_infill_speed", "initial_layer_infill_speed")
    registry.register_simple("small_perimeter_speed", "small_perimeter_speed")
    
    # Overhang speeds (dynamic)
    registry.register_simple("overhang_speed_0", "overhang_1_4_speed")
    registry.register_simple("overhang_speed_1", "overhang_2_4_speed")
    registry.register_simple("overhang_speed_2", "overhang_3_4_speed")
    registry.register_simple("overhang_speed_3", "overhang_4_4_speed")

    # TODO: convert to compatible_printers
    registry.register_simple("compatible_printers_condition", "compatible_printers_condition", lambda x: convert_printer_model_condition(x))
    
    return registry


def create_printer_registry():
    """Create registry for printer profile settings."""
    registry = ConverterRegistry()
    
    # Basic printer info
    registry.register_simple("printer_model", "printer_model")
    registry.register_simple("printer_variant", "printer_variant")
    registry.register_simple("nozzle_diameter", "nozzle_diameter",
                           lambda x: [x] if not isinstance(x, list) else x)
    registry.register_simple("bed_shape", "printable_area",
                           lambda x: convert_bed_shape(x))
    registry.register_simple("max_print_height", "printable_height")
    
    # Machine limits (convert to arrays)
    registry.register_simple("machine_max_acceleration_x", "machine_max_acceleration_x",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_acceleration_y", "machine_max_acceleration_y",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_acceleration_z", "machine_max_acceleration_z",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_acceleration_e", "machine_max_acceleration_e",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_acceleration_extruding", "machine_max_acceleration_extruding",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_acceleration_retracting", "machine_max_acceleration_retracting",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_acceleration_travel", "machine_max_acceleration_travel",
                           lambda x: convert_to_array(x))
    
    registry.register_simple("machine_max_feedrate_x", "machine_max_speed_x",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_feedrate_y", "machine_max_speed_y",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_feedrate_z", "machine_max_speed_z",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_feedrate_e", "machine_max_speed_e",
                           lambda x: convert_to_array(x))
    
    registry.register_simple("machine_max_jerk_x", "machine_max_jerk_x",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_jerk_y", "machine_max_jerk_y",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_jerk_z", "machine_max_jerk_z",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_max_jerk_e", "machine_max_jerk_e",
                           lambda x: convert_to_array(x))
    
    registry.register_simple("machine_min_extruding_rate", "machine_min_extruding_rate",
                           lambda x: convert_to_array(x))
    registry.register_simple("machine_min_travel_rate", "machine_min_travel_rate",
                           lambda x: convert_to_array(x))
    
    # Retraction settings
    registry.register_simple("retract_length", "retraction_length")
    registry.register_simple("retract_speed", "retraction_speed")
    registry.register_simple("deretract_speed", "deretraction_speed")
    registry.register_simple("retract_before_travel", "retraction_minimum_travel")
    registry.register_simple("retract_lift", "z_hop")
    registry.register_simple("retract_lift_above", "retract_lift_above")
    registry.register_simple("retract_lift_below", "retract_lift_below")
    registry.register_simple("retract_layer_change", "retract_when_changing_layer")
    registry.register_simple("retract_before_wipe", "retract_before_wipe")
    registry.register_simple("wipe", "wipe")
    
    # G-code settings
    registry.register_simple("gcode_flavor", "gcode_flavor")
    registry.register_simple("start_gcode", "machine_start_gcode",
                           lambda x: [x] if isinstance(x, str) else x)
    registry.register_simple("end_gcode", "machine_end_gcode",
                           lambda x: [x] if isinstance(x, str) else x)
    registry.register_simple("before_layer_gcode", "before_layer_change_gcode",
                           lambda x: [x] if isinstance(x, str) else x)
    registry.register_simple("layer_gcode", "layer_change_gcode",
                           lambda x: [x] if isinstance(x, str) else x)
    registry.register_simple("color_change_gcode", "change_filament_gcode",
                           lambda x: [x] if isinstance(x, str) else x)
    registry.register_simple("pause_print_gcode", "machine_pause_gcode")
    
    # Other printer settings
    registry.register_simple("use_relative_e_distances", "use_relative_e_distances")
    registry.register_simple("extruder_offset", "extruder_offset")
    registry.register_simple("extruder_colour", "extruder_colour")
    registry.register_simple("single_extruder_multi_material", "single_extruder_multi_material")
    registry.register_simple("thumbnails", "thumbnails",
                           lambda x: convert_thumbnails(x))
    registry.register_simple("printer_notes", "printer_notes",
                           lambda x: [x] if isinstance(x, str) else x)
    registry.register_simple("extruder_clearance_radius", "extruder_clearance_radius")
    registry.register_simple("extruder_clearance_height", "extruder_clearance_height_to_rod")
    
    # Emit machine limits
    registry.register_simple("machine_limits_usage", "emit_machine_limits_to_gcode",
                           lambda x: "1" if x == "emit_to_gcode" else "0")
    
    return registry


def create_filament_registry():
    """Create registry for filament profile settings."""
    registry = ConverterRegistry()
    
    # Basic filament info
    registry.register_simple("filament_type", "filament_type")
    registry.register_simple("filament_vendor", "filament_vendor")
    registry.register_simple("filament_cost", "filament_cost")
    registry.register_simple("filament_density", "filament_density")
    registry.register_simple("filament_diameter", "filament_diameter")
    
    # Temperature settings
    # Note: chamber_temperature and chamber_minimal_temperature are mutually exclusive in PrusaSlicer
    registry.register_mutually_exclusive("chamber_temperature", "chamber_temperature", "chamber_minimal_temperature")
    registry.register_simple("first_layer_temperature", "nozzle_temperature_initial_layer")
    registry.register_simple("temperature", "nozzle_temperature")
    registry.register_simple("first_layer_bed_temperature", "hot_plate_temp_initial_layer")
    registry.register_simple("bed_temperature", "hot_plate_temp")
    registry.register_simple("chamber_temperature", "chamber_temperature")
    registry.register_simple("chamber_minimal_temperature", "chamber_temperature")
    
    # Cooling settings
    registry.register_simple("fan_always_on", "fan_always_on")
    registry.register_simple("min_fan_speed", "fan_min_speed")
    registry.register_simple("max_fan_speed", "fan_max_speed")
    registry.register_simple("bridge_fan_speed", "bridge_fan_speed")
    registry.register_simple("disable_fan_first_layers", "close_fan_the_first_x_layers")
    registry.register_simple("full_fan_speed_layer", "full_fan_speed_layer")
    registry.register_simple("fan_below_layer_time", "fan_cooling_layer_time")
    registry.register_simple("slowdown_below_layer_time", "slow_down_layer_time")
    registry.register_simple("min_print_speed", "slow_down_min_speed")
    registry.register_simple("filament_cooling_moves", "filament_cooling_moves")
    registry.register_simple("filament_cooling_initial_speed", "filament_cooling_initial_speed")
    registry.register_simple("filament_cooling_final_speed", "filament_cooling_final_speed")
    
    # Retraction settings
    registry.register_simple("filament_retract_length", "filament_retraction_length")
    registry.register_simple("filament_retract_speed", "filament_retraction_speed")
    registry.register_simple("filament_deretract_speed", "filament_deretraction_speed")
    registry.register_simple("filament_retract_lift", "filament_retract_lift_below")
    registry.register_simple("filament_retract_restart_extra", "filament_retract_restart_extra")
    registry.register_simple("filament_retract_before_wipe", "filament_retract_before_wipe")
    registry.register_simple("filament_retract_before_travel", "filament_retraction_minimum_travel")
    registry.register_simple("filament_retract_layer_change", "filament_retract_when_changing_layer")
    registry.register_simple("filament_wipe", "wipe")
    
    # Loading/Unloading settings
    registry.register_simple("filament_loading_speed", "filament_loading_speed")
    registry.register_simple("filament_loading_speed_start", "filament_loading_speed_start")
    registry.register_simple("filament_unloading_speed", "filament_unloading_speed")
    registry.register_simple("filament_unloading_speed_start", "filament_unloading_speed_start")
    registry.register_simple("filament_load_time", "filament_load_time")
    registry.register_simple("filament_unload_time", "filament_unload_time")
    
    # MMU/Toolchange settings
    registry.register_simple("filament_minimal_purge_on_wipe_tower", "filament_minimal_purge_on_wipe_tower")
    registry.register_simple("filament_multitool_ramming", "filament_multitool_ramming")
    registry.register_simple("filament_multitool_ramming_flow", "filament_multitool_ramming_flow")
    registry.register_simple("filament_multitool_ramming_volume", "filament_multitool_ramming_volume")
    registry.register_simple("filament_ramming_parameters", "filament_ramming_parameters")
    registry.register_simple("filament_stamping_distance", "filament_stamping_distance")
    registry.register_simple("filament_stamping_loading_speed", "filament_stamping_loading_speed")
    
    # Filament physical properties
    registry.register_simple("filament_spool_weight", "filament_spool_weight",
                           lambda x: str(x) if x else "0")
    registry.register_simple("filament_colour", "filament_colour",
                           lambda x: [x] if isinstance(x, str) else x)
    
    # Filament properties
    registry.register_simple("filament_notes", "filament_notes")
    registry.register_simple("filament_max_volumetric_speed", "filament_max_volumetric_speed")
    registry.register_simple("extrusion_multiplier", "filament_flow_ratio")
    registry.register_simple("filament_soluble", "filament_soluble")
    
    # G-code
    registry.register_simple("start_filament_gcode", "filament_start_gcode",
                           lambda x: [x] if isinstance(x, str) else x)
    registry.register_simple("end_filament_gcode", "filament_end_gcode",
                           lambda x: [x] if isinstance(x, str) else x)
    
    # Compatible printers
    # TODO - handle properly
    registry.register_simple("compatible_printers", "compatible_printers")
    registry.register_simple("compatible_printers_condition", "compatible_printers_condition")

    
    return registry


# Helper functions for value transformations

def is_numeric(value):
    """Check if a value is numeric (not a percentage or special string)."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except:
            return False
    return False


def convert_to_percentage(value, nozzle_diameter=0.4):
    """Convert absolute extrusion width to percentage of nozzle diameter."""
    if isinstance(value, str) and '%' in value:
        return value
    try:
        width = float(value)
        # Convert to percentage of nozzle diameter
        percentage = (width / nozzle_diameter) * 100
        return f"{percentage:.2f}%"
    except:
        return value


def convert_percentage_to_absolute(percentage_str, default_value):
    """Convert percentage string to absolute value."""
    if isinstance(percentage_str, str) and '%' in percentage_str:
        # For now, return a sensible default - this would need context
        return str(default_value)
    return percentage_str


def convert_fill_pattern(prusa_pattern):
    """Convert PrusaSlicer fill pattern to OrcaSlicer."""
    pattern_map = {
        "rectilinear": "rectilinear",
        "grid": "grid",
        "triangles": "triangles",
        "stars": "stars",
        "cubic": "cubic",
        "gyroid": "gyroid",
        "honeycomb": "honeycomb",
        "adaptivecubic": "adaptive-cubic",
        "supportcubic": "support-cubic",
        "3dhoneycomb": "3dhoneycomb",
        "hilbertcurve": "hilbertcurve",
        "archimedeanchords": "archimedeanchords",
        "octagramspiral": "octagramspiral",
        "crosshatch": "crosshatch"
    }
    return pattern_map.get(prusa_pattern.lower(), prusa_pattern)


def convert_top_pattern(prusa_pattern):
    """Convert PrusaSlicer top fill pattern to OrcaSlicer."""
    pattern_map = {
        "rectilinear": "rectilinear",
        "monotonic": "monotonic",
        "monotoniclines": "monotonicline",
        "alignedrectilinear": "rectilinear",
        "concentric": "concentric",
        "hilbertcurve": "hilbertcurve",
        "archimedeanchords": "archimedeanchords",
        "octagramspiral": "octagramspiral"
    }
    return pattern_map.get(prusa_pattern.lower(), "monotonicline")


def convert_bottom_pattern(prusa_pattern):
    """Convert PrusaSlicer bottom fill pattern to OrcaSlicer."""
    pattern_map = {
        "rectilinear": "rectilinear",
        "monotonic": "monotonic",
        "monotoniclines": "monotonic",
        "alignedrectilinear": "rectilinear",
        "concentric": "concentric",
        "hilbertcurve": "hilbertcurve",
        "archimedeanchords": "archimedeanchords",
        "octagramspiral": "octagramspiral"
    }
    return pattern_map.get(prusa_pattern.lower(), "monotonic")


def convert_support_style(prusa_style):
    """Convert PrusaSlicer support style to OrcaSlicer."""
    style_map = {
        "grid": "snug",
        "snug": "snug",
        "tree": "tree",
        "organic": "tree"
    }
    return style_map.get(prusa_style.lower(), "snug")


def convert_support_pattern(prusa_pattern):
    """Convert PrusaSlicer support pattern to OrcaSlicer."""
    pattern_map = {
        "rectilinear": "rectilinear",
        "rectilinear-grid": "grid",
        "honeycomb": "honeycomb",
        "lightning": "lightning",
    }
    return pattern_map.get(prusa_pattern.lower(), "auto")


def convert_bed_shape(bed_shape_str):
    """Convert PrusaSlicer bed shape to OrcaSlicer printable area."""
    # bed_shape format: "0x0,250x0,250x220,0x220"
    # OrcaSlicer uses same format
    if isinstance(bed_shape_str, list):
        return bed_shape_str
    return bed_shape_str.split(',')


def convert_thumbnails(thumbnails_str):
    """Convert PrusaSlicer thumbnail format to OrcaSlicer."""
    # Format is similar, might just need list conversion
    if isinstance(thumbnails_str, list):
        return thumbnails_str
    return thumbnails_str.split(',')


def convert_to_array(value):
    """Convert comma-separated values to array of strings."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        # Split by comma and strip whitespace
        return [v.strip() for v in value.split(',')]
    # Single numeric value - convert to single-element array
    return [str(value)]


def convert_printer_model_condition(condition_str):
    """Convert PrusaSlicer printer model condition to OrcaSlicer format."""
    # Example conversion: "contains('MK3')" -> "MK3"
    if "contains(" in condition_str:
        start = condition_str.find("contains(") + len("contains(")
        end = condition_str.find(")", start)
        model = condition_str[start:end].strip("'\"")
        return model
    return condition_str