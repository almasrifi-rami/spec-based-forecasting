"""
Synthetic B2B ERP Data Generator for Spec-Based Forecasting (Option A: Medical & Industrial Gloves)
Generates 5 raw tables in DuckDB (`raw_erp` schema) with realistic cross-SKU substitution,
customer segment dynamics, Pareto whale concentration, and messy ERP master data strings.
"""

from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

# Set fixed random seed for reproducibility across runs
SEED = 42
rng = np.random.default_rng(SEED)

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

# Simulation window: 2 years of daily B2B data up to October 2026
START_DATE = pd.Timestamp("2024-10-01")
END_DATE = pd.Timestamp("2026-10-18")
ALL_DATES = pd.date_range(START_DATE, END_DATE, freq="D")


def generate_suppliers() -> pd.DataFrame:
    """Generates raw_erp.suppliers with Asian sea-freight vs. EU buffer factories."""
    suppliers = [
        {
            "supplier_id": "SUP-001",
            "supplier_name": "Selangor MedGlove Manufacturing Sdn Bhd",
            "country_raw": "MY",
            "base_lead_time_days": 75,
            "moq_cases": 200,
            "reliability_score": 0.91,
            "currency_code": "USD",
            "updated_at": "2025-01-15 08:30:00",
        },
        {
            "supplier_id": "SUP-002",
            "supplier_name": "Kuala Lumpur Nitrile Tech Ltd.",
            "country_raw": "Malaysia",
            "base_lead_time_days": 82,
            "moq_cases": 250,
            "reliability_score": 0.87,
            "currency_code": "USD",
            "updated_at": "2025-03-10 11:15:00",
        },
        {
            "supplier_id": "SUP-003",
            "supplier_name": "Rayong Latex & Polymer Co.",
            "country_raw": "TH",
            "base_lead_time_days": 68,
            "moq_cases": 150,
            "reliability_score": 0.93,
            "currency_code": "USD",
            "updated_at": "2025-02-01 09:00:00",
        },
        {
            "supplier_id": "SUP-004",
            "supplier_name": "Silesia PPE Buffer Logistics Sp. z o.o.",
            "country_raw": "PL",
            "base_lead_time_days": 14,
            "moq_cases": 30,
            "reliability_score": 0.97,
            "currency_code": "EUR",
            "updated_at": "2025-06-20 14:45:00",
        },
        {
            "supplier_id": "SUP-005",
            "supplier_name": "Danube Industrial Safety Kft",
            "country_raw": "Hungary",
            "base_lead_time_days": 10,
            "moq_cases": 20,
            "reliability_score": 0.96,
            "currency_code": "EUR",
            "updated_at": "2025-08-05 16:20:00",
        },
        {
            "supplier_id": "SUP-006",
            "supplier_name": "Ningbo Vinyl & Disposable Corp",
            "country_raw": "CN",
            "base_lead_time_days": 90,
            "moq_cases": 300,
            "reliability_score": 0.83,
            "currency_code": "USD",
            "updated_at": "2025-04-12 07:10:00",
        },
    ]
    return pd.DataFrame(suppliers)


