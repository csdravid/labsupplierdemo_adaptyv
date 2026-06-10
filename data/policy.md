# Supplier reorder policy

> Tuned for lab-supplier-agent-v2 inventory (Gemini research + CH suppliers).
> Supplier names below must match `supplier` column in `data/inventory.csv`.

## Defaults
- Ship-to: Adaptyv Biosystems, EPFL Innovation Park, Lausanne
- Requester: Lab Operations
- Currency: CHF

## Finance defaults
- Standard shipping CHF: 25
- Expedite flat surcharge CHF: 150
- Expedite percent surcharge: 40
- Expedite model: max(flat, percent)

## Per-SKU overrides (optional)
- A1435101: reorder_qty 2
- E2621S: reorder_qty 3

## Supplier lead times (days)
- BioConcept: 3
- Sigma-Aldrich: 5
- Thermo Fisher: 3
- Cytiva: 4
- Starlab CH: 2
- Greiner Bio-One: 3
- Macherey-Nagel: 5
