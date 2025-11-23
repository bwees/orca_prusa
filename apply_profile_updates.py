#!/usr/bin/env python3
"""
Apply PrusaSlicer profile changes to OrcaSlicer JSON profiles.
Uses the comparison data to update existing JSON profiles with mapped settings.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional, List
from compare_coreone_profiles import ProfileParser, ProfileComparer


# Import the mapping registry
import sys
sys.path.insert(0, str(Path(__file__).parent))
from converters.mapping_registry import create_print_registry


def prusa_profile_name_to_orca_filename(prusa_name: str) -> str:
    """
    Convert PrusaSlicer profile name to OrcaSlicer filename format.
    
    Examples:
        print:0.05mm DETAIL @COREONE 0.25 -> 0.05mm DETAIL @CORE One 0.25.json
        print:0.15mm SPEED @COREONE HF0.4 -> 0.15mm SPEED @CORE One HF 0.4.json
    """
    # Remove the 'print:' prefix
    name = prusa_name.replace('print:', '')
    
    # Replace @COREONE with @CORE One
    name = name.replace('@COREONE', '@CORE One')
    name = name.replace('@COREONEL', '@CORE One L')
    
    # Handle HF notation: HF0.4 -> HF 0.4
    name = re.sub(r'HF(\d)', r'HF \1', name)
    
    # Add .json extension
    return f"{name}.json"


def convert_prusa_setting_to_orca(registry, key: str, value: str) -> Optional[List[tuple]]:
    """
    Convert a PrusaSlicer setting to OrcaSlicer format using the mapping registry.
    
    Returns:
        List of (orca_key, orca_value) tuples or None if setting should be ignored
    """
    # Try to convert using the registry
    result = registry.convert_setting(key, value)
    
    if result.settings:
        # Return all converted settings
        return list(result.settings.items())
    elif result.needs_manual_conversion:
        # Setting not in registry
        print(f"  Warning: Unknown setting '{key}', skipping")
        return None
    else:
        # Ignored setting
        return None


def apply_changes_to_profile(profile_path: Path, changes: Dict, registry) -> bool:
    """
    Apply changes to a single JSON profile file.
    
    Returns:
        True if changes were applied, False otherwise
    """
    if not profile_path.exists():
        print(f"  Profile not found: {profile_path}")
        return False
    
    # Load the JSON profile
    with open(profile_path, 'r') as f:
        profile_data = json.load(f)
    
    changes_made = False
    
    # Process additions
    for key, info in changes.get('added', {}).items():
        if not info.get('direct'):
            continue
        
        value = info['value']
        converted = convert_prusa_setting_to_orca(registry, key, value)
        
        if converted:
            for orca_key, orca_value in converted:
                profile_data[orca_key] = orca_value
                print(f"    + {orca_key} = {orca_value} (from {key})")
                changes_made = True
    
    # Process modifications
    for key, info in changes.get('modified', {}).items():
        if not info.get('direct'):
            continue
        
        new_value = info['new']
        converted = convert_prusa_setting_to_orca(registry, key, new_value)
        
        if converted:
            for orca_key, orca_value in converted:
                old_orca_value = profile_data.get(orca_key, '(not set)')
                profile_data[orca_key] = orca_value
                print(f"    ~ {orca_key}: {old_orca_value} -> {orca_value} (from {key})")
                changes_made = True
    
    # Process removals
    for key, info in changes.get('removed', {}).items():
        if not info.get('direct'):
            continue
        
        # Convert to Orca key to know what to remove
        converted = convert_prusa_setting_to_orca(registry, key, info['value'])
        
        if converted:
            for orca_key, _ in converted:
                if orca_key in profile_data:
                    removed_value = profile_data.pop(orca_key)
                    print(f"    - {orca_key} = {removed_value} (from {key})")
                    changes_made = True
    
    # Save the modified profile
    if changes_made:
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f, indent=4)
        print(f"  ✓ Saved changes to {profile_path.name}")
    
    return changes_made


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    
    # Input files
    old_ini = script_dir / "new" / "2.2.11.ini"
    new_ini = script_dir / "new" / "2.4.2.ini"
    
    # Output directory
    orca_process_dir = Path("/Users/bwees/Developer/OrcaSlicer/resources/profiles/Prusa/process")
    
    if not orca_process_dir.exists():
        print(f"Error: OrcaSlicer process directory not found: {orca_process_dir}")
        return
    
    print("Parsing profiles...")
    old_parser = ProfileParser(old_ini)
    new_parser = ProfileParser(new_ini)
    
    print("Comparing profiles...")
    comparer = ProfileComparer(old_parser, new_parser)
    comparison = comparer.compare_profiles('print')
    
    # Create the mapping registry
    print("Loading mapping registry...")
    registry = create_print_registry()
    
    print("\n" + "=" * 80)
    print("APPLYING CHANGES TO ORCA SLICER PROFILES")
    print("=" * 80 + "\n")
    
    profiles_updated = 0
    profiles_not_found = []
    
    # Process only profiles with direct changes
    for prusa_profile_name in sorted(comparison['changed_profiles'].keys()):
        changes = comparison['changed_profiles'][prusa_profile_name]
        
        # Skip profiles without direct changes
        if not changes.get('direct_changes'):
            continue
        
        # Convert profile name to OrcaSlicer filename
        orca_filename = prusa_profile_name_to_orca_filename(prusa_profile_name)
        profile_path = orca_process_dir / orca_filename
        
        print(f"\n{prusa_profile_name}")
        print(f"  -> {orca_filename}")
        
        if apply_changes_to_profile(profile_path, changes, registry):
            profiles_updated += 1
        else:
            if not profile_path.exists():
                profiles_not_found.append(orca_filename)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Profiles updated: {profiles_updated}")
    print(f"Profiles not found: {len(profiles_not_found)}")
    
    if profiles_not_found:
        print("\nProfiles not found in orca_existing/process:")
        for filename in profiles_not_found:
            print(f"  - {filename}")
    
    print("\nDone!")


if __name__ == '__main__':
    main()
