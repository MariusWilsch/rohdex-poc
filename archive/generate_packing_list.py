import pandas as pd
from openpyxl import load_workbook
import os


def process_partie(file_path):
    """Process Partie CSV file to extract weights"""
    try:
        df = pd.read_csv(file_path, header=None)
        print(f"Processing {file_path} with {len(df.columns)} columns")

        # Validate expected columns
        if len(df.columns) < 11:
            raise ValueError(f"File {file_path} has only {len(df.columns)} columns")

        gross = df[10].sum()  # Column K (0-indexed)
        tare = df[9].sum()  # Column J
        print(f"Processed {file_path}: Gross={gross}, Tare={tare}")
        return gross, tare, gross - tare

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        raise


def load_wahrheit(wahrheit_path):
    """Load Wahrheitsdatei mapping"""
    df = pd.read_csv(wahrheit_path, sep="\t", skiprows=1)
    return dict(zip(df.iloc[:, 1], df.iloc[:, 3]))


def generate_packing_list(partie_files, wahrheit_path, template_path):
    # Load product mappings
    product_map = load_wahrheit(wahrheit_path)

    # Process all Partie files
    results = []
    for pfile in partie_files:
        partie_num = os.path.basename(pfile).split()[1].split(".")[0]
        gross, tare, net = process_partie(pfile)
        results.append(
            {
                "description": product_map.get(partie_num, "Unknown Product"),
                "gross_kg": gross,
                "tare_kg": tare,
                "net_kg": net,
                "net_lbs": net * 2.2046,
            }
        )

    # Load CSV template
    template_path = os.path.join(
        "context", "2410270 Vorlagen + Warheitsdatei + Waage", "Packing List.csv"
    )

    if not os.path.exists(template_path):
        available_files = "\n".join(os.listdir(os.path.dirname(template_path)))
        raise FileNotFoundError(
            f"Template file not found at {template_path}\n"
            f"Available files in directory:\n{available_files}"
        )

    print(f"Loading CSV template from: {template_path}")
    # Read template with proper header handling
    df_template = pd.read_csv(
        template_path,
        header=0,
        usecols=[
            "Description",
            "Gross Weight (kg)",
            "Tare Weight (kg)",
            "Net Weight (kg)",
            "Net Weight (lbs)",
        ],
    )


import pandas as pd
from openpyxl import load_workbook
import os


def process_partie(file_path):
    """Process Partie CSV file to extract weights"""
    try:
        df = pd.read_csv(file_path, header=None)
        print(f"Processing {file_path} with {len(df.columns)} columns")

        # Validate expected columns
        if len(df.columns) < 11:
            raise ValueError(f"File {file_path} has only {len(df.columns)} columns")

        gross = df[10].sum()  # Column K (0-indexed)
        tare = df[9].sum()  # Column J
        print(f"Processed {file_path}: Gross={gross}, Tare={tare}")
        return gross, tare, gross - tare

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        raise


def load_wahrheit(wahrheit_path):
    """Load Wahrheitsdatei mapping"""
    df = pd.read_csv(wahrheit_path, sep="\t", skiprows=1)
    return dict(zip(df.iloc[:, 1], df.iloc[:, 3]))


def generate_packing_list(partie_files, wahrheit_path, template_path, output_path):
    # Load product mappings
    product_map = load_wahrheit(wahrheit_path)

    # Process all Partie files
    results = []
    for pfile in partie_files:
        partie_num = os.path.basename(pfile).split()[1].split(".")[0]
        gross, tare, net = process_partie(pfile)
        results.append(
            {
                "description": product_map.get(partie_num, "Unknown Product"),
                "gross_kg": gross,
                "tare_kg": tare,
                "net_kg": net,
                "net_lbs": net * 2.2046,
            }
        )

    # Load CSV template
    template_path = os.path.join(
        "context", "2410270 Vorlagen + Warheitsdatei + Waage", "Packing List.csv"
    )

    if not os.path.exists(template_path):
        available_files = "\n".join(os.listdir(os.path.dirname(template_path)))
        raise FileNotFoundError(
            f"Template file not found at {template_path}\n"
            f"Available files in directory:\n{available_files}"
        )

    print(f"Loading CSV template from: {template_path}")
    df_template = pd.read_csv(template_path)

    # Insert processed data into template
    for result in results:
        new_row = {
            "Description": result["description"],
            "Gross Weight (kg)": result["gross_kg"],
            "Tare Weight (kg)": result["tare_kg"],
            "Net Weight (kg)": result["net_kg"],
            "Net Weight (lbs)": result["net_lbs"],
        }
        df_template = pd.concat(
            [df_template, pd.DataFrame([new_row])], ignore_index=True
        )

    # Save final output
    df_template.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python generate_packing_list.py [wahrheit] [partie1] [partie2] ..."
        )
        sys.exit(1)

    output = generate_packing_list(
        sys.argv[2:],  # partie files
        sys.argv[1],  # wahrheitsdatei
        None,  # template path (now hardcoded)
        "Generated_Packing_List.csv",
    )
    print(f"Created {output}")
