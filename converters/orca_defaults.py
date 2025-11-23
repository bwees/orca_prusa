"""
Default values for OrcaSlicer-specific settings that don't have PrusaSlicer equivalents.

These settings are required by OrcaSlicer but may not exist in PrusaSlicer profiles.
You can modify these defaults as needed for your printer/profiles.
"""

# Process (print) profile defaults
PROCESS_DEFAULTS = {
    "setting_id": "GFSA04",

    # Layer and perimeter settings
    "bottom_surface_pattern": "monotonic",
    "wall_generator": "arachne",
    "wall_infill_order": "inner wall/outer wall/infill",
    
    # Brim settings
    "brim_width": "5",
    
    # Draft shield
    "draft_shield": "disabled",
    
    # Overhang settings
    "overhang_1_4_speed": "80%",
    "overhang_4_4_speed": "15",
    "enable_overhang_speed": "1",
    
    # Quality settings
    "min_bead_width": "85%",
    "min_feature_size": "25%",
    "slice_closing_radius": "0.049",
    "slowdown_for_curled_perimeters": "1",
    "resolution": "0",
    
    # Infill settings
    "minimum_sparse_infill_area": "0",
    "infill_anchor": "2",
    "infill_anchor_max": "12",
    
    # Support settings
    "support_type": "normal(auto)",
    "support_interface_loop_pattern": "0",
    "tree_support_branch_angle": "40",
    "tree_support_branch_diameter": "2",
    "tree_support_wall_count": "0",
    "tree_support_with_infill": "0",
    
    # Multi-material settings
    "solid_infill_filament": "1",
    "sparse_infill_filament": "1",
    "wall_filament": "1",
    "support_filament": "0",
    "support_interface_filament": "0",
    
    # Advanced settings
    "exclude_object": "1",
    "reduce_crossing_wall": "0",
    "max_travel_detour_distance": "0",
    "standby_temperature_delta": "-5",
    
    # Ironing settings
    "ironing_type": "no ironing",
    "ironing_flow": "10%",
    "ironing_spacing": "0.15",
    "ironing_speed": "30",
    
    # Raft settings
    "raft_layers": "0",
    "raft_expansion": "1.5",
    
    # Skirt settings
    "skirt_distance": "2",
    "skirt_height": "3",
    
    # Travel settings
    "travel_speed_z": "12",
    
    # Wipe tower settings
    "wipe_tower_no_sparse_layers": "0",
    "prime_tower_width": "60",
    
    # Compensation settings
    "xy_hole_compensation": "0",
    "xy_contour_compensation": "0",
    
    # Print sequence
    "print_sequence": "by layer",
    
    # Spiral vase
    "spiral_mode": "0",
    
    # Settings ID (usually empty)
    "print_settings_id": "",

    # TODO: Not sure if we want to set these jerk settings
    # "default_jerk": "8",
    # "infill_jerk": "8",
    # "initial_layer_jerk": "7",
    # "inner_wall_jerk": "8",
    # "outer_wall_jerk": "7",
    # "top_surface_jerk": "7",
    # "travel_jerk": "8",

    "overhang_reverse": "1",
    "precise_outer_wall": "1",
    "internal_bridge_speed": "50",
}

# Filament profile defaults
FILAMENT_DEFAULTS = {
    # Filament properties
    "filament_is_support": "0",
    "filament_settings_id": "",
    
    # Additional cooling
    "additional_cooling_fan_speed": [],
    "enable_overhang_bridge_fan": "1",
    "fan_speedup_time": "0",
    "fan_speedup_overhangs": "1",
    "fan_kickstart": "0",
    
    # Retraction
    "filament_retract_lift_below": ["0"],
    "filament_retract_lift_above": ["0"],
    
    # Z-hop
    "filament_z_hop": ["0"],
    "filament_z_hop_types": ["Normal Lift"],
    
    # Material properties
    "temperature_vitrification": ["0"],
    
    # Color
    "filament_colour": ["#FFFFFF"],
}

# Machine (printer variant) defaults
MACHINE_DEFAULTS = {
    # Bed settings
    "bed_exclude_area": [],
    "scan_first_layer": "0",
    
    # Auxiliary fan
    "auxiliary_fan": "0",
    
    # Clearances
    "extruder_clearance_height_to_lid": "140",
    "extruder_clearance_height_to_rod": "36",
    "extruder_clearance_radius": "57",
    
    # Parking
    "parking_pos_retraction": "92",
    
    # Retraction defaults (if not specified)
    "retract_length_toolchange": ["0"],
    "retract_restart_extra_toolchange": ["0"],
    
    # Firmware features
    "use_firmware_retraction": "0",
    "use_relative_e_distances": "0",
    
    # G-code
    "scan_first_layer_gcode": "",
    
    # Settings
    "setting_id": "",
    
}

# Machine model defaults
MACHINE_MODEL_DEFAULTS = {
    # Model identification
    "family": "Prusa",
    "machine_tech": "FFF",
    "hotend_model": "",
    
    # Materials (usually empty, populated from printer data)
    "default_materials": [],
    
    # Models and textures (usually empty, populated from printer data)
    "bed_model": "",
    "bed_texture": "",
}


def get_process_defaults():
    """Get default values for process profiles."""
    return PROCESS_DEFAULTS.copy()


def get_filament_defaults():
    """Get default values for filament profiles."""
    return FILAMENT_DEFAULTS.copy()


def get_machine_defaults():
    """Get default values for machine profiles."""
    return MACHINE_DEFAULTS.copy()


def get_machine_model_defaults():
    """Get default values for machine model profiles."""
    return MACHINE_MODEL_DEFAULTS.copy()


def apply_defaults(profile: dict, profile_type: str, ignored_keys: set = None) -> dict:
    """
    Apply default values to a profile for settings that aren't present.
    
    Args:
        profile: The profile dictionary
        profile_type: One of 'process', 'filament', 'machine', 'machine_model'
        ignored_keys: Set of keys to exclude from defaults
    
    Returns:
        Profile with defaults applied
    """
    defaults_map = {
        'process': get_process_defaults,
        'filament': get_filament_defaults,
        'machine': get_machine_defaults,
        'machine_model': get_machine_model_defaults,
    }
    
    if profile_type not in defaults_map:
        return profile
    
    defaults = defaults_map[profile_type]()
    
    # Filter out ignored keys if provided
    if ignored_keys:
        defaults = {k: v for k, v in defaults.items() if k not in ignored_keys}
    
    # Apply defaults only for missing keys
    for key, value in defaults.items():
        if key not in profile:
            profile[key] = value
    
    return profile
