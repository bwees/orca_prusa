"""
Profile converters for printer, print, and filament profiles.
"""
import json
import os
import re
from typing import Dict, List, Any, Tuple
from converters.mapping_registry import (
    create_print_registry,
    create_printer_registry,
    create_filament_registry
)
from converters.orca_defaults import apply_defaults


def normalize_printer_name(name: str) -> str:
    """
    Normalize printer names to OrcaSlicer format.
    COREONE -> CORE One
    COREONEL -> CORE One L
    
    Also fixes HF variant naming:
    @COREONE HF0.4 -> @CORE One HF 0.4
    """
    # Replace COREONEL with CORE One L (must be done first to avoid double replacement)
    name = re.sub(r'\bCOREONEL\b', 'CORE One L', name)
    # Replace COREONE with CORE One
    name = re.sub(r'\bCOREONE\b', 'CORE One', name)
    
    # Fix HF variant naming: "HF0.4" -> "HF 0.4"
    name = re.sub(r'\bHF(\d)', r'HF \1', name)
    
    return name


class PrinterProfileConverter:
    """Converts PrusaSlicer printer profiles to OrcaSlicer machine profiles."""
    
    def __init__(self):
        self.registry = create_printer_registry()
        self.needs_conversion = []
        
    def convert_printer_model(self, model_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Convert a printer_model section to machine_model and machine profiles.
        Returns (machine_model, [machine_variants])
        
        For HF nozzle variants, creates separate printer models.
        """
        name = normalize_printer_name(model_data.get('name', 'Unknown'))
        variants = model_data.get('variants', '').split(';')
        variants = [v.strip() for v in variants if v.strip()]
        
        # Determine if this printer has HF variants
        hf_variants = [v for v in variants if v.startswith('HF')]
        standard_variants = [v for v in variants if not v.startswith('HF')]
        
        machine_models = []
        
        # Create standard model if there are standard variants
        if standard_variants:
            machine_model = {
                "type": "machine_model",
                "name": name,
                "bed_model": model_data.get('bed_model', ''),
                "bed_texture": model_data.get('bed_texture', ''),
                "default_materials": ';'.join(model_data.get('default_materials', [])),
                "family": "Prusa",
                "hotend_model": "",
                "machine_tech": "FFF",
                "model_id": self._generate_model_id(name),
                "nozzle_diameter": ';'.join(standard_variants)
            }
            machine_models.append(machine_model)
        
        # Create HF model if there are HF variants
        if hf_variants:
            hf_name = f"{name} HF"
            # Remove HF prefix from variants
            hf_nozzle_sizes = [v.replace('HF', '') for v in hf_variants]
            
            machine_model_hf = {
                "type": "machine_model",
                "name": hf_name,
                "bed_model": model_data.get('bed_model', ''),
                "bed_texture": model_data.get('bed_texture', ''),
                "default_materials": ';'.join(model_data.get('default_materials', [])),
                "family": "Prusa",
                "hotend_model": "",
                "machine_tech": "FFF",
                "model_id": self._generate_model_id(hf_name),
                "nozzle_diameter": ';'.join(hf_nozzle_sizes)
            }
            machine_models.append(machine_model_hf)
        
        return machine_models
    
    def convert_printer_variant(self, printer_data: Dict[str, Any], 
                               parent_name: str = None, resolve_inheritance: bool = True) -> Dict[str, Any]:
        """
        Convert a printer section to a machine JSON profile.
        
        Args:
            printer_data: The printer profile data
            parent_name: The base printer name
            resolve_inheritance: If True, creates concrete profile with all inherited settings
        """
        name = normalize_printer_name(printer_data.get('name', 'Unknown'))
        variant = printer_data.get('printer_variant', '0.4')
        model = printer_data.get('printer_model', '')
        is_hf = printer_data.get('nozzle_high_flow') == '1'
        
        # Normalize parent name
        if parent_name:
            parent_name = normalize_printer_name(parent_name)
        
        # Determine inheritance and printer model
        if is_hf:
            printer_model_name = f"{parent_name} HF" if parent_name else model
            inherits = "fdm_machine_common"
        else:
            printer_model_name = parent_name or model
            # Non-HF variants inherit from HF variant of same nozzle size if it exists
            hf_variant_name = f"{parent_name} HF {variant} nozzle" if parent_name else f"{model} HF {variant} nozzle"
            inherits = hf_variant_name
        
        # Build the base machine profile
        machine = {
            "type": "machine",
            "name": name,
            "from": "system",
            "instantiation": "true",
            "printer_model": printer_model_name,
            "printer_variant": variant
        }
        
        # If resolving inheritance, apply defaults first, then converted settings
        if resolve_inheritance:
            # Apply OrcaSlicer defaults for base settings
            machine = apply_defaults(machine, 'machine', self.registry.ignored_keys)
        
        # Convert and add this profile's settings (overrides defaults)
        converted, needs_conv = self.registry.convert_dict(printer_data)
        self.needs_conversion.extend(needs_conv)
        machine.update(converted)
        
        # Ensure lists for gcode fields
        for gcode_field in ["machine_start_gcode", "machine_end_gcode", 
                           "before_layer_change_gcode", "layer_change_gcode",
                           "change_filament_gcode"]:
            if gcode_field in machine and isinstance(machine[gcode_field], str):
                machine[gcode_field] = [machine[gcode_field]]
        
        # If not resolving inheritance, apply defaults after to fill any gaps
        if not resolve_inheritance:
            machine = apply_defaults(machine, 'machine', self.registry.ignored_keys)
        
        return machine
        # Apply OrcaSlicer defaults for any missing settings (filter out ignored keys)
        machine = apply_defaults(machine, 'machine', self.registry.ignored_keys)
        
        return machine
    
    def _generate_model_id(self, name: str) -> str:
        """Generate a model_id from the printer name."""
        # Replace spaces and special chars with underscores
        model_id = name.replace(" ", "_").replace("-", "_")
        # Add Prusa_ prefix if not already there
        if not model_id.startswith("Prusa_"):
            model_id = f"Prusa_{model_id}"
        return model_id


class PrintProfileConverter:
    """Converts PrusaSlicer print profiles to OrcaSlicer process profiles."""
    
    def __init__(self):
        self.registry = create_print_registry()
        self.needs_conversion = []
        self.all_profiles = {}  # Cache of all print profiles
        
    def set_all_profiles(self, profiles: Dict[str, Any]):
        """Set reference to all profiles for inheritance resolution."""
        self.all_profiles = {p.get('name', ''): p for p in profiles}
        
    def _resolve_inherited_settings(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve and merge settings from all parent profiles."""
        merged = {}
        
        if 'inherits' not in profile_data:
            return merged
        
        inherits_str = profile_data['inherits']
        parents = [p.strip() for p in inherits_str.split(';')]
        
        # Process parents in order (first parent's settings take precedence)
        for parent_name in parents:
            if parent_name in self.all_profiles:
                parent = self.all_profiles[parent_name]
                # Recursively get parent's inherited settings first
                parent_settings = self._resolve_inherited_settings(parent)
                merged.update(parent_settings)
                # Then apply parent's own settings
                parent_converted, _ = self.registry.convert_dict(parent)
                merged.update(parent_converted)
        
        return merged
        
    def convert_print_profile(self, print_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a print profile section to an OrcaSlicer process profile."""
        name = normalize_printer_name(print_data.get('name', 'Unknown'))
        
        # Build the process profile
        process = {
            "type": "process",
            "name": name,
            "from": "system",
            "instantiation": "true" if not name.startswith('*') else "false"
        }
        
        # Handle inheritance - OrcaSlicer only supports single parent
        concrete_parent = None
        if 'inherits' in print_data:
            inherits_str = print_data['inherits']
            parents = [p.strip() for p in inherits_str.split(';')]
            
            # Find first concrete parent for inheritance
            concrete_parents = [p for p in parents if not p.startswith('*')]
            if concrete_parents:
                concrete_parent = normalize_printer_name(concrete_parents[0])
                process['inherits'] = concrete_parent
            elif parents:
                # All parents are abstract, use first one
                concrete_parent = normalize_printer_name(parents[0])
                process['inherits'] = concrete_parent
            
            # Get inherited settings from ALL parents (including abstract ones)
            inherited_settings = self._resolve_inherited_settings(print_data)
            process.update(inherited_settings)
        
        # Convert and apply this profile's own settings (overrides inherited)
        converted, needs_conv = self.registry.convert_dict(print_data)
        self.needs_conversion.extend(needs_conv)
        process.update(converted)
        
        # Apply OrcaSlicer defaults for any missing settings (filter out ignored keys)
        process = apply_defaults(process, 'process', self.registry.ignored_keys)
        
        return process


class FilamentProfileConverter:
    """Converts PrusaSlicer filament profiles to OrcaSlicer filament profiles."""
    
    def __init__(self):
        self.registry = create_filament_registry()
        self.needs_conversion = []
        self.all_profiles = {}  # Cache of all filament profiles
        
    def set_all_profiles(self, profiles: Dict[str, Any]):
        """Set reference to all profiles for inheritance resolution."""
        self.all_profiles = {p.get('name', ''): p for p in profiles}
        
    def _resolve_inherited_settings(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve and merge settings from all parent profiles."""
        merged = {}
        
        if 'inherits' not in profile_data:
            return merged
        
        inherits_str = profile_data['inherits']
        parents = [p.strip() for p in inherits_str.split(';')]
        
        # Process parents in order (first parent's settings take precedence)
        for parent_name in parents:
            if parent_name in self.all_profiles:
                parent = self.all_profiles[parent_name]
                # Recursively get parent's inherited settings first
                parent_settings = self._resolve_inherited_settings(parent)
                merged.update(parent_settings)
                # Then apply parent's own settings
                parent_converted, _ = self.registry.convert_dict(parent)
                merged.update(parent_converted)
        
        return merged
        
    def convert_filament_profile(self, filament_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a filament profile section to an OrcaSlicer filament profile."""
        name = normalize_printer_name(filament_data.get('name', 'Unknown'))
        
        # Build the filament profile
        filament = {
            "type": "filament",
            "name": name,
            "from": "system",
            "instantiation": "true" if not name.startswith('*') else "false"
        }
        
        # Handle inheritance - OrcaSlicer only supports single parent
        concrete_parent = None
        if 'inherits' in filament_data:
            inherits_str = filament_data['inherits']
            parents = [p.strip() for p in inherits_str.split(';')]
            
            # Find first concrete parent for inheritance
            concrete_parents = [p for p in parents if not p.startswith('*')]
            if concrete_parents:
                concrete_parent = normalize_printer_name(concrete_parents[0])
                filament['inherits'] = concrete_parent
            elif parents:
                # All parents are abstract, use first one
                concrete_parent = normalize_printer_name(parents[0])
                filament['inherits'] = concrete_parent
            
            # Get inherited settings from ALL parents (including abstract ones)
            inherited_settings = self._resolve_inherited_settings(filament_data)
            filament.update(inherited_settings)
        
        # Convert and apply this profile's own settings (overrides inherited)
        converted, needs_conv = self.registry.convert_dict(filament_data)
        self.needs_conversion.extend(needs_conv)
        filament.update(converted)
        
        # Ensure temperature values are in lists
        for temp_field in ["nozzle_temperature", "nozzle_temperature_initial_layer",
                          "hot_plate_temp", "hot_plate_temp_initial_layer",
                          "chamber_temperature"]:
            if temp_field in filament:
                value = filament[temp_field]
                if not isinstance(value, list):
                    filament[temp_field] = [str(value)]
        
        # Ensure gcode fields are lists
        for gcode_field in ["filament_start_gcode", "filament_end_gcode"]:
            if gcode_field in filament and isinstance(filament[gcode_field], str):
                filament[gcode_field] = [filament[gcode_field]]
        
        # Apply OrcaSlicer defaults for any missing settings (filter out ignored keys)
        filament = apply_defaults(filament, 'filament', self.registry.ignored_keys)
        
        return filament


def save_json_profile(profile: Dict[str, Any], output_dir: str, filename: str):
    """Save a profile as a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=4, ensure_ascii=False)
    
    return filepath
