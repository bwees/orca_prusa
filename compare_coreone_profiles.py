#!/usr/bin/env python3
"""
Compare PrusaSlicer profiles between versions for CORE One profiles.
This script:
1. Parses INI files containing printer and print profiles
2. Resolves inheritance chains to get complete profile settings
3. Compares profiles between versions
4. Generates a report of changes (excluding filament profiles)
"""

import configparser
import re
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict


class ProfileParser:
    """Parse and resolve PrusaSlicer INI profiles with inheritance."""
    
    def __init__(self, ini_path: str):
        self.ini_path = Path(ini_path)
        # Disable interpolation to handle % characters in values
        self.config = configparser.ConfigParser(interpolation=None)
        # Preserve case for keys
        self.config.optionxform = str
        self.config.read(self.ini_path)
        
    def get_sections_by_type(self, section_type: str) -> List[str]:
        """Get all sections of a specific type (e.g., 'print:', 'printer:')."""
        return [s for s in self.config.sections() if s.startswith(f'{section_type}:')]
    
    def get_coreone_sections(self, section_type: str) -> List[str]:
        """Get all CORE One sections of a specific type."""
        all_sections = self.get_sections_by_type(section_type)
        return [s for s in all_sections if '@COREONE' in s.upper()]
    
    def resolve_profile(self, section_name: str) -> Dict[str, str]:
        """
        Resolve a profile by following its inheritance chain.
        Returns a complete dictionary of all settings.
        """
        if section_name not in self.config:
            return {}
        
        # Start with an empty profile
        resolved = {}
        
        # Track visited sections to avoid circular inheritance
        visited = set()
        
        def resolve_recursive(current_section: str):
            if current_section in visited:
                return
            if current_section not in self.config:
                return
                
            visited.add(current_section)
            
            # Check if this section has an 'inherits' field
            if 'inherits' in self.config[current_section]:
                inherits_value = self.config[current_section]['inherits']
                # Split on semicolon to handle multiple inheritance
                parent_names = [p.strip() for p in inherits_value.split(';')]
                
                # Resolve parents first (in order)
                for parent_name in parent_names:
                    # Handle wildcard patterns like *C1_HF04*
                    if parent_name.startswith('*') and parent_name.endswith('*'):
                        # This is a template/mixin, find matching sections
                        pattern = parent_name.strip('*')
                        # Look for sections that match this pattern
                        matching = [s for s in self.config.sections() 
                                  if pattern in s and s.startswith('*')]
                        for match in matching:
                            resolve_recursive(match)
                    else:
                        # Regular inheritance - need to find the full section name
                        # Try to find exact match or with prefix
                        full_name = None
                        if parent_name in self.config:
                            full_name = parent_name
                        else:
                            # Try with section type prefix
                            section_type = current_section.split(':')[0]
                            candidate = f"{section_type}:{parent_name}"
                            if candidate in self.config:
                                full_name = candidate
                        
                        if full_name:
                            resolve_recursive(full_name)
            
            # Now apply current section's settings (overriding parents)
            for key, value in self.config[current_section].items():
                if key != 'inherits':  # Don't include the inherits directive itself
                    resolved[key] = value
        
        resolve_recursive(section_name)
        return resolved
    
    def resolve_profile_with_source(self, section_name: str) -> Dict[str, Tuple[str, str]]:
        """
        Resolve a profile and track which section each setting came from.
        Returns dict mapping setting_name -> (value, source_section)
        """
        if section_name not in self.config:
            return {}
        
        # Maps setting -> (value, source_section)
        resolved = {}
        visited = set()
        
        def resolve_recursive(current_section: str):
            if current_section in visited:
                return
            if current_section not in self.config:
                return
                
            visited.add(current_section)
            
            # Check if this section has an 'inherits' field
            if 'inherits' in self.config[current_section]:
                inherits_value = self.config[current_section]['inherits']
                parent_names = [p.strip() for p in inherits_value.split(';')]
                
                # Resolve parents first (in order)
                for parent_name in parent_names:
                    if parent_name.startswith('*') and parent_name.endswith('*'):
                        pattern = parent_name.strip('*')
                        matching = [s for s in self.config.sections() 
                                  if pattern in s and s.startswith('*')]
                        for match in matching:
                            resolve_recursive(match)
                    else:
                        full_name = None
                        if parent_name in self.config:
                            full_name = parent_name
                        else:
                            section_type = current_section.split(':')[0]
                            candidate = f"{section_type}:{parent_name}"
                            if candidate in self.config:
                                full_name = candidate
                        
                        if full_name:
                            resolve_recursive(full_name)
            
            # Apply current section's settings with source tracking
            for key, value in self.config[current_section].items():
                if key != 'inherits':
                    resolved[key] = (value, current_section)
        
        resolve_recursive(section_name)
        return resolved
    
    def get_direct_settings(self, section_name: str) -> Dict[str, str]:
        """Get only the settings directly defined in this section (not inherited)."""
        if section_name not in self.config:
            return {}
        return {k: v for k, v in self.config[section_name].items() if k != 'inherits'}
    
    def get_inheritance_chain(self, section_name: str) -> List[str]:
        """Get the inheritance chain for a section."""
        if section_name not in self.config:
            return []
        
        chain = []
        if 'inherits' in self.config[section_name]:
            inherits_value = self.config[section_name]['inherits']
            parent_names = [p.strip() for p in inherits_value.split(';')]
            
            for parent_name in parent_names:
                if parent_name.startswith('*') and parent_name.endswith('*'):
                    pattern = parent_name.strip('*')
                    matching = [s for s in self.config.sections() 
                              if pattern in s and s.startswith('*')]
                    chain.extend(matching)
                else:
                    full_name = None
                    if parent_name in self.config:
                        full_name = parent_name
                    else:
                        section_type = section_name.split(':')[0]
                        candidate = f"{section_type}:{parent_name}"
                        if candidate in self.config:
                            full_name = candidate
                    if full_name:
                        chain.append(full_name)
        
        return chain