def generate_customers() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generates raw_erp.customers across 4 B2B segments with Pareto whale weights
    and dirty ERP strings. Returns (dirty_df_for_db, clean_df_for_sim).
    """
    segments = [
        ("Healthcare_Hospital", 0.35, "Same_Material_Weight_Only"),
        ("Dental_Clinic_Dist", 0.25, "Same_Material_Color_Flex"),
        ("Industrial_Auto", 0.25, "Weight_Up_Or_Color_Flex"),
        ("Lab_Pharma", 0.15, "Same_Material_Weight_Only"),
    ]
    countries = ["DE", "Germany", "HU", "Hungary", "AT", "NL", "PL", "CZ", "RO"]
    contract_tiers = ["Contract_Fixed", "Framework_Annual", "Spot_Buyer"]

    clean_rows = []
    dirty_rows = []

    for idx in range(1, 86):
        cust_id = f"CUST-{idx:03d}"
        seg_choice = rng.choice(len(segments), p=[s[1] for s in segments])
        seg_name, _, subst_rule = segments[seg_choice]

        # Pareto power-law weight: a few huge "whale" distributors/hospitals per segment
        pareto_weight = float(rng.pareto(a=1.6) + 0.35)
        if idx in (1, 2, 3, 12, 25, 41):  # Intentional top whales
            pareto_weight *= 3.5

        country = rng.choice(countries)
        tier = rng.choice(contract_tiers, p=[0.45, 0.30, 0.25])

        # Introduce messy segment formatting in the raw ERP table
        seg_dirty_map = {
            "Healthcare_Hospital": ["Healthcare_Hospital", "HEALTHCARE", "Hospital / Clinical", "Healthcare - Hosp"],
            "Dental_Clinic_Dist": ["Dental_Clinic_Dist", "DENTAL", "Dental Distributor", "Dental & Clinic"],
            "Industrial_Auto": ["Industrial_Auto", "INDUSTRIAL", "Auto / Manufacturing", "Industrial & Auto"],
            "Lab_Pharma": ["Lab_Pharma", "PHARMA_LAB", "Lab & Diagnostics", "Pharma / Lab"],
        }
        seg_raw = rng.choice(seg_dirty_map[seg_name])

        credit_limit = round(pareto_weight * 45000, -2)
        payment_terms = int(rng.choice([15, 30, 45, 60, 90]))

        clean_rows.append(
            {
                "customer_id": cust_id,
                "customer_segment_clean": seg_name,
                "subst_rule": subst_rule,
                "pareto_weight": pareto_weight,
                "contract_tier": tier,
            }
        )

        dirty_rows.append(
            {
                "customer_id": cust_id,
                "customer_name": f"{seg_name.split('_')[0]} Partner Group #{idx:02d} ({country[:2].upper()})",
                "customer_segment_raw": seg_raw,
                "country_raw": country,
                "contract_tier_raw": tier if rng.random() > 0.08 else tier.lower(),
                "preferred_substitute_rule": subst_rule,
                "credit_limit_eur": credit_limit if rng.random() > 0.05 else None,
                "payment_terms_days": payment_terms,
                "created_date": (START_DATE - pd.Timedelta(days=int(rng.integers(30, 900)))).strftime("%Y-%m-%d"),
            }
        )

    return pd.DataFrame(dirty_rows), pd.DataFrame(clean_rows)


def generate_items() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generates ~64 glove SKUs with structured specs for simulation and messy ERP strings
    (dirty weights, sizes, materials, UoMs, and a few duplicate extract rows) for dbt Staging.
    """
    # Product spec combinations: (material, weight_g, colors, base_cost_per_1000_pcs, primary_suppliers)
    spec_archetypes = [
        ("Nitrile", 3.2, ["Blue", "Violet", "White"], 21.0, ["SUP-001", "SUP-002"]),
        ("Nitrile", 3.5, ["Blue", "Cobalt", "Violet", "White"], 23.5, ["SUP-001", "SUP-002", "SUP-004"]),
        ("Nitrile", 4.5, ["Blue", "Cobalt", "Black"], 29.0, ["SUP-002", "SUP-004"]),
        ("Nitrile", 6.0, ["Black", "Orange", "Cobalt"], 38.0, ["SUP-002", "SUP-005"]),
        ("Latex", 3.5, ["White", "Natural"], 19.5, ["SUP-003", "SUP-005"]),
        ("Latex", 4.5, ["White", "Natural"], 24.0, ["SUP-003"]),
        ("Vinyl", 3.2, ["Clear", "Blue"], 13.5, ["SUP-006", "SUP-005"]),
    ]
    sizes = ["XS", "S", "M", "L", "XL"]
    size_velocity_mult = {"XS": 0.35, "S": 0.85, "M": 1.65, "L": 1.35, "XL": 0.55}

    # Dirty formatting maps to challenge dbt staging models
    material_dirty_map = {
        "Nitrile": ["Nitrile", "NITRILE", "nitrile_exam", "NBR (Nitrile)"],
        "Latex": ["Latex", "LATEX", "Nat. Latex", "Natural Rubber Latex"],
        "Vinyl": ["Vinyl", "VINYL", "PVC/Vinyl", "Synthetic Vinyl"],
    }
    size_dirty_map = {
        "XS": ["XS", "Extra Small", "5-6 (XS)", "SZ-XS"],
        "S": ["S", "Small", "6-7 (S)", "SZ-S"],
        "M": ["M", "Medium", "7-8 (M)", "SZ-M", "m"],
        "L": ["L", "Large", "8-9 (L)", "SZ-L"],
        "XL": ["XL", "Extra Large", "9-10 (XL)", "SZ-XL"],
    }

    clean_items = []
    dirty_items = []
    sku_counter = 100

    for material, weight_g, colors, cost_per_1k, sups in spec_archetypes:
        for color in colors:
            for size in sizes:
                # Skip a few rare combinations so we get ~65 realistic SKUs
                if material == "Vinyl" and size in ("XS", "XL"):
                    continue
                if weight_g == 6.0 and size in ("XS", "S"):
                    continue

                sku_counter += 1
                item_id = f"ITM-{sku_counter}"
                sku_code = f"GLV-{material[:3].upper()}-{color[:3].upper()}-{size}-{int(weight_g*10)}"

                # Pack UoM: lighter exam gloves sometimes come in BOX_200, heavy ones in BOX_100
                box_pieces = 200 if (weight_g == 3.2 and color in ("Blue", "Violet")) else 100
                default_uom = "BOX_200" if box_pieces == 200 else "BOX_100"

                unit_cost_box = round((cost_per_1k / 1000.0) * box_pieces * rng.uniform(0.96, 1.05), 2)
                list_price_box = round(unit_cost_box * rng.uniform(1.38, 1.62), 2)
                supplier_id = rng.choice(sups)

                # Cold-start SKUs: 6 items launched recently (Sept 2026)
                is_cold_start = sku_counter in (108, 119, 134, 147, 158, 166)
                launch_date = (
                    pd.Timestamp("2026-09-07")
                    if is_cold_start
                    else START_DATE - pd.Timedelta(days=int(rng.integers(60, 720)))
                )

                # Base weekly demand in boxes
                mat_mult = 1.4 if material == "Nitrile" else (0.75 if material == "Latex" else 0.55)
                color_mult = 1.35 if color in ("Blue", "White", "Black") else 0.70
                base_daily_boxes = max(
                    4.0,
                    22.0 * mat_mult * color_mult * size_velocity_mult[size] * rng.uniform(0.8, 1.25),
                )

                clean_items.append(
                    {
                        "item_id": item_id,
                        "sku_code": sku_code,
                        "material_clean": material,
                        "size_clean": size,
                        "color_clean": color,
                        "weight_g_clean": weight_g,
                        "box_pieces": box_pieces,
                        "default_uom": default_uom,
                        "unit_cost_box_eur": unit_cost_box,
                        "list_price_box_eur": list_price_box,
                        "primary_supplier_id": supplier_id,
                        "launch_date": launch_date,
                        "is_cold_start": is_cold_start,
                        "base_daily_boxes": base_daily_boxes,
                    }
                )

                # Format messy weight string for raw ERP
                weight_formats = [
                    f"{weight_g:.1f}g",
                    f"{weight_g:.1f} g",
                    f"{str(weight_g).replace('.', ',')}g",
                    f"{int(weight_g * 1000)}mg",
                    f"{weight_g:.1f} GR",
                ]
                weight_raw = rng.choice(weight_formats)

                uom_dirty_map = {
                    "BOX_100": ["BOX_100", "BX100", "Box of 100", "100/BOX"],
                    "BOX_200": ["BOX_200", "BX200", "Box of 200", "200/BOX"],
                }

                dirty_row = {
                    "item_id": item_id,
                    "sku_code": sku_code,
                    "item_description_raw": f"{material.upper()} GLOVE {color.upper()} ({size}) - {weight_raw} [{default_uom}]",
                    "material_raw": rng.choice(material_dirty_map[material]),
                    "size_raw": rng.choice(size_dirty_map[size]),
                    "color_raw": color if rng.random() > 0.15 else color.upper(),
                    "weight_raw": weight_raw,
                    "order_uom_raw": rng.choice(uom_dirty_map[default_uom]),
                    "cases_per_pallet": int(rng.choice([48, 60, 72])),
                    "boxes_per_case": 10,
                    "unit_cost_eur": unit_cost_box,
                    "list_price_eur": list_price_box,
                    "primary_supplier_id": supplier_id,
                    "launch_date": launch_date.strftime("%Y-%m-%d"),
                    "is_active_raw": rng.choice(["Y", "YES", "1", "True"]),
                    "erp_extracted_at": "2026-10-19 02:00:00",
                }
                dirty_items.append(dirty_row)

                # Inject 3 duplicate ERP item master records with older timestamps for dbt deduplication practice
                if sku_counter in (105, 122, 140):
                    dup_row = dirty_row.copy()
                    dup_row["unit_cost_eur"] = round(unit_cost_box * 0.94, 2)
                    dup_row["erp_extracted_at"] = "2026-05-01 02:00:00"
                    dirty_items.append(dup_row)

    return pd.DataFrame(dirty_items), pd.DataFrame(clean_items)


