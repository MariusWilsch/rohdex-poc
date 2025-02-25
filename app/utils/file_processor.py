from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime
from io import StringIO, BytesIO


def process_partie(content: bytes) -> Dict:
    """Process Partie data from bytes content"""
    try:
        # Read CSV from bytes buffer
        buffer = BytesIO(content)
        df = pd.read_csv(buffer, header=None)
        print(f"\nProcessing Partie data with {len(df.columns)} columns")
        print("Column values for first row:")
        for i, val in enumerate(df.iloc[0]):
            print(f"Column {i}: {val}")

        # Validate expected columns
        if len(df.columns) < 11:
            raise ValueError(f"Data has only {len(df.columns)} columns")

        # Process individual bales
        bales_data = []
        for idx, row in df.iterrows():
            gross = row[10]  # Column K (0-indexed)
            tare = 2.0  # Standard tare weight of 2.0 kg for all bales except last
            if idx == len(df) - 1:  # Last bale
                tare = 1.6  # Special tare weight for last bale

            net = gross - tare
            bale_data = {
                "bale_no": idx + 1,
                "gross_kg": gross,
                "tare_kg": tare,
                "net_kg": net,
                "net_lbs": net * 2.2046,
            }
            print(f"\nProcessed bale {idx + 1}:")
            print(f"Gross: {gross} kg")
            print(f"Tare: {tare} kg")
            print(f"Net: {net} kg")
            print(f"Net (lbs): {net * 2.2046} lbs")
            bales_data.append(bale_data)

        # Calculate totals
        total_gross = sum(bale["gross_kg"] for bale in bales_data)
        total_tare = sum(bale["tare_kg"] for bale in bales_data)
        total_net = sum(bale["net_kg"] for bale in bales_data)
        total_lbs = total_net * 2.2046

        print(f"\nTotals:")
        print(f"Total Gross: {total_gross} kg")
        print(f"Total Tare: {total_tare} kg")
        print(f"Total Net: {total_net} kg")
        print(f"Total Net (lbs): {total_lbs} lbs")

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
        print(f"Error processing partie data: {str(e)}")
        raise ValueError(f"Error processing partie data: {str(e)}")


def load_wahrheit(content: bytes) -> Tuple[Dict, str, str]:
    """Load Wahrheitsdatei mapping from bytes content"""
    print("\n=== Processing Wahrheitsdatei ===")

    # Read CSV content, skipping the first row and using second row as headers
    buffer = BytesIO(content)
    df = pd.read_csv(buffer, sep="\t", encoding="utf-8", skiprows=1)

    # Debug information
    print("\nDataFrame Info:")
    print("Columns:", df.columns.tolist())
    print("\nFirst few rows:")
    print(df.head())
    print(f"\nNumber of rows in Wahrheit file: {len(df)}")

    # Initialize variables
    product_map = {}
    container_no = None
    invoice_no = None

    # Extract container number and invoice number from the raw text
    text = content.decode("utf-8")
    lines = text.splitlines()
    for line in lines:
        if any(prefix in line for prefix in ["CAIU", "ONEU"]):
            parts = line.strip().split()
            for i, part in enumerate(parts):
                if any(
                    part.startswith(prefix) for prefix in ["CAIU", "ONEU"]
                ) and i + 1 < len(parts):
                    container_no = f"{part} {parts[i+1]}"
                    print(f"Found container number: {container_no}")
                    break
        elif line.strip().isdigit() and len(line.strip()) >= 7:
            invoice_no = line.strip()
            print(f"Found invoice number: {invoice_no}")

    # Create product mapping from Virtuelle Partie to Beschreibung 2
    for _, row in df.iterrows():
        if pd.notna(row["Virtuelle Partie"]):  # Check if partie number exists
            partie_num = str(
                int(row["Virtuelle Partie"])
            )  # Convert to int first to remove any decimal places
            description = row["Beschreibung 2"]
            if pd.notna(description):  # Check if description exists
                product_map[partie_num] = description.strip().upper()
                print(f"Found product mapping - Partie {partie_num}: {description}")

    print("\nFinal Wahrheit Processing Results:")
    print(f"Container Number: {container_no}")
    print(f"Invoice Number: {invoice_no}")
    print("Product Mappings:")
    for partie, desc in product_map.items():
        print(f"  Partie {partie}: {desc}")

    return product_map, container_no, invoice_no


def format_bales_data(bales: List[Dict]) -> str:
    """Format bales data according to template structure"""
    lines = []
    for bale in bales:
        line = f"{bale['bale_no']},{bale['gross_kg']:.2f} kg,{bale['tare_kg']:.2f} kg,{bale['net_kg']:.2f} kg,2.2046,{bale['net_lbs']:.2f}lbs"
        lines.append(line)
    return "\n".join(lines)


def generate_packing_list(
    partie_contents: List[bytes], wahrheit_content: bytes, template_content: str
) -> str:
    """Generate a packing list from multiple Partie contents"""
    print("\n=== Generating Packing List ===")
    # Load product mappings
    product_map, container_no, invoice_no = load_wahrheit(wahrheit_content)

    print("\nTemplate Processing:")
    # Extract the product section template
    start = template_content.find("{BEGIN_PRODUCT_SECTION}")
    end = template_content.find("{END_PRODUCT_SECTION}") + len("{END_PRODUCT_SECTION}")
    print(f"Template markers found - Start: {start}, End: {end}")

    product_template = (
        template_content[start:end]
        .replace("{BEGIN_PRODUCT_SECTION}\n", "")
        .replace("\n{END_PRODUCT_SECTION}", "")
    )

    # Process all Partie contents
    product_sections = []
    print(f"\nProcessing {len(partie_contents)} Partie files:")
    for idx, partie_content in enumerate(partie_contents):
        # Extract partie number from filename (e.g., "Partie 33876.csv" -> "33876")
        partie_num = partie_content.filename.split()[1].split(".")[0]
        print(f"\nProcessing Partie {partie_num}")
        product_data = process_partie(partie_content.content)
        description = product_map.get(partie_num)
        print(f"Found description from Wahrheit: {description}")
        section = generate_product_section(
            product_template, product_data, partie_num, product_map.get(partie_num)
        )
        product_sections.append(section)

    # Generate final document
    print("\nGenerating final document")
    output_content = template_content[:start]  # Get header
    output_content = output_content.replace(
        "{INVOICE_NO}", invoice_no or datetime.now().strftime("%Y%m%d")
    )
    output_content = output_content.replace("{CONTAINER_NO}", container_no or "TBD")
    print(f"Using Invoice No: {invoice_no}")
    print(f"Using Container No: {container_no}")

    # Add all product sections
    output_content += "\n".join(product_sections)

    return output_content


def generate_product_section(
    template_section: str, product_data: Dict, partie_num: str, description: str
) -> str:
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
