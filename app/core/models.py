from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union


class Bale(BaseModel):
    """Individual bale information"""

    bale_no: str = Field(..., description="Bale number which starts with 1")
    gross_kg: float = Field(
        ..., description="Gross weight in kg which is in column 10 and 11"
    )


class PartieData(BaseModel):
    """Structured data extracted from a Partie file"""

    partie_no: str = Field(..., description="Partie number")
    bales: List[Bale] = Field(..., description="List of bales in the partie")


class ProductInfo(BaseModel):
    """Product information from Wahrheit"""

    product_code: int = Field(..., description="Product code")
    description: str = Field(..., description="Product description")


class WahrheitData(BaseModel):
    """Structured data extracted from a Wahrheit file"""

    invoice_no: int = Field(..., description="Invoice number")
    container_no: str = Field(..., description="Container number which is in column 4")
    products: List[ProductInfo] = Field(
        ..., description="List of products in the Wahrheit file"
    )