def simulate_inventory_and_orders(
    clean_items: pd.DataFrame, clean_customers: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Simulates 2 years of daily inventory and B2B customer sales orders, including:
    - Planned multi-week stockouts on high-runner SKUs
    - Spec-based cross-SKU substitution when stockouts happen
    - Pareto customer concentration & random one-off tender orders
    - Messy UoM mixes (Boxes vs. Cases of 10 Boxes) and ERP noise
    """
    items_dict = clean_items.set_index("item_id").to_dict("index")
    item_ids = list(items_dict.keys())

    # Pre-compute spec-compatible substitute pairs for each item:
    # 1) Same material + size + weight_g, different color (Clinical/Hospital preference)
    # 2) Same material + size, heavier weight_g (Industrial preference)
    same_spec_diff_color = {}
    heavier_spec_same_size = {}

    for iid, spec in items_dict.items():
        if spec["is_cold_start"]:
            same_spec_diff_color[iid] = []
            heavier_spec_same_size[iid] = []
            continue
        color_peers = [
            other_id
            for other_id, o in items_dict.items()
            if other_id != iid
            and not o["is_cold_start"]
            and o["material_clean"] == spec["material_clean"]
            and o["size_clean"] == spec["size_clean"]
            and o["weight_g_clean"] == spec["weight_g_clean"]
        ]
        weight_peers = [
            other_id
            for other_id, o in items_dict.items()
            if other_id != iid
            and not o["is_cold_start"]
            and o["material_clean"] == spec["material_clean"]
            and o["size_clean"] == spec["size_clean"]
            and o["weight_g_clean"] > spec["weight_g_clean"]
        ]
        same_spec_diff_color[iid] = color_peers
        heavier_spec_same_size[iid] = weight_peers

    # Select 8 high-velocity non-cold-start SKUs to suffer realistic 18-to-24 day stockouts
    eligible_for_stockout = [
        iid
        for iid, s in items_dict.items()
        if not s["is_cold_start"] and len(same_spec_diff_color[iid]) > 0 and s["size_clean"] in ("M", "L", "S")
    ]
    stockout_skus = rng.choice(eligible_for_stockout, size=min(8, len(eligible_for_stockout)), replace=False)

    # Define 3 stockout windows per selected SKU across the 2-year timeline
    stockout_windows = {}
    for iid in stockout_skus:
        windows = [
            (pd.Timestamp("2025-02-10"), pd.Timestamp("2025-03-02")),
            (pd.Timestamp("2025-11-03"), pd.Timestamp("2025-11-24")),
            (pd.Timestamp("2026-07-13"), pd.Timestamp("2026-08-03")),
        ]
        stockout_windows[iid] = windows

    # Map segments to preferred product specs
    seg_customers = {}
    for seg_name, grp in clean_customers.groupby("customer_segment_clean"):
        weights = grp["pareto_weight"].to_numpy()
        weights = weights / weights.sum()
        seg_customers[seg_name] = (grp["customer_id"].to_numpy(), weights)

    inventory_records = []
    order_records = []
    order_seq = 100000

    for current_date in ALL_DATES:
        day_of_week = current_date.day_of_week  # B2B orders mostly Mon-Fri (0-4)
        month = current_date.month

        # Seasonal multipliers: Q4/Q1 winter healthcare surge, Q2/Q3 industrial surge
        healthcare_season = 1.25 if month in (11, 12, 1, 2) else (0.90 if month in (7, 8) else 1.0)
        industrial_season = 1.20 if month in (4, 5, 6, 9, 10) else 0.92

        # Determine which SKUs are stocked out today
        stocked_out_today = set()
        for iid, windows in stockout_windows.items():
            for w_start, w_end in windows:
                if w_start <= current_date <= w_end:
                    stocked_out_today.add(iid)

        # Track daily inventory snapshots
        for iid in item_ids:
            spec = items_dict[iid]
            if current_date < spec["launch_date"]:
                continue

            is_out = iid in stocked_out_today
            if is_out:
                on_hand_boxes = 0
                in_transit_boxes = int(spec["base_daily_boxes"] * rng.integers(14, 30))
            else:
                # Normal inventory fluctuations + occasional -1 ERP glitch (0.2% of rows)
                on_hand_boxes = int(spec["base_daily_boxes"] * rng.uniform(12, 42))
                if rng.random() < 0.002:
                    on_hand_boxes = -1  # ERP sync glitch for dbt staging to clean!
                in_transit_boxes = (
                    int(spec["base_daily_boxes"] * rng.uniform(10, 25)) if rng.random() < 0.35 else 0
                )

            inventory_records.append(
                {
                    "snapshot_date": current_date.strftime("%Y-%m-%d"),
                    "item_id": iid,
                    "warehouse_code": "WH-CENTRAL-EU",
                    "on_hand_uom_qty": on_hand_boxes,
                    "uom_code_raw": spec["default_uom"],
                    "in_transit_po_uom_qty": in_transit_boxes,
                    "stockout_flag_raw": "Y" if is_out else ("N" if rng.random() > 0.1 else "0"),
                }
            )

        # Skip Sunday order generation (B2B ERP rarely books Sunday orders)
        if day_of_week == 6:
            continue
        weekend_dampener = 0.25 if day_of_week == 5 else 1.0

        # Generate daily customer orders per item
        for iid in item_ids:
            spec = items_dict[iid]
            if current_date < spec["launch_date"]:
                continue

            # Pick primary segment based on glove weight & material
            if spec["weight_g_clean"] >= 4.5:
                seg_probs = [0.10, 0.05, 0.70, 0.15]  # Industrial heavy
                season_mult = industrial_season
            elif spec["material_clean"] == "Latex":
                seg_probs = [0.40, 0.45, 0.05, 0.10]
                season_mult = healthcare_season
            else:
                seg_probs = [0.45, 0.25, 0.10, 0.20]
                season_mult = healthcare_season

            expected_orders_today = (
                (spec["base_daily_boxes"] / 18.0) * season_mult * weekend_dampener
            )
            num_orders = rng.poisson(lam=max(0.15, expected_orders_today))

            for _ in range(num_orders):
                seg_name = rng.choice(
                    ["Healthcare_Hospital", "Dental_Clinic_Dist", "Industrial_Auto", "Lab_Pharma"],
                    p=seg_probs,
                )
                cust_ids, cust_weights = seg_customers[seg_name]
                cust_id = str(rng.choice(cust_ids, p=cust_weights))

                target_item_id = iid
                is_sub_order = False
                orig_requested_id = None

                # Stockout substitution logic!
                if iid in stocked_out_today:
                    if seg_name in ("Healthcare_Hospital", "Lab_Pharma", "Dental_Clinic_Dist"):
                        candidates = same_spec_diff_color[iid]
                        sub_prob = 0.72
                    else:
                        candidates = same_spec_diff_color[iid] + heavier_spec_same_size[iid]
                        sub_prob = 0.65

                    # Filter out candidates that are also stocked out
                    candidates = [c for c in candidates if c not in stocked_out_today]
                    if candidates and rng.random() < sub_prob:
                        target_item_id = str(rng.choice(candidates))
                        is_sub_order = True
                        orig_requested_id = iid
                    else:
                        # Customer walks away / backorders elsewhere during stockout
                        continue

                target_spec = items_dict[target_item_id]

                # Order quantity in boxes (with occasional huge whale tender spike!)
                base_boxes = int(max(2, rng.lognormal(mean=2.4, sigma=0.65)))
                if rng.random() < 0.025:  # 2.5% chance of bulk distributor tender order
                    base_boxes *= int(rng.integers(4, 8))

                # PPF-style UoM mix: if base_boxes >= 20, 45% chance ERP books it in CASES (1 Case = 10 Boxes)
                if base_boxes >= 20 and rng.random() < 0.45:
                    ordered_qty = max(1, round(base_boxes / 10))
                    case_uom_variants = (
                        ["CASE_10_BOX200", "CS10_BX200"]
                        if target_spec["box_pieces"] == 200
                        else ["CASE_10_BOX100", "CS10", "CASE_10"]
                    )
                    uom_raw = str(rng.choice(case_uom_variants))
                    unit_price = round(target_spec["list_price_box_eur"] * 10 * rng.uniform(0.88, 0.98), 2)
                else:
                    ordered_qty = base_boxes
                    box_uom_variants = (
                        ["BOX_200", "BX200", "Box of 200"]
                        if target_spec["box_pieces"] == 200
                        else ["BOX_100", "BX100", "Box of 100"]
                    )
                    uom_raw = str(rng.choice(box_uom_variants))
                    unit_price = round(target_spec["list_price_box_eur"] * rng.uniform(0.92, 1.05), 2)

                order_seq += 1
                order_id = f"SO-{order_seq}"

                # 2% chance of CANCELLED order, 1% RETURNED (for dbt staging filter practice)
                status_roll = rng.random()
                if status_roll < 0.02:
                    order_status = "CANCELLED"
                elif status_roll < 0.03:
                    order_status = "RETURNED"
                    ordered_qty = -abs(ordered_qty)
                else:
                    order_status = str(rng.choice(["COMPLETED", "SHIPPED", "CLOSED", "closed"]))

                order_row = {
                    "order_id": order_id,
                    "order_date": current_date.strftime("%Y-%m-%d"),
                    "customer_id": cust_id,
                    "item_id": target_item_id,
                    "ordered_uom_qty": ordered_qty,
                    "uom_code_raw": uom_raw,
                    "unit_selling_price_eur": unit_price,
                    "order_status_raw": order_status,
                    "is_substitute_order_flag": "Y" if is_sub_order else "N",
                    "original_requested_item_id": orig_requested_id,
                    "erp_loaded_at": f"{current_date.strftime('%Y-%m-%d')} 23:55:00",
                }
                order_records.append(order_row)

                # 0.4% chance of duplicate ERP extraction row
                if rng.random() < 0.004:
                    dup_order = order_row.copy()
                    dup_order["erp_loaded_at"] = f"{current_date.strftime('%Y-%m-%d')} 23:59:59"
                    order_records.append(dup_order)

    return pd.DataFrame(inventory_records), pd.DataFrame(order_records)


def main() -> None:
    print("🚀 Generating realistic B2B ERP data for Spec-Based Forecasting...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    df_suppliers = generate_suppliers()
    df_customers_dirty, df_customers_clean = generate_customers()
    df_items_dirty, df_items_clean = generate_items()
    df_inventory, df_orders = simulate_inventory_and_orders(df_items_clean, df_customers_clean)

    print(f"📦 Connecting to DuckDB at: {DB_PATH}")
    with duckdb.connect(str(DB_PATH)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw_erp;")

        tables = {
            "suppliers": df_suppliers,
            "customers": df_customers_dirty,
            "items": df_items_dirty,
            "inventory_daily": df_inventory,
            "sales_orders": df_orders,
        }

        for table_name, df in tables.items():
            con.execute(f"CREATE OR REPLACE TABLE raw_erp.{table_name} AS SELECT * FROM df;")
            count = con.execute(f"SELECT COUNT(*) FROM raw_erp.{table_name}").fetchall()[0][0]
            print(f"   ✅ raw_erp.{table_name:<18} -> {count:>8,} rows loaded")

    print("\n🎉 Done! Raw ERP tables are ready in `raw_erp` schema.")


if __name__ == "__main__":
    main()
