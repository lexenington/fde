"""The output contract. Changing this is a breaking change for finance - version it."""

from typing import Optional

from pydantic import BaseModel, Field


class Invoice(BaseModel):
    is_invoice: bool = Field(description="False if the document is not a supplier invoice (e.g. a receipt, quote, letter)")
    supplier_name: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str] = Field(description="ISO 8601 date, YYYY-MM-DD")
    currency: Optional[str] = Field(description="ISO 4217 code, e.g. GHS, USD")
    subtotal: Optional[float]
    tax_total: Optional[float] = Field(description="Sum of VAT and all levies (NHIL, GETFund, COVID-19 levy)")
    total: Optional[float] = Field(description="Amount payable. Negative for credit notes")
    confidence: float = Field(description="0.0-1.0: how confident you are that every extracted field is correct")
    needs_review: bool = Field(description="True if any field is ambiguous, contradictory, illegible or suspicious")
    review_reason: Optional[str]
