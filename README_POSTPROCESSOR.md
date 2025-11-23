# Prusa Profile Post-Processor

The `prusa_postprocessor.py` script processes converted PrusaSlicer profiles to align them with OrcaSlicer naming conventions and filters them to match what's currently in OrcaSlicer.

## What It Does

1. **Preserves All Settings**: Keeps all converted settings intact - no data is removed
2. **Normalizes Printer Names**:
   - `@MK3` → `@MK3S`
   - `@MINI` → `@MINIIS`
   - `@XL` → `@Prusa XL`
   - `@XL 5T` → `@Prusa XL 5T`
3. **Fixes compatible_printers_condition**:
   - Converts `printer_model=~/(COREONE|COREONEMMU3)/`
   - To: `printer_notes=~/.*PRINTER_MODEL_COREONE.*/`
4. **Adds Missing printer_model Fields**: Automatically adds `printer_model` to profiles that don't have it
5. **Filters Profiles**: Only outputs profiles that exist in current OrcaSlicer (with exception for CORE One L)
6. **Updates Variables**: Changes PrusaSlicer variables to OrcaSlicer equivalents (e.g., `{printing_filament_types}` → `{filament_type[0]}`)

## Usage

### Basic Usage

```bash
python prusa_postprocessor.py --input output --output output_processed --orca-existing orca_existing
```

### Arguments

- `--input`, `-i`: Input directory with converted profiles (required)
- `--output`, `-o`: Output directory for processed profiles (required)
- `--orca-existing`, `-e`: Directory with existing OrcaSlicer profiles (default: `orca_existing`)
- `--no-core-one-l`: Filter out CORE One L profiles (default: allow them)

## Complete Workflow

1. **Convert PrusaSlicer profiles**:

   ```bash
   python prusa_to_orca_converter.py 2.4.2.ini --output-dir output
   ```

2. **Post-process to align with OrcaSlicer**:

   ```bash
   python prusa_postprocessor.py --input output --output output_processed --orca-existing orca_existing
   ```

3. **Result**: `output_processed/` contains profiles ready to drop into OrcaSlicer

## Output Stats

After processing, you get:

- **Process profiles**: ~154 (filtered from 519 converted)
- **Filament profiles**: ~34 (filtered from 5588 converted)
- **Machine profiles**: ~24 (filtered from 263 converted)

Only profiles that match existing OrcaSlicer profiles are included (plus CORE One L variants).

## Supported Printers

The post-processor handles all Prusa printers in OrcaSlicer:

- CORE One (including CORE One L)
- MK4S, MK4IS, MK4
- MINIIS, MINI
- MK3.5, MK3S, MK3
- XLIS, XL (including XL 5T)
- MK2.5

## Examples

### Profile Name Normalization

- `0.15mm SPEED @MK3 0.4` → `0.15mm SPEED @MK3S 0.4`
- `0.20mm Speed @XL 0.5` → `0.20mm Speed @Prusa XL 0.5`
- `Generic ABS @MINI` → `Generic ABS @MINIIS`

### Compatible Condition Conversion

```json
// Before
"compatible_printers_condition": "printer_model=~/(COREONE|COREONEMMU3)/ and nozzle_diameter[0]==0.4"

// After
"compatible_printers_condition": "printer_notes=~/.*PRINTER_MODEL_COREONE.*/ and nozzle_diameter[0]==0.4"
```

### Printer Model Assignment

```json
// Profile: "0.15mm SPEED @CORE One 0.4"
// Automatically adds:
"printer_model": "Prusa CORE One"
```
