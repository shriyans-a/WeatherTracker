from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class CurrentConditions(BaseModel):
    temperature_c: Optional[float] = None
    wind_speed_kph: Optional[float] = None
    wind_direction: Optional[str] = None
    short_description: Optional[str] = None
    detailed_description: Optional[str] = None
    is_thunderstorm: bool = False
    is_extreme_heat: bool = False
    is_high_wind: bool = False
    is_heavy_precipitation: bool = False


class ShortTermForecastPeriod(BaseModel):
    name: str
    start_time: str
    end_time: str
    temperature_c: Optional[float] = None
    wind_speed_kph: Optional[float] = None
    wind_direction: Optional[str] = None
    short_description: Optional[str] = None
    is_thunderstorm: bool = False
    is_extreme_heat: bool = False
    is_high_wind: bool = False
    is_heavy_precipitation: bool = False


class ShortTermForecast(BaseModel):
    periods: List[ShortTermForecastPeriod] = Field(default_factory=list)


class Alert(BaseModel):
    id: str
    event: str
    severity: Literal["Minor", "Moderate", "Severe", "Extreme"]
    urgency: Optional[str] = None
    certainty: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    instruction: Optional[str] = None


class Forecast(BaseModel):
    current_conditions: CurrentConditions
    short_term: ShortTermForecast


class RiskAssessmentRequest(BaseModel):
    location: str = Field(..., description="City name or ZIP code")


class AIExplanation(BaseModel):
    explanation: str
    recommendations: List[str]


class RiskAssessmentResponse(BaseModel):
    location: str
    coordinates: Coordinates
    current_conditions: CurrentConditions
    short_term_forecast: ShortTermForecast
    alerts: List[Alert]
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["Low", "Moderate", "High", "Extreme"]
    ai: AIExplanation

