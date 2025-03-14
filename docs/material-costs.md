# 3D Printer and CNC Material Cost Analysis

## 3D Printer Material Costs (Per KG)

| Category | Material           | Price/KG    | Density (g/cm³) | Cost Factor (vs. Cheapest) |
|----------|-------------------|-------------|----------------|----------------------------|
| FDM      | PLA               | $18-22      | 1.24-1.30      | 1.0x                       |
| FDM      | ABS               | $22-26      | 1.04-1.06      | 1.2x                       |
| FDM      | Nylon 12          | $60-80      | 1.01-1.04      | 3.5x                       |
| FDM      | ASA               | $28-35      | 1.05-1.07      | 1.6x                       |
| FDM      | PETG              | $22-28      | 1.27-1.29      | 1.3x                       |
| FDM      | TPU               | $40-55      | 1.21-1.25      | 2.4x                       |
| SLA      | Standard Resin    | $65-85      | 1.10-1.20      | 3.8x                       |
| SLS      | Nylon 12 (White)  | $80-120     | 0.95-1.00      | 5.0x                       |
| SLS      | Nylon 12 (Black)  | $85-125     | 0.95-1.00      | 5.3x                       |

## CNC Material Costs (Per KG)

| Category | Material              | Price/KG    | Density (g/cm³) | Cost Factor (vs. Cheapest) |
|----------|----------------------|-------------|----------------|----------------------------|
| Metal    | Mild Steel           | $2-4        | 7.85-7.87      | 1.0x                       |
| Metal    | Aluminum 6061        | $6-8        | 2.70-2.72      | 2.3x                       |
| Metal    | 304 Stainless Steel  | $8-12       | 7.93-8.00      | 3.3x                       |
| Metal    | 316 Stainless Steel  | $12-16      | 7.98-8.03      | 4.7x                       |
| Metal    | Titanium             | $80-120     | 4.43-4.51      | 33.3x                      |
| Metal    | Copper               | $12-18      | 8.92-8.96      | 5.0x                       |
| Metal    | Brass                | $10-15      | 8.40-8.73      | 4.2x                       |
| Plastic  | HDPE                 | $3-5        | 0.94-0.97      | 1.0x                       |
| Plastic  | POM (Acetal)         | $8-12       | 1.41-1.43      | 2.5x                       |
| Plastic  | ABS                  | $6-9        | 1.04-1.06      | 1.9x                       |
| Plastic  | Acrylic              | $7-11       | 1.17-1.20      | 2.3x                       |
| Plastic  | Nylon                | $12-18      | 1.13-1.15      | 3.8x                       |
| Plastic  | PEEK                 | $300-500    | 1.26-1.32      | 100.0x                     |
| Plastic  | PC (Polycarbonate)   | $15-25      | 1.20-1.22      | 5.0x                       |

## Volume Comparison (1kg of material)

| Material              | Volume per 1kg (cm³) | Relative Volume (vs. Steel) |
|----------------------|---------------------|----------------------------|
| PLA                  | 769-806             | 6.1x                       |
| ABS                  | 943-962             | 7.5x                       |
| Nylon 12             | 962-990             | 7.7x                       |
| PETG                 | 775-787             | 6.2x                       |
| TPU                  | 800-826             | 6.5x                       |
| PEEK                 | 758-794             | 6.1x                       |
| PC (Polycarbonate)   | 820-833             | 6.5x                       |
| Mild Steel           | 127-127.4           | 1.0x                       |
| Aluminum 6061        | 368-370             | 2.9x                       |
| Titanium             | 222-226             | 1.8x                       |
| Copper               | 112-112.1           | 0.9x                       |
| HDPE                 | 1031-1064           | 8.3x                       |

## CNC Finishes (Estimated Costs)

### Plastic Finishes

| Finish         | Price/KG (or Fixed Cost) | Notes                     |
|----------------|--------------------------|---------------------------|
| Deburr edges   | Free-$5                  | Standard in most quotes   |
| Electroplated  | +$18-25/kg               | Adds conductivity/gloss   |
| Sand Blasted   | +$8-12/kg                | Matte texture             |
| Painted        | +$12-20/kg               | Color customization       |

### Metal Finishes

| Finish         | Price/KG (or Fixed Cost) | Notes                     |
|----------------|--------------------------|---------------------------|
| Deburr edges   | Free-$5                  | Standard in most quotes   |
| Anodized       | +$12-18/kg               | Only for Al, Ti, Cu       |
| Sand Blasted   | +$8-15/kg                | Uniform matte finish      |
| Polished       | +$18-25/kg               | Mirror-like shine         |
| Brushed        | +$10-15/kg               | Directional satin texture |
| Electropolish  | +$25-40/kg               | Enhanced corrosion resist |
| Powder Coated  | +$15-25/kg               | Durable colored coating   |

## Sources

1. Formlabs pricing information for SLS powders (2024): https://formlabs.com/store/materials/nylon-12-white-powder/ - Indicates bulk pricing for SLS powders can reach as low as $45/kg
2. CNC Kitchen comparison of PLA, PETG & ASA (2023): https://www.cnckitchen.com/blog/comparing-pla-petg-amp-asa-feat-prusament - Prusament PLA sells for €25, PETG and ASA for €30
3. 3DSourced filament guide (2024): https://www.3dsourced.com/guides/3d-printer-filament/ - PLA and ABS start around $20/kg, PETG around $25/kg
4. VoxelMatters article on Formlabs pricing (2024): https://www.voxelmatters.com/formlabs-launches-10k-form-4l-large-scale-sla-3d-printer/ - Bulk pricing for SLA resin at $35/liter
5. Plasticker raw materials price database (2024): https://plasticker.de/preise/pms_en.php - Current market prices for various plastic materials
6. BeePlastic article on PEEK plastic pricing (2023): https://www.beeplastic.com/blogs/plastic-insights/why-peek-plastic-is-more-expensive-than-other-materials - Explains why PEEK is significantly more expensive
7. Metal price charts from Alumeco (2024): https://www.alumeco.com/metal-prices/ - Current metal prices for aluminum, copper, brass
8. D&D Scrap Metal current market prices (2024): https://dndscrapmetal.com/current-market-prices/ - Pricing for various aluminum grades including 6061
9. ECOREPRAP guide on sandblasting aluminum (2024): https://ecoreprap.com/cnc-machining/sand-blasting-aluminium/ - Information on finishing processes
10. Hubs surface finishing services pricing (2024): https://www.hubs.com/surface-finishing-services/brushing-electropolishing-services/ - Quotes for brushed and electropolished parts
11. Simplify3D Material Properties Table: https://www.simplify3d.com/resources/materials-guide/properties-table/ - Density values for 3D printing materials
12. Bitfab blog on 3D printing material densities: https://bitfab.io/blog/3d-printing-materials-densities/ - Comprehensive density information
13. MatWeb material property database: https://www.matweb.com/ - Density values for metals and engineering plastics
14. Omnexus Polymer Density Technical Properties: https://omnexus.specialchem.com/polymer-property/density - Detailed plastic density information

*Note: Prices are presented as ranges based on current market data as of 2024. Actual prices may vary based on supplier, quantity, quality, and market conditions. Cost factors are calculated using the midpoint of each price range compared to the cheapest option in each category. The volume comparison table shows how much physical volume you get per kilogram of each material, highlighting why lightweight materials like HDPE provide much more volume per dollar than dense metals like steel or copper.* 