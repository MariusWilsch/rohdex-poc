import pandas as pd
import os
from datetime import datetime
import string


def process_partie(file_path):
    """Process Partie CSV file to extract weights and bale data"""
    try:
        df = pd.read_csv(file_path, header=None)
        print(f"Processing {file_path} with {len(df.columns)} columns")

        # Validate expected columns
        if len(df.columns) < 11:
            raise ValueError(f"File {file_path} has only {len(df.columns)} columns")

        # Process individual bales
        bales_data = []
        for idx, row in df.iterrows():
            gross = row[10]  # Column K (0-indexed)
            tare = row[9]  # Column J
            net = gross - tare
            bales_data.append(
                {
                    "bale_no": idx + 1,
                    "gross_kg": gross,
                    "tare_kg": tare,
                    "net_kg": net,
                    "net_lbs": net * 2.2046,
                }
            )

        # Calculate totals
        total_gross = sum(bale["gross_kg"] for bale in bales_data)
        total_tare = sum(bale["tare_kg"] for bale in bales_data)
        total_net = sum(bale["net_kg"] for bale in bales_data)
        total_lbs = total_net * 2.2046

        print(f"Processed {file_path}: Gross={total_gross}, Tare={total_tare}")
        return {
            "bales": bales_data,
            "totals": {
                "gross_kg": total_gross,
                "tare_kg": total_tare,
                "net_kg": total_net,
                "net_lbs": total_lbs,
                "bale_count": len(bales_data),
            },
        }

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        raise


def load_wahrheit(wahrheit_path):
    """Load Wahrheitsdatei mapping"""
    # Read all lines to find container number and process mappings
    product_map = {}
    container_no = None
    invoice_no = None

    with open(wahrheit_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        # Look for container numbers (both CAIU and ONEU formats)
        if any(prefix in line for prefix in ["CAIU", "ONEU"]):
            # Extract full container number (format: XXXX XXXXXX-X)
            parts = line.strip().split()
            for i, part in enumerate(parts):
                if any(
                    part.startswith(prefix) for prefix in ["CAIU", "ONEU"]
                ) and i + 1 < len(parts):
                    container_no = f"{part} {parts[i+1]}"
                    break
        elif line.strip().isdigit() and len(line.strip()) >= 7:
            invoice_no = line.strip()
        elif "Artikel" in line and "GRS" in line:
            # Split on multiple spaces to handle variable spacing
            parts = [p for p in line.split() if p.strip()]
            if len(parts) >= 5:
                partie_num = parts[2]  # Virtuelle Partie
                # Find the GRS part of the description
                desc_parts = []
                found_grs = False
                for p in parts[4:]:
                    if p in ["EXPORT", "USD", "ROHDEX"] or p.endswith(",00"):
                        break
                    if "GRS" in p and found_grs:  # Skip second GRS
                        continue
                    if "GRS" in p:
                        found_grs = True
                    desc_parts.append(p)
                description = " ".join(desc_parts)
                if partie_num.isdigit():
                    product_map[partie_num] = description.upper()

    return product_map, container_no, invoice_no


def format_bales_data(bales):
    """Format bales data according to template structure"""
    lines = []
    for bale in bales:
        line = f"{bale['bale_no']},{bale['gross_kg']:.2f} kg,{bale['tare_kg']:.2f} kg,{bale['net_kg']:.2f} kg,2.2046,{bale['net_lbs']:.2f}lbs"
        lines.append(line)
    return "\n".join(lines)


def generate_product_section(template_section, product_data, partie_num, description):
    """Generate a complete product section from template"""
    section = template_section.replace(
        "{PRODUCT_DESCRIPTION}", description or f"Unknown Product"
    )
    section = section.replace("{SAMPLE_NO}", partie_num)

    # Format and insert bales data
    bales_data = format_bales_data(product_data["bales"])
    section = section.replace("{BALES_DATA}", bales_data)

    # Insert totals
    totals = product_data["totals"]
    section = section.replace("{BALES_COUNT}", str(totals["bale_count"]))
    section = section.replace("{TOTAL_GROSS}", f"{totals['gross_kg']:.2f}")
    section = section.replace("{TOTAL_TARE}", f"{totals['tare_kg']:.2f}")
    section = section.replace("{TOTAL_NET}", f"{totals['net_kg']:.2f}")
    section = section.replace("{TOTAL_LBS}", f"{totals['net_lbs']:.2f}")
    section = section.replace("{TOTAL_GROSS_LBS}", f"{totals['gross_kg'] * 2.2046:.2f}")
    section = section.replace("{TOTAL_NET_LBS}", f"{totals['net_lbs']:.2f}")

    return section


def generate_packing_list(partie_files, wahrheit_path, template_path, output_path):
    """Generate a packing list from multiple Partie files"""
    # Load product mappings
    product_map, container_no, invoice_no = load_wahrheit(wahrheit_path)

    # Load template
    with open(template_path, "r") as f:
        template_content = f.read()

    # Extract the product section template
    start = template_content.find("{BEGIN_PRODUCT_SECTION}")
    end = template_content.find("{END_PRODUCT_SECTION}") + len("{END_PRODUCT_SECTION}")
    product_template = (
        template_content[start:end]
        .replace("{BEGIN_PRODUCT_SECTION}\n", "")
        .replace("\n{END_PRODUCT_SECTION}", "")
    )

    # Process all Partie files
    product_sections = []
    for pfile in partie_files:
        # Extract partie number from filename
        partie_num = os.path.basename(pfile).split()[1].split(".")[0]
        # Process the file
        product_data = process_partie(pfile)
        # Generate product section
        section = generate_product_section(
            product_template, product_data, partie_num, product_map.get(partie_num)
        )
        product_sections.append(section)

    # Generate final document
    output_content = template_content[:start]  # Get header
    output_content = output_content.replace(
        "{INVOICE_NO}", invoice_no or datetime.now().strftime("%Y%m%d")
    )
    output_content = output_content.replace("{CONTAINER_NO}", container_no or "TBD")

    # Add all product sections
    output_content += "\n".join(product_sections)

    # Write output
    with open(output_path, "w") as f:
        f.write(output_content)

    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python generate_packing_list_v2.py [wahrheit] [partie1] [partie2] ..."
        )
        sys.exit(1)

    output = generate_packing_list(
        sys.argv[2:],  # partie files
        sys.argv[1],  # wahrheitsdatei
        "template_packing_list.csv",  # local template
        "Generated_Packing_List.csv",
    )
    print(f"Created {output}")
