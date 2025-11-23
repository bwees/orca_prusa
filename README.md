# PrusaSlicer to OrcaSlicer Profile Converter

An extensible, modular converter for converting PrusaSlicer INI profiles to OrcaSlicer JSON format.

Claude was heavily used for the creation of the conversion script as it is excellent at parsign large amounts of configs and creating converters.

## Features

- **Modular Architecture**: Built with a flexible converter system that supports 1:1 mappings, multi-key mappings, split conversions, and custom logic
- **Automatic HF Variant Handling**: Separates HF (High Flow) nozzle variants into separate printer models as required by OrcaSlicer
- **Comprehensive Mapping**: Supports printer, print, and filament profile conversions with extensive setting mappings
- **Standalone Profiles**: Builds profiles from scratch without relying on inheritance from other printer models
- **Missing Settings Report**: Automatically generates a `NEEDS_CONVERTED.md` file listing settings that need manual conversion
- **Extensible**: Easy to add new converters and mappings for additional settings

## Quick Start

### Basic Usage

Convert all profiles from a PrusaSlicer INI file:

```bash
python3 prusa_to_orca_converter.py 2.4.2.ini
```

### Filter by Printer

Convert only profiles for a specific printer:

```bash
python3 prusa_to_orca_converter.py 2.4.2.ini --printer "Prusa CORE One"
```

### Custom Output Directory

Specify where to save the converted profiles:

```bash
python3 prusa_to_orca_converter.py 2.4.2.ini --output-dir my_profiles
```

## Output Structure

The converter creates the following directory structure:

```
output/
├── machine/              # Printer profiles
│   ├── Prusa CORE One.json
│   ├── Prusa CORE One HF.json
│   ├── Prusa CORE One 0.4 nozzle.json
│   ├── Prusa CORE One HF 0.4 nozzle.json
│   └── ...
├── process/              # Print profiles
│   ├── 0.20mm SPEED @CORE One 0.4.json
│   ├── 0.15mm STRUCTURAL @CORE One 0.4.json
│   └── ...
├── filament/             # Filament profiles
│   ├── Prusa Generic PLA @CORE One.json
│   ├── Prusa Generic PETG @CORE One.json
│   └── ...
└── NEEDS_CONVERTED.md    # Settings requiring manual conversion
```

## How It Works

### Converter Architecture

The converter uses a modular architecture with different converter types:

1. **SimpleKeyConverter**: 1:1 key mapping with optional value transformation

   ```python
   SimpleKeyConverter("layer_height", "layer_height")
   ```

2. **MultiKeyConverter**: Multiple PrusaSlicer keys → one OrcaSlicer key

   ```python
   MultiKeyConverter(["min_fan_speed", "max_fan_speed"], "fan_speed")
   ```

3. **SplitConverter**: One PrusaSlicer key → multiple OrcaSlicer keys

   ```python
   SplitConverter("support_material_contact_distance", [
       ("support_top_z_distance", lambda x: x),
       ("support_bottom_z_distance", lambda x: x)
   ])
   ```

4. **CustomConverter**: Complex custom conversion logic
   ```python
   CustomConverter(
       can_convert_func=lambda k, v: k == "special_setting",
       convert_func=lambda k, v: custom_logic(v)
   )
   ```

### Profile Conversion Process

#### 1. Printer Profiles

- **printer_model** sections → `machine_model` JSON files
- HF variants separated into distinct models (e.g., "Prusa CORE One" and "Prusa CORE One HF")
- **printer** sections → `machine` JSON files (individual nozzle variants)
- Non-HF variants inherit from corresponding HF variant of same nozzle size
- HF variants inherit from `fdm_machine_common`

#### 2. Print Profiles

- **print** sections → `process` JSON files
- Maintains inheritance chains from PrusaSlicer
- Converts speeds, accelerations, extrusion widths, and all print settings
- Handles layer height profiles, infill patterns, support settings, etc.

#### 3. Filament Profiles

- **filament** sections → `filament` JSON files
- Converts temperatures, cooling settings, flow rates
- Maintains compatibility conditions
- Preserves filament-specific G-code

### Key Differences Handled

The converter handles several key differences between PrusaSlicer and OrcaSlicer:

| PrusaSlicer                   | OrcaSlicer                   | Notes                                |
| ----------------------------- | ---------------------------- | ------------------------------------ |
| `perimeters`                  | `wall_loops`                 | Simple rename                        |
| `fill_pattern`                | `sparse_infill_pattern`      | Pattern names converted              |
| `extrusion_width`             | `line_width`                 | Converted to percentage when numeric |
| `support_material_xy_spacing` | `support_object_xy_distance` | Percentage → absolute value          |
| `first_layer_height`          | `initial_layer_print_height` | Naming convention                    |
| HF variants in nozzle list    | Separate printer model       | Structural change                    |