class ProfileComparer:
    """Compare profiles between two versions."""
    
    def __init__(self, old_parser: ProfileParser, new_parser: ProfileParser):
        self.old_parser = old_parser
        self.new_parser = new_parser
        
    def build_inheritance_tree(self, parser: ProfileParser, section_type: str) -> Dict[str, Set[str]]:
        """Build a tree showing which profiles inherit from which."""
        sections = parser.get_coreone_sections(section_type)
        children = defaultdict(set)
        
        for section in sections:
            parents = parser.get_inheritance_chain(section)
            for parent in parents:
                children[parent].add(section)
        
        return children
    
    def get_all_descendants(self, section: str, children_map: Dict[str, Set[str]]) -> Set[str]:
        """Get all profiles that inherit from this section (recursively)."""
        descendants = set()
        to_visit = [section]
        
        while to_visit:
            current = to_visit.pop()
            if current in children_map:
                for child in children_map[current]:
                    if child not in descendants:
                        descendants.add(child)
                        to_visit.append(child)
        
        return descendants
        
    def compare_profiles(self, section_type: str = 'print') -> Dict:
        """
        Compare all CORE One profiles of a given type between versions.
        Returns dict with added, removed, and changed profiles.
        """
        old_sections = set(self.old_parser.get_coreone_sections(section_type))
        new_sections = set(self.new_parser.get_coreone_sections(section_type))
        
        added = new_sections - old_sections
        removed = old_sections - new_sections
        common = old_sections & new_sections
        
        # Build inheritance trees
        old_children = self.build_inheritance_tree(self.old_parser, section_type)
        new_children = self.build_inheritance_tree(self.new_parser, section_type)
        
        changes = {}
        
        for section in common:
            old_profile = self.old_parser.resolve_profile_with_source(section)
            new_profile = self.new_parser.resolve_profile_with_source(section)
            old_direct = self.old_parser.get_direct_settings(section)
            new_direct = self.new_parser.get_direct_settings(section)
            
            # Find differences
            all_keys = set(old_profile.keys()) | set(new_profile.keys())
            
            profile_changes = {
                'added': {},
                'removed': {},
                'modified': {},
                'direct_changes': set()  # Settings changed directly in this profile
            }
            
            for key in all_keys:
                old_val_source = old_profile.get(key)
                new_val_source = new_profile.get(key)
                
                old_val = old_val_source[0] if old_val_source else None
                new_val = new_val_source[0] if new_val_source else None
                old_source = old_val_source[1] if old_val_source else None
                new_source = new_val_source[1] if new_val_source else None
                
                # Check if this setting was directly defined in either version
                in_old_direct = key in old_direct
                in_new_direct = key in new_direct
                
                # From a "what do I need to edit" perspective:
                # - "added" = need to add this line to the profile (wasn't there before)
                # - "removed" = need to remove this line from the profile (was there before)
                # - "modified" = need to change the value of an existing line
                
                if not in_old_direct and in_new_direct:
                    # Need to ADD this line to the profile
                    profile_changes['added'][key] = {
                        'value': new_val,
                        'source': new_source,
                        'direct': True
                    }
                    profile_changes['direct_changes'].add(key)
                elif in_old_direct and not in_new_direct:
                    # Need to REMOVE this line from the profile
                    profile_changes['removed'][key] = {
                        'value': old_val,
                        'source': old_source,
                        'direct': True
                    }
                    profile_changes['direct_changes'].add(key)
                elif in_old_direct and in_new_direct and old_direct[key] != new_direct[key]:
                    # Line exists in both but value changed - need to MODIFY
                    profile_changes['modified'][key] = {
                        'old': old_direct[key],
                        'new': new_direct[key],
                        'old_source': old_source,
                        'new_source': new_source,
                        'direct': True
                    }
                    profile_changes['direct_changes'].add(key)
            
            # Only include if there are actual changes
            if any(profile_changes['added']) or any(profile_changes['removed']) or any(profile_changes['modified']):
                # Get descendants to show impact
                descendants = self.get_all_descendants(section, new_children)
                profile_changes['affects'] = sorted(descendants)
                changes[section] = profile_changes
        
        return {
            'added_profiles': sorted(added),
            'removed_profiles': sorted(removed),
            'changed_profiles': changes,
            'inheritance_tree': new_children
        }


