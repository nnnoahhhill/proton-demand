# ProtoGo Quoting Algorithm Documentation

## Overview

The ProtoGo quoting system calculates manufacturing costs for 3D printed parts based on material usage, print time, and manufacturing method. This document provides a detailed breakdown of all variables that impact the final quote price.

## Core Pricing Formula

The fundamental pricing formula is:

```
Total Cost = Material Cost + Machine Cost
```

Where:
- **Material Cost** = (Material Usage in kg) × (Material Cost per kg)
- **Machine Cost** = (Print Time in hours) × (Machine Cost per hour)

## Material Usage Calculation

The material usage is calculated differently based on the manufacturing method:

### For SLA Printing

```python
support_factor = 1.1  # 10% extra for supports
material_usage_g = volume_cm3 * material_density * support_factor
```

### For FDM Printing

```python
shell_factor = 0.3  # 30% for outer shells
infill_factor = infill_density / 100
effective_volume = volume_cm3 * (shell_factor + (1-shell_factor) * infill_factor)
material_usage_g = effective_volume * material_density
```

### For SLS Printing

```python
packing_factor = 1.05  # 5% extra for powder packing inefficiency
waste_factor = 1.4     # 40% powder waste/recycling rate
material_usage_g = volume_cm3 * material_density * packing_factor * waste_factor
```

## Configurable Variables

| Variable | Default Value | Description | Impact on Quote |
|----------|---------------|-------------|----------------|
| `material_cost_per_kg` | 50.0 | Cost of material per kilogram | Directly proportional to material cost |
| `material_density` | 1.1 g/cm³ | Density of material | Affects material usage calculation |
| `machine_cost_per_hour` | 3.0 | Operating cost of printer per hour | Directly proportional to machine cost |
| `support_factor` | 1.1 | Additional material for SLA supports | 10% increase in material for SLA prints |
| `infill_density` | Varies | Percentage of interior fill (FDM) | Higher density increases material usage |
| `shell_factor` | 0.3 | Percentage of volume for outer shells | Affects material calculation for FDM |
| `packing_factor` | 1.05 | Powder packing inefficiency (SLS) | 5% increase in material for SLS prints |
| `waste_factor` | 1.4 | Powder waste/recycling rate (SLS) | 40% increase in material for SLS prints |
| `parts_per_batch` | 10 | Average parts in an SLS batch | Reduces per-part machine time for SLS |

## Print Time Estimation

Print time is calculated based on:

1. **Detailed Method** (using external slicer):
   - Obtained directly from slicer output

2. **Simplified Estimation**:
   - Based on volume, printer speed, and complexity factors
   - SLA print time depends on layer height and laser speed
   - FDM print time depends on print speed and travel
   - SLS print time includes batch processing overhead with per-layer time

### SLS-Specific Time Factors

```python
# Base time per layer for SLS
time_per_layer_sec = 15  # seconds per layer including powder spreading

# Pre-heating and cooldown add significant time to SLS
base_machine_time_min = 180  # 3 hours for preheating and cooldown
parts_per_batch = 10  # Average parts in an SLS batch
batch_overhead_min = base_machine_time_min / parts_per_batch

# Calculate print time with batch overhead
total_print_time_sec = (layer_count * time_per_layer_sec) + (batch_overhead_min * 60)
```

## Shapeways Price Comparison

The system includes a comparison with Shapeways pricing:

### Material Price per cm³

| Material | Price per cm³ |
|----------|---------------|
| Accura 60 (SLA) | $2.50 |
| Strong & Flexible Plastic (SLS Nylon) | $2.10 |
| White Strong & Flexible | $1.80 |
| White Detail Resin | $3.00 |
| Black Professional Plastic | $2.00 |
| Versatile Plastic | $1.90 |

### Shapeways Formula

```
Shapeways Price = (Volume in cm³ × Price per cm³) + Base Fee
```

Where:
- **Base Fee** = $7.50 (handling fee)

## Quote Adjustment Factors

The following factors can be adjusted to influence the final quote:

1. **Material Cost**: Changing material_cost_per_kg directly impacts material cost
2. **Machine Cost**: Adjusting machine_cost_per_hour affects time-based costs
3. **Support Factor**: Increasing this adds more material for complex geometries
4. **Infill Density**: Higher density increases material usage for FDM prints

## Command Line Parameters

You can adjust pricing parameters via command line:

```
python dfm/dfm-analyzer.py <input_file> --material-cost 60.0 --machine-cost 4.0
```

## Quote Example Calculation

### SLA Example

For a 100cm³ SLA print with 5 hour print time:

1. **Material Usage**: 
   ```
   100 cm³ × 1.1 g/cm³ × 1.1 (support) = 121g = 0.121kg
   ```

2. **Material Cost**:
   ```
   0.121kg × $50/kg = $6.05
   ```

3. **Machine Cost**:
   ```
   5 hours × $3/hour = $15.00
   ```

4. **Total Cost**:
   ```
   $6.05 + $15.00 = $21.05
   ```

### SLS Example

For a 100cm³ SLS print with 3 hour print time:

1. **Material Usage**: 
   ```
   100 cm³ × 1.1 g/cm³ × 1.05 (packing) × 1.4 (waste) = 161.7g = 0.1617kg
   ```

2. **Material Cost**:
   ```
   0.1617kg × $50/kg = $8.09
   ```

3. **Machine Cost** (including batching efficiency):
   ```
   3 hours × $3/hour = $9.00
   ```

4. **Total Cost**:
   ```
   $8.09 + $9.00 = $17.09
   ```

## Comparison with Shapeways:

### SLA Comparison

```
Shapeways SLA: (100cm³ × $2.50/cm³) + $7.50 = $257.50
Internal SLA Quote: $21.05
Difference: $236.45 (91.8% less)
```

### SLS Comparison

```
Shapeways SLS Nylon: (100cm³ × $2.10/cm³) + $7.50 = $217.50
Internal SLS Quote: $17.09
Difference: $200.41 (92.1% less)
```

## Recommendations for Quote Adjustment

1. **Increase Accuracy**: Integrate with more advanced slicers for precise material and time estimates
2. **Add Markup**: Implement percentage markup for profit margin
3. **Volume Discounts**: Add tiered pricing for larger prints
4. **Labor Costs**: Include manual post-processing time for complex parts
5. **Rush Fees**: Implement priority pricing for expedited orders
6. **SLS Batch Optimization**: Adjust batch size parameters based on actual machine capacity
7. **Material Waste Recovery**: Fine-tune waste factors based on powder recycling efficiency
8. **Density Adjustment**: Calibrate material density values for each specific SLS powder type

By adjusting these variables, the ProtoGo quoting system can be fine-tuned to balance competitive pricing with profitability across all three printing technologies (SLA, FDM, and SLS).