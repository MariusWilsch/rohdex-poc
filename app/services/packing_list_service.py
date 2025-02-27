from fastapi import UploadFile
from app.utils.file_processor import (
    process_partie,
    load_wahrheit,
    generate_packing_list,
)
from rich.console import Console
import pandas as pd
from io import BytesIO

console = Console()


class PackingListService:
    def _process_excel_partie(self, content: bytes, filename: str) -> bytes:
        """Process an Excel partie file and convert it to CSV format.

        Args:
            content: The raw bytes content of the Excel file
            filename: The filename for logging purposes

        Returns:
            bytes: The CSV content as bytes
        """
        console.print(f"[green]Processing Excel Partie file:[/] [cyan]{filename}[/]")
        # Convert Excel to CSV format
        df = pd.read_excel(BytesIO(content))
        # Convert to CSV bytes
        return df.to_csv(index=False).encode("utf-8")

    def _process_excel_wahrheit(self, content: bytes, filename: str) -> bytes:
        """Process an Excel wahrheit file, extract the V-LIEF sheet, and convert to CSV format.

        Args:
            content: The raw bytes content of the Excel file
            filename: The filename for logging purposes

        Returns:
            bytes: The CSV content as bytes from the V-LIEF sheet
        """
        console.print(f"[green]Processing Excel Wahrheit file:[/] [cyan]{filename}[/]")
        # Read all sheet names
        excel_file = BytesIO(content)
        xls = pd.ExcelFile(excel_file)

        # Find the sheet that starts with "V-LIEF"
        v_lief_sheet = None
        for sheet_name in xls.sheet_names:
            if sheet_name.startswith("V-LIEF"):
                v_lief_sheet = sheet_name
                break

        # If no V-LIEF sheet found, use the first sheet
        if not v_lief_sheet and len(xls.sheet_names) > 0:
            v_lief_sheet = xls.sheet_names[0]
            console.print(
                "[yellow]Warning: No sheet starting with V-LIEF found, using first sheet[/]"
            )

        if not v_lief_sheet:
            raise ValueError("No sheets found in Excel file")

        # Read the specific sheet
        df = pd.read_excel(excel_file, sheet_name=v_lief_sheet)

        # Convert to CSV bytes
        csv_content = df.to_csv(index=False).encode("utf-8")
        console.print(f"[green]Successfully extracted sheet: {v_lief_sheet}[/]")
        return csv_content

    def _is_excel_file(self, filename: str) -> bool:
        """Check if a file is an Excel file based on its extension.

        Args:
            filename: The filename to check

        Returns:
            bool: True if the file is an Excel file, False otherwise
        """
        return filename.lower().endswith((".xlsx", ".xls"))

    async def generate(
        self,
        partie_files: list[UploadFile],
        wahrheit_file: UploadFile,
        template_file: UploadFile,
    ) -> str:
        """Generates a packing list from uploaded files using in-memory processing.

        This method processes multiple types of uploaded files to generate a packing list:
        - One or more Partie files containing weight measurements
        - A Wahrheitsdatei containing reference data and container information
        - A template file defining the output format

        Args:
            partie_files (list[UploadFile]): List of Partie files containing weight measurements
                from digital scales. Each file should be a CSV with at least 11 columns.
            wahrheit_file (UploadFile): The Wahrheitsdatei (truth file) containing product
                descriptions, container numbers, and other reference information.
            template_file (UploadFile): CSV template file defining the structure of the
                output packing list, including placeholders for data insertion.

        Returns:
            str: The generated packing list content as a CSV-formatted string, with all
                placeholders replaced with actual data from the input files.
        """
        console.print("[bold blue]Starting packing list generation process...[/]")

        # Read all partie files into memory
        partie_contents = []
        for pfile in partie_files:
            content = await pfile.read()

            # Process Excel files if needed
            if self._is_excel_file(pfile.filename):
                processed_content = self._process_excel_partie(content, pfile.filename)
            else:
                processed_content = content

            # Create a custom object that has both content and filename
            partie_contents.append(
                type(
                    "PartieFile",
                    (),
                    {"content": processed_content, "filename": pfile.filename},
                )()
            )
            await pfile.seek(0)  # Reset file pointer for potential reuse
            console.print(f"[green]Loaded partie file:[/] [cyan]{pfile.filename}[/]")

        # Read wahrheit file into memory
        wahrheit_content = await wahrheit_file.read()

        # Process Excel wahrheit file if needed
        if self._is_excel_file(wahrheit_file.filename):
            wahrheit_content = self._process_excel_wahrheit(
                wahrheit_content, wahrheit_file.filename
            )

        await wahrheit_file.seek(0)  # Reset file pointer for potential reuse
        console.print(
            f"[green]Loaded wahrheit file:[/] [cyan]{wahrheit_file.filename}[/]"
        )

        # Read template from uploaded file
        template_content = (await template_file.read()).decode("utf-8")
        await template_file.seek(0)  # Reset file pointer for potential reuse
        console.print(
            f"[green]Loaded template file:[/] [cyan]{template_file.filename}[/]"
        )

        # Generate packing list in memory
        console.print("[bold blue]Processing files with AI...[/]")
        result_content = await generate_packing_list(
            partie_contents=partie_contents,
            wahrheit_content=wahrheit_content,
            template_content=template_content,
            wahrheit_filename=wahrheit_file.filename,
        )

        console.print("[bold green]Packing list generation completed successfully![/]")
        return result_content  # Return the generated content directly