def generate_report(comparison: Dict, output_path: str):
    """Generate a text report of the comparison."""
    
    lines = []
    lines.append("=" * 80)
    lines.append("PRUSA CORE ONE PROFILE COMPARISON REPORT")
    lines.append("Comparing: 2.2.11 (initial) → 2.4.2 (latest)")
    lines.append("Scope: Print and Printer profiles with @COREONE (excluding filament)")
    lines.append("=" * 80)
    lines.append("")
    
    # Added profiles
    if comparison['added_profiles']:
        lines.append("=" * 80)
        lines.append("NEWLY ADDED PROFILES")
        lines.append("=" * 80)
        for profile in comparison['added_profiles']:
            lines.append(f"  + {profile}")
        lines.append("")
    else:
        lines.append("No new profiles added.")
        lines.append("")
    
    # Removed profiles
    if comparison['removed_profiles']:
        lines.append("=" * 80)
        lines.append("REMOVED PROFILES")
        lines.append("=" * 80)
        for profile in comparison['removed_profiles']:
            lines.append(f"  - {profile}")
        lines.append("")
    else:
        lines.append("No profiles removed.")
        lines.append("")
    
    # Changed profiles - first show profiles with direct changes
    if comparison['changed_profiles']:
        # Separate profiles with direct changes from those with only inherited changes
        profiles_with_direct_changes = {
            k: v for k, v in comparison['changed_profiles'].items()
            if v['direct_changes']
        }
        
        profiles_with_only_inherited = {
            k: v for k, v in comparison['changed_profiles'].items()
            if not v['direct_changes']
        }
        
        lines.append("=" * 80)
        lines.append("PROFILES WITH DIRECT CHANGES")
        lines.append("=" * 80)
        lines.append("These profiles have settings that were modified directly in the profile.")
        lines.append("Changes will propagate to all child profiles that inherit from these.")
        lines.append("")
        
        if profiles_with_direct_changes:
            for profile_name in sorted(profiles_with_direct_changes.keys()):
                changes = profiles_with_direct_changes[profile_name]
                
                lines.append("-" * 80)
                lines.append(f"Profile: {profile_name}")
                lines.append("-" * 80)
                
                # Show which profiles will be affected
                if changes['affects']:
                    lines.append(f"\n  ⚠️  AFFECTS {len(changes['affects'])} CHILD PROFILE(S):")
                    for affected in changes['affects'][:10]:  # Show first 10
                        lines.append(f"      - {affected}")
                    if len(changes['affects']) > 10:
                        lines.append(f"      ... and {len(changes['affects']) - 10} more")
                
                # Added settings (direct only)
                direct_added = {k: v for k, v in changes['added'].items() if v['direct']}
                if direct_added:
                    lines.append("\n  SETTINGS TO ADD (add these lines to the profile):")
                    for key in sorted(direct_added.keys()):
                        value = direct_added[key]['value']
                        lines.append(f"    + {key} = {value}")
                
                # Removed settings (direct only)
                direct_removed = {k: v for k, v in changes['removed'].items() if v['direct']}
                if direct_removed:
                    lines.append("\n  SETTINGS TO REMOVE (delete these lines from the profile):")
                    for key in sorted(direct_removed.keys()):
                        value = direct_removed[key]['value']
                        lines.append(f"    - {key} = {value}")
                
                # Modified settings (direct only)
                direct_modified = {k: v for k, v in changes['modified'].items() if v['direct']}
                if direct_modified:
                    lines.append("\n  SETTINGS TO MODIFY (change the value in the profile):")
                    for key in sorted(direct_modified.keys()):
                        old_val = direct_modified[key]['old']
                        new_val = direct_modified[key]['new']
                        lines.append(f"    • {key}")
                        lines.append(f"      OLD: {old_val}")
                        lines.append(f"      NEW: {new_val}")
                
                lines.append("")
        else:
            lines.append("None - all changes are inherited from parent profiles.")
            lines.append("")
        
        # Now show profiles with only inherited changes
        if profiles_with_only_inherited:
            lines.append("=" * 80)
            lines.append("PROFILES WITH ONLY INHERITED CHANGES")
            lines.append("=" * 80)
            lines.append("These profiles inherit changes from their parent profiles.")
            lines.append("No action needed - they will update automatically when parents are updated.")
            lines.append("")
            
            for profile_name in sorted(profiles_with_only_inherited.keys()):
                changes = profiles_with_only_inherited[profile_name]
                
                lines.append(f"  • {profile_name}")
                
                # Show where changes came from
                sources = set()
                for change_dict in [changes['added'], changes['removed'], changes['modified']]:
                    for key, info in change_dict.items():
                        if isinstance(info, dict):
                            if 'source' in info:
                                sources.add(info['source'])
                            if 'new_source' in info:
                                sources.add(info['new_source'])
                
                if sources:
                    lines.append(f"    Inherits changes from: {', '.join(sorted(sources))}")
            
            lines.append("")
    else:
        lines.append("No profiles were modified.")
        lines.append("")
    
    # Summary statistics
    lines.append("=" * 80)
    lines.append("SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Profiles added: {len(comparison['added_profiles'])}")
    lines.append(f"Profiles removed: {len(comparison['removed_profiles'])}")
    lines.append(f"Profiles modified: {len(comparison['changed_profiles'])}")
    
    if comparison['changed_profiles']:
        profiles_with_direct = sum(1 for v in comparison['changed_profiles'].values() if v['direct_changes'])
        profiles_inherited_only = len(comparison['changed_profiles']) - profiles_with_direct
        
        lines.append(f"  - With direct changes: {profiles_with_direct}")
        lines.append(f"  - With only inherited changes: {profiles_inherited_only}")
        
        total_direct_changes = sum(
            len(v['direct_changes']) 
            for v in comparison['changed_profiles'].values()
        )
        lines.append(f"Total direct setting changes to make: {total_direct_changes}")
    
    lines.append("=" * 80)
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Report generated: {output_path}")
    print(f"  - {len(comparison['added_profiles'])} profiles added")
    print(f"  - {len(comparison['removed_profiles'])} profiles removed")
    print(f"  - {len(comparison['changed_profiles'])} profiles modified")
    if comparison['changed_profiles']:
        profiles_with_direct = sum(1 for v in comparison['changed_profiles'].values() if v['direct_changes'])
        total_direct_changes = sum(
            len(v['direct_changes']) 
            for v in comparison['changed_profiles'].values()
        )
        print(f"  - {profiles_with_direct} profiles need direct updates ({total_direct_changes} settings)")
        print(f"  - {len(comparison['changed_profiles']) - profiles_with_direct} profiles inherit changes automatically")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    
    # Input files
    old_ini = script_dir / "new" / "2.2.11.ini"
    new_ini = script_dir / "new" / "2.4.2.ini"
    
    # Output file
    output_file = script_dir / "coreone_profile_changes.txt"
    
    print("Parsing profiles...")
    old_parser = ProfileParser(old_ini)
    new_parser = ProfileParser(new_ini)
    
    print("Comparing print profiles...")
    comparer = ProfileComparer(old_parser, new_parser)
    comparison = comparer.compare_profiles('print')
    
    print("Generating report...")
    generate_report(comparison, output_file)
    
    print("\nDone!")


if __name__ == '__main__':
    main()
