#!/usr/bin/env python3
"""
Main conversion script to convert PrusaSlicer INI profiles to OrcaSlicer JSON profiles.

Usage:
    python prusa_to_orca_converter.py <ini_file> [--printer <printer_name>] [--output-dir <dir>]
    
Example:
    python prusa_to_orca_converter.py 2.4.2.ini --printer "Prusa CORE One" --output-dir output
"""
import sys
import os
import argparse
from typing import Dict, List, Set
from profile_parser import ProfileParser
from converters.profile_converters import (
    PrinterProfileConverter,
    PrintProfileConverter,
    FilamentProfileConverter,
    save_json_profile,
    normalize_printer_name
)


class PrusaToOrcaConverter:
    """Main converter orchestrator."""
    
    def __init__(self, ini_file: str, output_dir: str = "output"):
        self.ini_file = ini_file
        self.output_dir = output_dir
        self.needs_conversion: Set[str] = set()
        
        # Create output directories
        self.machine_dir = os.path.join(output_dir, "machine")
        self.process_dir = os.path.join(output_dir, "process")
        self.filament_dir = os.path.join(output_dir, "filament")
        
        for dir_path in [self.machine_dir, self.process_dir, self.filament_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Parse INI file
        print(f"Parsing {ini_file}...")
        parser = ProfileParser(ini_file)
        self.profiles = parser.parse()
        
    def convert_all(self, printer_filter: str = None):
        """
        Convert all profiles.
        
        Args:
            printer_filter: Optional printer name to filter (e.g., "Prusa CORE One")
        """
        print("\n" + "="*60)
        print("Starting conversion...")
        print("="*60 + "\n")
        
        # Convert printer models and printers
        self.convert_printers(printer_filter)
        
        # Convert print profiles
        self.convert_prints(printer_filter)
        
        # Convert filament profiles
        self.convert_filaments(printer_filter)
        
        # Write needs conversion report
        self.write_needs_conversion_report()
        
        print("\n" + "="*60)
        print("Conversion complete!")
        print(f"Output directory: {self.output_dir}")
        print("="*60 + "\n")
        
    def convert_printers(self, printer_filter: str = None):
        """Convert printer models and printer variant profiles."""
        print("Converting printer profiles...")
        
        printer_converter = PrinterProfileConverter()
        
        # Convert printer_model sections
        if 'printer_model' in self.profiles:
            for model in self.profiles['printer_model']:
                model_name = model.get('name', '')
                
                if printer_filter and printer_filter not in model_name:
                    continue
                
                print(f"  - Converting printer model: {model_name}")
                
                # Convert to machine_model(s)
                machine_models = printer_converter.convert_printer_model(model)
                
                for machine_model in machine_models:
                    filename = f"{machine_model['name']}.json"
                    save_json_profile(machine_model, self.machine_dir, filename)
                    print(f"    Created: {filename}")
        
        # Convert printer sections (variants)
        if 'printer' in self.profiles:
            # Group printers by model
            printers_by_model = {}
            for printer in self.profiles['printer']:
                printer_name = printer.get('name', '')
                
                if printer_filter and printer_filter not in printer_name:
                    continue
                
                model = printer.get('printer_model', '')
                if model not in printers_by_model:
                    printers_by_model[model] = []
                printers_by_model[model].append(printer)
            
            # Convert each printer
            for model, printers in printers_by_model.items():
                # Determine parent name from first printer
                if printers:
                    first_printer = printers[0]
                    parent_name = self._extract_printer_base_name(first_printer.get('name', ''))
                    
                    for printer in printers:
                        printer_name = printer.get('name', '')
                        print(f"  - Converting printer variant: {printer_name}")
                        
                        machine = printer_converter.convert_printer_variant(printer, parent_name)
                        # Normalize filename to match OrcaSlicer format
                        normalized_name = normalize_printer_name(printer_name)
                        filename = f"{normalized_name}.json"
                        save_json_profile(machine, self.machine_dir, filename)
                        print(f"    Created: {filename}")
        
        # Track unconverted settings
        self.needs_conversion.update(printer_converter.needs_conversion)
        
    def convert_prints(self, printer_filter: str = None):
        """Convert print profiles."""
        print("\nConverting print profiles...")
        
        print_converter = PrintProfileConverter()
        
        if 'print' in self.profiles:
            # Pass all profiles to converter for inheritance resolution
            print_converter.set_all_profiles(self.profiles['print'])
            
            for print_profile in self.profiles['print']:
                profile_name = print_profile.get('name', '')
                
                # Filter by printer if specified
                if printer_filter:
                    # Check compatible_printers_condition
                    condition = print_profile.get('compatible_printers_condition', '')
                    if condition and printer_filter.replace(' ', '').upper() not in condition.upper():
                        continue
                
                print(f"  - Converting print profile: {profile_name}")
                
                process = print_converter.convert_print_profile(print_profile)
                
                # Skip abstract profiles (starting with *)
                if not profile_name.startswith('*'):
                    # Normalize the filename to match OrcaSlicer format
                    normalized_name = normalize_printer_name(profile_name)
                    filename = f"{normalized_name}.json"
                    save_json_profile(process, self.process_dir, filename)
                    print(f"    Created: {filename}")
        
        # Track unconverted settings
        self.needs_conversion.update(print_converter.needs_conversion)
        
    def convert_filaments(self, printer_filter: str = None):
        """Convert filament profiles."""
        print("\nConverting filament profiles...")
        
        filament_converter = FilamentProfileConverter()
        
        if 'filament' in self.profiles:
            # Pass all profiles to converter for inheritance resolution
            filament_converter.set_all_profiles(self.profiles['filament'])
            
            for filament_profile in self.profiles['filament']:
                profile_name = filament_profile.get('name', '')
                
                # Filter by printer if specified
                if printer_filter:
                    # Check compatible_printers or compatible_printers_condition
                    compatible = filament_profile.get('compatible_printers', [])
                    condition = filament_profile.get('compatible_printers_condition', '')
                    
                    if isinstance(compatible, list) and compatible:
                        # Check if any compatible printer matches filter
                        if not any(printer_filter in p for p in compatible):
                            continue
                    elif condition:
                        if printer_filter.replace(' ', '').upper() not in condition.upper():
                            continue
                
                print(f"  - Converting filament profile: {profile_name}")
                
                filament = filament_converter.convert_filament_profile(filament_profile)
                
                # Skip abstract profiles (starting with *)
                if not profile_name.startswith('*'):
                    # Normalize the filename to match OrcaSlicer format
                    normalized_name = normalize_printer_name(profile_name)
                    filename = f"{normalized_name}.json"
                    save_json_profile(filament, self.filament_dir, filename)
                    print(f"    Created: {filename}")
        
        # Track unconverted settings
        self.needs_conversion.update(filament_converter.needs_conversion)
        
    def write_needs_conversion_report(self):
        """Write a report of settings that need manual conversion."""
        if not self.needs_conversion:
            print("\n✓ All settings were converted successfully!")
            return
        
        report_path = os.path.join(self.output_dir, "NEEDS_CONVERTED.md")
        
        with open(report_path, 'w') as f:
            f.write("# Settings That Need Manual Conversion\n\n")
            f.write("The following PrusaSlicer settings were encountered but don't have ")
            f.write("automatic conversion mappings yet. You'll need to handle these manually:\n\n")
            
            for setting in sorted(self.needs_conversion):
                f.write(f"- `{setting}`\n")
            
            f.write(f"\n\nTotal: {len(self.needs_conversion)} settings\n")
        
        print(f"\n⚠️  Found {len(self.needs_conversion)} settings that need manual conversion")
        print(f"   See {report_path} for details")
        
    def _extract_printer_base_name(self, full_name: str) -> str:
        """Extract the base printer name without nozzle size."""
        # Remove nozzle size variants like "0.4 nozzle", "HF0.4 nozzle", etc.
        import re
        # Pattern to match nozzle variants at the end
        pattern = r'\s+(HF)?0\.\d+\s+nozzle$'
        base_name = re.sub(pattern, '', full_name, flags=re.IGNORECASE)
        return base_name.strip()


def main():
    parser = argparse.ArgumentParser(
        description='Convert PrusaSlicer INI profiles to OrcaSlicer JSON profiles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all profiles
  python prusa_to_orca_converter.py 2.4.2.ini
  
  # Convert only Prusa CORE One profiles
  python prusa_to_orca_converter.py 2.4.2.ini --printer "Prusa CORE One"
  
  # Specify custom output directory
  python prusa_to_orca_converter.py 2.4.2.ini --output-dir my_profiles
        """
    )
    
    parser.add_argument('ini_file', help='Path to PrusaSlicer INI file')
    parser.add_argument('--printer', '-p', help='Filter by printer name (e.g., "Prusa CORE One")')
    parser.add_argument('--output-dir', '-o', default='output', 
                       help='Output directory (default: output)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.ini_file):
        print(f"Error: INI file not found: {args.ini_file}")
        sys.exit(1)
    
    converter = PrusaToOrcaConverter(args.ini_file, args.output_dir)
    converter.convert_all(args.printer)


if __name__ == '__main__':
    main()
