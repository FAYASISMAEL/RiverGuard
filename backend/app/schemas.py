from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from .image_classifier import Prediction

Category = Literal['Industrial Discharge', 'Sewage', 'Oil / Fuel', 'Plastic / Solid Waste', 'Agricultural Runoff', 'Dead Fish', 'Water Discoloration', 'Foam', 'Bad Odour', 'Other', 'Other / Unclear']
Status = Literal['UNDER REVIEW', 'VERIFIED', 'REJECTED', 'RESOLVED']

class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class ReportInput(Location):
    contamination_type: Category
    description: str = Field(min_length=10, max_length=3000)
    observed_at: datetime
    reporter_name: str = Field(default='', max_length=100)
    contact: str = Field(default='', max_length=200)
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list, max_length=50)
    ai_image_results: list[Prediction] = Field(default_factory=list, max_length=50)

    @field_validator('description')
    @classmethod
    def clean_description(cls, value):
        if len(value.strip()) < 10:
            raise ValueError('Please describe your observation in at least 10 characters.')
        return value.strip()

    @field_validator('observed_at')
    @classmethod
    def check_time(cls, value):
        if value.tzinfo is None:
            raise ValueError('Observation time must include a timezone.')
        if value > datetime.now(timezone.utc):
            raise ValueError('Observation time cannot be in the future.')
        return value

class StatusInput(BaseModel):
    status: Status
    note: str = Field(default='', max_length=1000)

class AlertInput(BaseModel):
    state: Literal['Sent - Simulated', 'Acknowledged']
