#!/usr/bin/env python3
"""
Profile Differ - Compare converted profiles with OrcaSlicer profiles

This tool compares profiles by resolving all inheritance chains to create
concrete profiles, then shows the differences between them.
"""

import json
import os
import argparse
from typing import Dict, Any, Set, List, Tuple
from pathlib import Path

# Import supported settings
try:
    from presets_supported import print_options, filament_options, machine_limits_options, printer_options
    SUPPORTED_SETTINGS = {
        'process': set(print_options),
        'filament': set(filament_options),
        'machine': set(machine_limits_options + printer_options),
        'machine_model': set(printer_options)
    }
    HAS_SUPPORTED_SETTINGS = True
except ImportError:
    SUPPORTED_SETTINGS = {}
    HAS_SUPPORTED_SETTINGS = False

# Import mapping registries for showing Prusa->Orca mappings
try:
    from converters.mapping_registry import (
        create_print_registry,
        create_printer_registry,
        create_filament_registry
    )
    REGISTRIES = {
        'process': create_print_registry(),
        'filament': create_filament_registry(),
        'machine': create_printer_registry(),
        'machine_model': create_printer_registry()
    }
    HAS_REGISTRIES = True
except ImportError:
    REGISTRIES = {}
    HAS_REGISTRIES = False