### G-code Template Handling

Currently, G-code templates are converted 1:1. The converter preserves:

- Start G-code
- End G-code
- Before layer change G-code
- Layer change G-code
- Filament change G-code

**Note**: OrcaSlicer uses different template variables in some cases. You may need to update these manually for full compatibility.

## Extending the Converter

### Adding New Setting Mappings

To add a new simple setting mapping, edit `converters/mapping_registry.py`:

```python
def create_print_registry():
    registry = ConverterRegistry()

    # Add your new mapping
    registry.register_simple("prusa_setting_name", "orca_setting_name")

    # With value transformation
    registry.register_simple("prusa_setting", "orca_setting",
                           lambda x: transform_value(x))

    return registry
```

### Adding Custom Converters

For complex conversions, create a custom converter:

```python
def my_custom_converter(prusa_key, prusa_value):
    result = ConversionResult()

    # Your conversion logic
    if prusa_key == "special_setting":
        value1 = calculate_value1(prusa_value)
        value2 = calculate_value2(prusa_value)

        result.add_setting("orca_setting_1", value1)
        result.add_setting("orca_setting_2", value2)

    return result

# Register it
registry.register_custom(
    can_convert_func=lambda k, v: k == "special_setting",
    convert_func=my_custom_converter
)
```

### Supporting New Printers

The converter is designed to work with any Prusa printer. To convert a different printer:

```bash
python3 prusa_to_orca_converter.py 2.4.2.ini --printer "Prusa MK4S"
```

The naming convention and structure will be automatically maintained.

## Known Limitations

### Settings Requiring Manual Conversion

Some PrusaSlicer settings don't have direct OrcaSlicer equivalents or require manual intervention. These are listed in `NEEDS_CONVERTED.md` after conversion.

Common settings that need manual attention:

- `binary_gcode` - OrcaSlicer handles this differently
- `filament_ramming_parameters` - MMU-specific, may need adjustment
- `cooling_tube_*` - MMU-specific settings
- `enable_dynamic_fan_speeds` - Different implementation in OrcaSlicer
- Template variables in G-code that differ between slicers

### G-code Templates

While G-code is converted 1:1, OrcaSlicer uses different template variables in some cases:

- Variable names may differ (e.g., `[first_layer_temperature]` vs `{first_layer_temperature[0]}`)
- Some printer-specific features may not have equivalents
- Review and test G-code after conversion

## Files Structure

```
coreone/
├── prusa_to_orca_converter.py    # Main conversion script
├── profile_parser.py              # INI file parser
├── converters/
│   ├── __init__.py                # Module exports
│   ├── base.py                    # Base converter classes
│   ├── mapping_registry.py       # Setting mappings
│   └── profile_converters.py     # Profile-specific converters
├── 2.4.2.ini                      # PrusaSlicer profiles (input)
└── output/                        # Generated OrcaSlicer profiles
    ├── machine/
    ├── process/
    ├── filament/
    └── NEEDS_CONVERTED.md
```

## Examples

### Example 1: Convert All CORE One Profiles

```bash
python3 prusa_to_orca_converter.py 2.4.2.ini --printer "CORE One" --output-dir coreone_profiles
```

This creates:

- 2 machine models (standard + HF)
- ~27 machine variants (all nozzle sizes)
- ~300+ process profiles
- ~200+ filament profiles

### Example 2: Convert MK3S Profiles

```bash
python3 prusa_to_orca_converter.py 2.4.2.ini --printer "MK3S" --output-dir mk3s_profiles
```

### Example 3: Convert Everything

```bash
python3 prusa_to_orca_converter.py 2.4.2.ini --output-dir all_profiles
```

## Troubleshooting

### "No profiles found"

Make sure you're using the correct printer name. The filter is case-sensitive and matches partial names.

### "Settings not converted correctly"

Check `NEEDS_CONVERTED.md` for settings that weren't mapped. You can add mappings to `converters/mapping_registry.py`.

### "G-code not working in OrcaSlicer"

Review the start/end G-code and update template variables to match OrcaSlicer's syntax.

## Contributing

To add support for more settings:

1. Identify the PrusaSlicer setting name
2. Find the equivalent OrcaSlicer setting name
3. Add the mapping to the appropriate registry in `converters/mapping_registry.py`
4. Test the conversion
5. Update this README if needed

## License

This converter is provided as-is for converting between slicer formats. Use at your own risk and always verify converted profiles before printing.

## Credits

Created to facilitate conversion from PrusaSlicer to OrcaSlicer profiles, with a focus on extensibility and maintainability.
