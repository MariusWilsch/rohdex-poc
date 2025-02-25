from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union


class Bale(BaseModel):
    """Individual bale information"""

    bale_no: str = Field(..., description="Bale number")
    gross_kg: float = Field(..., description="Gross weight in kg")


class PartieData(BaseModel):
    """Structured data extracted from a Partie file"""

    partie_no: str = Field(..., description="Partie number")
    bales: List[Bale] = Field(..., description="List of bales in the partie")


class ProductInfo(BaseModel):
    """Product information from Wahrheit"""

    product_code: str = Field(..., description="Product code")
    description: str = Field(..., description="Product description")
    quantity: int = Field(..., description="Quantity")
    unit: str = Field(..., description="Unit of measurement")
    unit_price: float = Field(..., description="Price per unit")
    total_price: float = Field(..., description="Total price")
    currency: Optional[str] = Field(None, description="Currency")


class WahrheitData(BaseModel):
    """Structured data extracted from a Wahrheit file"""

    invoice_no: str = Field(..., description="Invoice number")
    container_no: str = Field(..., description="Container number")
    products: List[ProductInfo] = Field(
        ..., description="List of products in the Wahrheit file"
    )
    total_amount: Optional[float] = Field(None, description="Total invoice amount")
    currency: Optional[str] = Field(None, description="Currency of the invoice")
    additional_info: Optional[Dict[str, Any]] = Field(
        None, description="Any additional information extracted"
    )
