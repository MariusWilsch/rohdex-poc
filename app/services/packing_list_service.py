from fastapi import UploadFile
from app.utils.file_processor import (
    process_partie,
    load_wahrheit,
    generate_packing_list,
)


class PackingListService:
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
        # Read all partie files into memory
        partie_contents = []
        for pfile in partie_files:
            content = await pfile.read()
            # Create a custom object that has both content and filename
            partie_contents.append(
                type(
                    "PartieFile", (), {"content": content, "filename": pfile.filename}
                )()
            )
            await pfile.seek(0)  # Reset file pointer for potential reuse

        # Read wahrheit file into memory
        wahrheit_content = await wahrheit_file.read()
        await wahrheit_file.seek(0)  # Reset file pointer for potential reuse

        # Read template from uploaded file
        template_content = (await template_file.read()).decode("utf-8")
        await template_file.seek(0)  # Reset file pointer for potential reuse

        # Generate packing list in memory
        result_content = generate_packing_list(
            partie_contents=partie_contents,
            wahrheit_content=wahrheit_content,
            template_content=template_content,
        )

        return result_content  # Return the generated content directly
