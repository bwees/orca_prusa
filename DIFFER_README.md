# Profile Differ Tool

A tool to compare converted OrcaSlicer profiles with existing OrcaSlicer profiles by resolving all inheritance chains and showing concrete differences.

## Overview

The Profile Differ resolves all inheritance chains in both the converted and existing OrcaSlicer profiles to create "concrete" profiles (with all settings from parents merged in), then compares them to show:

- Settings only in converted profiles
- Settings only in OrcaSlicer profiles
- Settings with different values between the two

## Usage

### Basic Usage

```bash
# Compare a single profile
python profile_differ.py --converted <converted_dir> --orca <orca_dir> <type> "<profile_name>"

# Compare all profiles matching a filter
python profile_differ.py --converted <converted_dir> --orca <orca_dir> <type> --filter "<filter>"

# Compare all profiles of a type
python profile_differ.py --converted <converted_dir> --orca <orca_dir> <type> --all
```

### Arguments

- `--converted`: Directory containing converted profiles (required)
- `--orca`: Directory containing OrcaSlicer profiles (required)
- `profile_type`: Type of profile - `process`, `filament`, `machine`, or `machine_model` (required)
- `profile_name`: Specific profile name without `.json` extension (optional)
- `--filter`: Filter profiles by substring match (case-insensitive) (optional)
- `--all`: Compare all profiles of the given type (optional)
- `--verbose, -v`: Show detailed differences (optional)
- `--only-issues`: Only show profiles with missing or different settings, excluding profiles that only have extra settings (optional)

## Examples

### Compare a Single Process Profile

```bash
python profile_differ.py \
  --converted orca_output_test \
  --orca orca_existing \
  process \
  "0.15mm STRUCTURAL @COREONEL 0.6" \
  --verbose
```

Output:

```
================================================================================
Comparing: process/0.15mm STRUCTURAL @COREONEL 0.6
================================================================================

Summary:
  Settings only in converted: 67
  Settings only in OrcaSlicer: 0
  Settings with different values: 0

✓ Profiles are identical (after resolving inheritance)!
```

### Compare All CORE One 0.6 Process Profiles

```bash
python profile_differ.py \
  --converted orca_output_test \
  --orca orca_existing \
  process \
  --filter "COREONEL 0.6"
```

Output:

```
Found 7 profiles to compare
✗ 0.15mm STRUCTURAL @COREONEL 0.6 - 67 extra, 0 missing, 0 different
✗ 0.20mm SPEED @COREONEL 0.6 - 67 extra, 0 missing, 0 different
...
================================================================================
Summary: 0 identical, 7 different
================================================================================
```

### Compare Filament Profiles with Details

```bash
python profile_differ.py \
  --converted orca_output_test \
  --orca orca_existing \
  filament \
  "Prusament PLA @COREONE" \
  --verbose
```

### Compare All Profiles

```bash
python profile_differ.py \
  --converted orca_output_test \
  --orca orca_existing \
  process \
  --all
```

### Show Only Profiles with Issues

```bash
# Only show profiles with missing or different settings
python profile_differ.py \
  --converted orca_output_test \
  --orca orca_existing \
  process \
  --filter "CORE One" \
  --only-issues
```

## Understanding the Output

### Summary Line Format

```
✗ <profile_name> - <extra> extra, <missing> missing, <different> different
```

- **extra**: Settings present in converted but not in OrcaSlicer (after resolving inheritance)
- **missing**: Settings present in OrcaSlicer but not in converted
- **different**: Settings present in both but with different values

### Interpreting Results

**All zeros (0 extra, 0 missing, 0 different)**:

- ✓ Profiles are perfectly identical after resolving inheritance
- Values match exactly

**Non-zero "extra" but 0 "different"**:

- Converted profile explicitly defines settings that OrcaSlicer inherits from parents
- This is normal and not an error - it means the converter is flattening inheritance
- As long as "different" is 0, the values are correct
- Use `--only-issues` to filter these out when looking for actual problems

**Non-zero "missing"**:

- OrcaSlicer has settings that the converted profile doesn't have
- May indicate missing mappings or settings that need to be added

**Non-zero "different"**:

- ⚠️ Values don't match between converted and OrcaSlicer
- This indicates potential conversion errors that should be investigated

### Verbose Mode

With `--verbose`, you'll see detailed listings of:

1. **Settings only in CONVERTED**: Full list with values
2. **Settings only in ORCASLICER**: Full list with values
3. **Settings with DIFFERENT VALUES**: Side-by-side comparison
   ```
   setting_name:
     Converted:  <value1>
     OrcaSlicer: <value2>
   ```

## How Inheritance Resolution Works

The differ recursively resolves inheritance chains:

1. Load the profile
2. If it has an `inherits` field, recursively resolve parent(s)
3. Merge parent settings (later parents override earlier ones)
4. Apply the profile's own settings (override parent settings)
5. Return fully concrete profile

This allows comparing what the actual final settings would be when a profile is used, rather than just comparing the JSON files directly.

## Common Use Cases

### Validate Conversion Accuracy

```bash
# Check if all CORE One profiles converted correctly
python profile_differ.py \
  --converted orca_output_test \
  --orca orca_existing \
  process \
  --filter "COREONE" \
  --verbose
```

### Find Missing Settings

Look for profiles with non-zero "missing" counts to identify settings that need mapping.

### Verify Value Transformations

Use `--verbose` to see specific value differences when "different" count is non-zero.

### Compare Specific Printer

```bash
# Compare all MK4S profiles
python profile_differ.py \
  --converted orca_output_test \
  --orca orca_existing \
  process \
  --filter "MK4S"
```

## Tips

- The tool caches loaded profiles for performance
- Profile names are case-sensitive in the file system but filtering is case-insensitive
- Use `--filter` for partial name matching (e.g., "STRUCTURAL" matches all structural profiles)
- Start without `--verbose` to get a quick overview, then use `--verbose` on specific profiles
- "extra" settings in converted profiles are usually fine - they just mean inheritance was flattened
- Use `--only-issues` to focus on profiles that have missing settings or different values, ignoring profiles with only extra settings

## Troubleshooting

**"No profiles found matching filter"**:

- Check that the converted directory contains the expected profiles
- Verify the filter string matches profile names (case-insensitive)
- Try `--all` to see all available profiles

**"Error loading profile"**:

- Ensure both directories exist and contain valid JSON files
- Check file permissions

**Circular inheritance warning**:

- Indicates a profile inherits from itself (directly or indirectly)
- This is usually an error in the profile data