class ProfileDiffer:
    """Compare profiles by resolving inheritance and showing differences."""
    
    def __init__(self, converted_dir: str, orca_dir: str, registries: Dict[str, Any] = None):
        """
        Initialize the differ.
        
        Args:
            converted_dir: Directory containing converted profiles
            orca_dir: Directory containing OrcaSlicer profiles
            registries: Optional dict of profile_type -> ConverterRegistry for mapping lookups
        """
        self.converted_dir = Path(converted_dir)
        self.orca_dir = Path(orca_dir)
        self.registries = registries or {}
        
        # Cache for loaded profiles
        self.converted_cache: Dict[str, Dict[str, Any]] = {}
        self.orca_cache: Dict[str, Dict[str, Any]] = {}
    
    def _is_supported(self, profile_type: str, setting_name: str) -> bool:
        """Check if a setting is supported in OrcaSlicer."""
        if not HAS_SUPPORTED_SETTINGS:
            return True  # Assume supported if we don't have the list
        
        supported = SUPPORTED_SETTINGS.get(profile_type, set())
        return setting_name in supported
    
    def _format_setting_name(self, profile_type: str, setting_name: str, show_mapping: bool = True) -> str:
        """Format setting name with mapping info and UNSUPPORTED tag if needed."""
        result = setting_name
        
        # Add mapping information if available
        if show_mapping and profile_type in self.registries:
            registry = self.registries[profile_type]
            prusa_keys = registry.get_reverse_mapping(setting_name)
            if prusa_keys:
                prusa_key_str = ', '.join(prusa_keys)
                result = f"{setting_name} [from: {prusa_key_str}]"
        
        # Add unsupported tag
        if not self._is_supported(profile_type, setting_name):
            result = f"{result} [UNSUPPORTED]"
        
        return result
    
    def load_profile(self, profile_type: str, profile_name: str, is_converted: bool) -> Dict[str, Any]:
        """
        Load a profile from disk.
        
        Args:
            profile_type: Type of profile (process, filament, machine, machine_model)
            profile_name: Name of the profile (without .json extension)
            is_converted: True for converted profiles, False for OrcaSlicer profiles
        
        Returns:
            Profile data as dictionary
        """
        cache = self.converted_cache if is_converted else self.orca_cache
        cache_key = f"{profile_type}/{profile_name}"
        
        if cache_key in cache:
            return cache[cache_key]
        
        base_dir = self.converted_dir if is_converted else self.orca_dir
        profile_path = base_dir / profile_type / f"{profile_name}.json"
        
        if not profile_path.exists():
            return {}
        
        try:
            with open(profile_path, 'r') as f:
                data = json.load(f)
                cache[cache_key] = data
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {profile_path}: {e}")
            return {}
    
    def resolve_inheritance(self, profile_type: str, profile_name: str, 
                          is_converted: bool, visited: Set[str] = None) -> Dict[str, Any]:
        """
        Resolve a profile's inheritance chain to create a concrete profile.
        
        Args:
            profile_type: Type of profile
            profile_name: Name of the profile
            is_converted: True for converted profiles, False for OrcaSlicer
            visited: Set of visited profiles to detect circular dependencies
        
        Returns:
            Fully resolved profile with all inherited settings
        """
        if visited is None:
            visited = set()
        
        cache_key = f"{profile_type}/{profile_name}"
        if cache_key in visited:
            print(f"Warning: Circular inheritance detected at {cache_key}")
            return {}
        
        visited.add(cache_key)
        
        # Load the profile
        profile = self.load_profile(profile_type, profile_name, is_converted)
        if not profile:
            return {}
        
        # Start with an empty resolved profile
        resolved = {}
        
        # If this profile inherits from others, resolve them first
        inherits = profile.get('inherits', '')
        if inherits:
            # Split by semicolon for multiple inheritance (mainly in OrcaSlicer format)
            parent_names = [p.strip() for p in inherits.split(';') if p.strip()]
            
            for parent_name in parent_names:
                parent_resolved = self.resolve_inheritance(
                    profile_type, parent_name, is_converted, visited.copy()
                )
                # Merge parent settings (later parents override earlier ones)
                resolved.update(parent_resolved)
        
        # Apply this profile's settings (overriding parent settings)
        for key, value in profile.items():
            # Skip metadata fields
            if key not in ['inherits', 'from', 'instantiation', 'type', 'name']:
                resolved[key] = value
        
        return resolved
    
    def compare_profiles(self, profile_type: str, profile_name: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Compare a converted profile with an OrcaSlicer profile.
        
        Args:
            profile_type: Type of profile to compare
            profile_name: Name of the profile to compare
        
        Returns:
            Tuple of (only_in_converted, only_in_orca, different_values)
        """
        converted = self.resolve_inheritance(profile_type, profile_name, is_converted=True)
        orca = self.resolve_inheritance(profile_type, profile_name, is_converted=False)
        
        only_in_converted = {}
        only_in_orca = {}
        different_values = {}
        
        # Find settings only in converted
        for key, value in converted.items():
            if key not in orca:
                only_in_converted[key] = value
            elif self._normalize_value(value) != self._normalize_value(orca[key]):
                different_values[key] = {
                    'converted': value,
                    'orca': orca[key]
                }
        
        # Find settings only in OrcaSlicer
        for key, value in orca.items():
            if key not in converted:
                only_in_orca[key] = value
        
        return only_in_converted, only_in_orca, different_values
    
    def _normalize_value(self, value: Any) -> Any:
        """Normalize values for comparison."""
        # Convert strings to comparable format
        if isinstance(value, str):
            # Try to convert to number for comparison
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except (ValueError, TypeError):
                return value.strip()
        
        # Normalize lists
        if isinstance(value, list):
            return [self._normalize_value(v) for v in value]
        
        return value
    
    def print_diff(self, profile_type: str, profile_name: str, verbose: bool = False):
        """
        Print differences between converted and OrcaSlicer profiles.
        
        Args:
            profile_type: Type of profile
            profile_name: Name of profile
            verbose: If True, show all differences. If False, only show summary.
        """
        print(f"\n{'='*80}")
        print(f"Comparing: {profile_type}/{profile_name}")
        print(f"{'='*80}\n")
        
        only_converted, only_orca, different = self.compare_profiles(profile_type, profile_name)
        
        if not only_converted and not only_orca and not different:
            print("✓ Profiles are identical!\n")
            return
        
        # Summary
        print(f"Summary:")
        print(f"  Settings only in converted: {len(only_converted)}")
        print(f"  Settings only in OrcaSlicer: {len(only_orca)}")
        print(f"  Settings with different values: {len(different)}\n")
        
        if not verbose:
            print("Run with --verbose to see detailed differences\n")
            return
        
        # Detailed output
        if only_converted:
            print(f"Settings only in CONVERTED ({len(only_converted)}):")
            print("-" * 80)
            for key, value in sorted(only_converted.items()):
                formatted_key = self._format_setting_name(profile_type, key)
                print(f"  {formatted_key}: {self._format_value(value)}")
            print()
        
        if only_orca:
            print(f"Settings only in ORCASLICER ({len(only_orca)}):")
            print("-" * 80)
            for key, value in sorted(only_orca.items()):
                formatted_key = self._format_setting_name(profile_type, key)
                print(f"  {formatted_key}: {self._format_value(value)}")
            print()
        
        if different:
            print(f"Settings with DIFFERENT VALUES ({len(different)}):")
            print("-" * 80)
            for key, values in sorted(different.items()):
                formatted_key = self._format_setting_name(profile_type, key)
                print(f"  {formatted_key}:")
                print(f"    Converted:  {self._format_value(values['converted'])}")
                print(f"    OrcaSlicer: {self._format_value(values['orca'])}")
            print()
    
    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, list):
            if len(value) == 1:
                return f"[{value[0]}]"
            elif len(value) > 3:
                return f"[{value[0]}, {value[1]}, ... ({len(value)} items)]"
            else:
                return str(value)
        return str(value)
    
    def find_profiles(self, profile_type: str, name_filter: str = None) -> List[str]:
        """
        Find all profiles of a given type.
        
        Args:
            profile_type: Type of profile to find
            name_filter: Optional filter string (case-insensitive substring match)
        
        Returns:
            List of profile names (without .json extension)
        """
        converted_dir = self.converted_dir / profile_type
        if not converted_dir.exists():
            return []
        
        profiles = []
        for path in converted_dir.glob("*.json"):
            name = path.stem
            if name_filter and name_filter.lower() not in name.lower():
                continue
            profiles.append(name)
        
        return sorted(profiles)
    
    def diff_all(self, profile_type: str, name_filter: str = None, verbose: bool = False, 
                 only_issues: bool = False):
        """
        Compare all profiles of a given type.
        
        Args:
            profile_type: Type of profiles to compare
            name_filter: Optional filter for profile names
            verbose: Show detailed differences
            only_issues: Only show profiles with missing or different settings
        """
        profiles = self.find_profiles(profile_type, name_filter)
        
        if not profiles:
            print(f"No profiles found matching filter: {name_filter or 'all'}")
            return
        
        print(f"\nFound {len(profiles)} profiles to compare")
        
        identical_count = 0
        different_count = 0
        
        for profile_name in profiles:
            only_converted, only_orca, different = self.compare_profiles(profile_type, profile_name)
            
            is_identical = not only_converted and not only_orca and not different
            has_issues = only_orca or different  # Missing settings or different values
            
            if is_identical:
                identical_count += 1
                if verbose and not only_issues:
                    print(f"✓ {profile_name}")
            else:
                different_count += 1
                
                # Skip if only_issues is True and there are no actual issues
                if only_issues and not has_issues:
                    continue
                
                if verbose:
                    self.print_diff(profile_type, profile_name, verbose=True)
                else:
                    print(f"✗ {profile_name} - {len(only_converted)} extra, {len(only_orca)} missing, {len(different)} different")
        
        print(f"\n{'='*80}")
        print(f"Summary: {identical_count} identical, {different_count} different")
        print(f"{'='*80}\n")
    
    def summarize_all(self, profile_type: str, name_filter: str = None):
        """
        Summarize all differences across multiple profiles.
        
        This aggregates all differences and shows which settings appear most frequently
        in each category (only converted, only orca, different values).
        
        Args:
            profile_type: Type of profiles to compare
            name_filter: Optional filter for profile names
        """
        profiles = self.find_profiles(profile_type, name_filter)
        
        if not profiles:
            print(f"No profiles found matching filter: {name_filter or 'all'}")
            return
        
        # Counters for aggregation
        only_converted_counts = {}  # setting -> count
        only_orca_counts = {}  # setting -> count
        only_orca_examples = {}  # setting -> list of (value, profile_name)
        different_counts = {}  # setting -> count
        different_examples = {}  # setting -> list of (converted_val, orca_val, profile_name)
        
        print(f"\nAnalyzing {len(profiles)} profiles...")
        
        for profile_name in profiles:
            only_converted, only_orca, different = self.compare_profiles(profile_type, profile_name)
            
            # Count settings only in converted
            for key in only_converted.keys():
                only_converted_counts[key] = only_converted_counts.get(key, 0) + 1
            
            # Count settings only in OrcaSlicer and store examples
            for key, value in only_orca.items():
                only_orca_counts[key] = only_orca_counts.get(key, 0) + 1
                
                # Store examples (limit to first 3)
                if key not in only_orca_examples:
                    only_orca_examples[key] = []
                if len(only_orca_examples[key]) < 3:
                    only_orca_examples[key].append({
                        'value': value,
                        'profile': profile_name
                    })
            
            # Count different values
            for key, values in different.items():
                different_counts[key] = different_counts.get(key, 0) + 1
                
                # Store examples (limit to first 3)
                if key not in different_examples:
                    different_examples[key] = []
                if len(different_examples[key]) < 3:
                    different_examples[key].append({
                        'converted': values['converted'],
                        'orca': values['orca'],
                        'profile': profile_name
                    })
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"SUMMARY ACROSS ALL {len(profiles)} PROFILES")
        print(f"{'='*80}\n")
        
        # Settings only in converted (sorted by frequency)
        if only_converted_counts:
            print(f"Settings only in CONVERTED ({len(only_converted_counts)} unique settings):")
            print("-" * 80)
            for key, count in sorted(only_converted_counts.items(), key=lambda x: (-x[1], x[0])):
                percentage = (count / len(profiles)) * 100
                formatted_key = self._format_setting_name(profile_type, key)
                print(f"  {formatted_key}: {count} profiles ({percentage:.1f}%)")
            print()
        else:
            print("✓ No settings found only in converted profiles\n")
        
        # Settings only in OrcaSlicer (sorted by frequency)
        if only_orca_counts:
            print(f"Settings only in ORCASLICER ({len(only_orca_counts)} unique settings):")
            print("-" * 80)
            for key, count in sorted(only_orca_counts.items(), key=lambda x: (-x[1], x[0])):
                percentage = (count / len(profiles)) * 100
                formatted_key = self._format_setting_name(profile_type, key)
                print(f"  {formatted_key}: {count} profiles ({percentage:.1f}%)")
                
                # Show examples
                if key in only_orca_examples:
                    for i, example in enumerate(only_orca_examples[key], 1):
                        print(f"    Example {i} ({example['profile']}):")
                        print(f"      Value: {self._format_value(example['value'])}")
            print()
        else:
            print("✓ No settings found only in OrcaSlicer profiles\n")
        
        # these have been manually determined to be non-critical differences
        # likely due to profile drift
        ignored_differences = [
            "overhang_1_4_speed",
            "overhang_2_4_speed",
            "overhang_3_4_speed",
            "overhang_4_4_speed",
            "raft_first_layer_expansion",
            "sparse_infill_pattern",
            "support_object_xy_distance",
            "support_interface_speed",
            "tree_support_tip_diameter",
            "initial_layer_infill_speed",
            "small_perimeter_speed",
            "outer_wall_speed",
            "support_interface_top_layers",
            "inner_wall_speed",
            "top_surface_speed",
            "support_line_width",
            "internal_solid_infill_speed",
            "initial_layer_speed",
            "gap_infill_speed",
            "support_threshold_angle",
            "top_surface_acceleration",
            "infill_wall_overlap",
            "initial_layer_print_height",
            "raft_first_layer_density",         
            "support_base_pattern_spacing",
            "support_interface_spacing",
            "support_top_z_distance",
            "tree_support_branch_angle",
            "enable_prime_tower",
            "internal_solid_infill_acceleration",
            "bottom_shell_layers",
            "bottom_shell_thickness",
            "bridge_acceleration",
            "bridge_speed",
            "brim_object_gap",
            "default_acceleration",
            "elefant_foot_compensation",
            "infill_anchor_max",
            "sparse_infill_acceleration"
            "sparse_infill_density",
            "sparse_infill_speed",
            "top_shell_layers",
            "top_shell_thickness",
            "travel_acceleration",
            "travel_speed",
            "inner_wall_acceleration",
            "internal_solid_infill_line_width",
            "outer_wall_acceleration",
            "seam_position",
            "sparse_infill_line_width",
            "sparse_infill_density",
            "sparse_infill_acceleration",
            "support_speed",
            "raft_contact_distance",
            "enable_support", # see note, this is manually overridden to be off
            
        ]


        # Settings with different values (sorted by frequency)
        if different_counts:
            print(f"Settings with DIFFERENT VALUES ({len(different_counts)} unique settings):")
            print("-" * 80)
            for key, count in sorted(different_counts.items(), key=lambda x: (-x[1], x[0])):
                if key in ignored_differences:
                    continue
                percentage = (count / len(profiles)) * 100
                formatted_key = self._format_setting_name(profile_type, key)
                print(f"  {formatted_key}: {count} profiles ({percentage:.1f}%)")
                
                # Show examples
                if key in different_examples:
                    for i, example in enumerate(different_examples[key], 1):
                        print(f"    Example {i} ({example['profile']}):")
                        print(f"      Converted:  {self._format_value(example['converted'])}")
                        print(f"      OrcaSlicer: {self._format_value(example['orca'])}")
            print()
        else:
            print("✓ No settings with different values\n")
        
        # Overall summary
        print(f"{'='*80}")
        print(f"TOTALS:")
        print(f"  Unique settings only in converted: {len(only_converted_counts)}")
        print(f"  Unique settings only in OrcaSlicer: {len(only_orca_counts)}")
        print(f"  Unique settings with different values: {len(different_counts)}")
        print(f"{'='*80}\n")



def main():
    parser = argparse.ArgumentParser(
        description='Compare converted profiles with OrcaSlicer profiles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare a single process profile
  python profile_differ.py --converted output --orca orca_existing process "0.15mm STRUCTURAL @COREONEL 0.6"
  
  # Compare all CORE One process profiles
  python profile_differ.py --converted output --orca orca_existing process --filter "COREONEL"
  
  # Compare all process profiles with verbose output
  python profile_differ.py --converted output --orca orca_existing process --all --verbose
  
  # Compare a filament profile
  python profile_differ.py --converted output --orca orca_existing filament "Prusament PLA @COREONE"
        """
    )
    
    parser.add_argument('--converted', required=True,
                       help='Directory containing converted profiles')
    parser.add_argument('--orca', required=True,
                       help='Directory containing OrcaSlicer profiles')
    parser.add_argument('profile_type', choices=['process', 'filament', 'machine', 'machine_model'],
                       help='Type of profile to compare')
    parser.add_argument('profile_name', nargs='?',
                       help='Name of specific profile to compare (without .json)')
    parser.add_argument('--filter',
                       help='Filter profiles by name (case-insensitive substring match)')
    parser.add_argument('--all', action='store_true',
                       help='Compare all profiles of the given type')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed differences')
    parser.add_argument('--only-issues', action='store_true',
                       help='Only show profiles with missing or different settings (excludes profiles with only extra settings)')
    parser.add_argument('--summarize', '-s', action='store_true',
                       help='Show aggregated summary of all differences across profiles')
    
    args = parser.parse_args()
    
    registries = REGISTRIES if HAS_REGISTRIES else {}
    differ = ProfileDiffer(args.converted, args.orca, registries)
    
    if args.profile_name:
        # Compare a single profile
        differ.print_diff(args.profile_type, args.profile_name, verbose=args.verbose)
    elif args.summarize:
        # Show aggregated summary
        differ.summarize_all(args.profile_type, args.filter)
    elif args.all or args.filter:
        # Compare multiple profiles
        differ.diff_all(args.profile_type, args.filter, verbose=args.verbose, 
                       only_issues=args.only_issues)
    else:
        parser.error("Provide either a profile name, --filter, --all, or --summarize")


if __name__ == '__main__':
    main()
