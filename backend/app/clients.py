from __future__ import annotations

import os
from typing import List, Tuple

import httpx
from pydantic import BaseModel

from .schemas import (
    AIExplanation,
    Alert,
    Coordinates,
    CurrentConditions,
    Forecast,
    ShortTermForecast,
    ShortTermForecastPeriod,
)


class GeocodingClient:
    """
    Simple geocoding via OpenStreetMap Nominatim.
    """

    _BASE_URL = "https://nominatim.openstreetmap.org/search"

    async def geocode(self, query: str) -> Coordinates:
        headers = {"User-Agent": "weather-risk-demo/1.0"}
        params = {"q": query, "format": "json", "limit": 1}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self._BASE_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        if not data:
            raise ValueError("Location not found")
        item = data[0]
        return Coordinates(latitude=float(item["lat"]), longitude=float(item["lon"]))


class NWSPointInfo(BaseModel):
    forecast_url: str
    forecast_hourly_url: str


class NWSClient:
    _POINTS_BASE = "https://api.weather.gov/points/{lat},{lon}"

    async def _get_point_info(self, lat: float, lon: float) -> NWSPointInfo:
        # NWS points endpoint often responds with an HTTP 301 redirect that must be followed.
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                self._POINTS_BASE.format(lat=lat, lon=lon),
                headers={"User-Agent": "weather-risk-demo/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
        props = data["properties"]
        return NWSPointInfo(
            forecast_url=props["forecast"],
            forecast_hourly_url=props["forecastHourly"],
        )

    async def _get_forecast(
        self, point: NWSPointInfo
    ) -> Tuple[CurrentConditions, ShortTermForecast]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                point.forecast_hourly_url,
                headers={"User-Agent": "weather-risk-demo/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        periods = data["properties"]["periods"]
        current_raw = periods[0] if periods else {}

        def f_to_c(temp_f: float | None) -> float | None:
            if temp_f is None:
                return None
            return (temp_f - 32) * 5.0 / 9.0

        def mph_to_kph(speed_mph: float | None) -> float | None:
            if speed_mph is None:
                return None
            return speed_mph * 1.60934

        def parse_wind_speed(speed_str: str | None) -> float | None:
            if not speed_str:
                return None
            # Example: "10 mph", "10 to 15 mph"
            parts = speed_str.split()
            try:
                value = float(parts[0])
            except (IndexError, ValueError):
                return None
            return mph_to_kph(value)

        def classify_conditions(short: str, detailed: str) -> dict:
            import re

            text = f"{short} {detailed}".lower()

            def word_match(keywords: list[str]) -> bool:
                # Use word-boundary matching to avoid substring hits like "hot"
                # inside "throughout", "shot", "shortly", etc.
                return any(
                    re.search(r"\b" + re.escape(k) + r"\b", text) for k in keywords
                )

            return {
                "is_thunderstorm": word_match(["thunderstorm", "t-storm", "tstorm"]),
                # Avoid plain "hot" – it's too broad; rely on explicit advisory phrases.
                "is_extreme_heat": word_match(
                    ["heat advisory", "excessive heat", "heat warning", "extreme heat"]
                ),
                "is_high_wind": word_match(
                    ["windy", "strong winds", "high wind", "gale", "storm force"]
                ),
                "is_heavy_precipitation": word_match(
                    ["heavy rain", "heavy snow", "downpour", "blizzard", "heavy rainfall"]
                ),
            }

        current_temp_c = f_to_c(current_raw.get("temperature"))
        current_wind_speed_kph = parse_wind_speed(current_raw.get("windSpeed"))
        current_short = current_raw.get("shortForecast") or ""
        current_detailed = current_raw.get("detailedForecast") or current_short
        flags = classify_conditions(current_short, current_detailed)

        current = CurrentConditions(
            temperature_c=current_temp_c,
            wind_speed_kph=current_wind_speed_kph,
            wind_direction=current_raw.get("windDirection"),
            short_description=current_short,
            detailed_description=current_detailed,
            **flags,
        )

        short_term_periods: List[ShortTermForecastPeriod] = []
        for raw in periods[:8]:
            short = raw.get("shortForecast") or ""
            detailed = raw.get("detailedForecast") or short
            flags = classify_conditions(short, detailed)
            short_term_periods.append(
                ShortTermForecastPeriod(
                    name=raw.get("name") or "",
                    start_time=raw.get("startTime") or "",
                    end_time=raw.get("endTime") or "",
                    temperature_c=f_to_c(raw.get("temperature")),
                    wind_speed_kph=parse_wind_speed(raw.get("windSpeed")),
                    wind_direction=raw.get("windDirection"),
                    short_description=short,
                    **flags,
                )
            )

        return current, ShortTermForecast(periods=short_term_periods)

    async def _get_alerts(self, lat: float, lon: float) -> List[Alert]:
        url = "https://api.weather.gov/alerts"
        params = {"point": f"{lat},{lon}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"User-Agent": "weather-risk-demo/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        alerts: List[Alert] = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            raw_severity = props.get("severity") or "Minor"
            severity = (
                raw_severity
                if raw_severity in {"Minor", "Moderate", "Severe", "Extreme"}
                else "Minor"
            )
            alerts.append(
                Alert(
                    id=feature.get("id") or props.get("id") or "",
                    event=props.get("event") or "Unknown",
                    severity=severity,
                    urgency=props.get("urgency"),
                    certainty=props.get("certainty"),
                    headline=props.get("headline"),
                    description=props.get("description"),
                    instruction=props.get("instruction"),
                )
            )
        return alerts

    async def fetch_forecast_and_alerts(
        self, lat: float, lon: float
    ) -> Tuple[Forecast, List[Alert]]:
        try:
            point = await self._get_point_info(lat, lon)
            current, short_term = await self._get_forecast(point)
            alerts = await self._get_alerts(lat, lon)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"NWS HTTP error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"NWS unexpected error: {exc}") from exc

        return Forecast(current_conditions=current, short_term=short_term), alerts


class GradientAIClient:
    """
    Wrapper around DigitalOcean Gradient AI serverless inference
    using the OpenAI-compatible Chat Completions API.
    """

    _BASE_URL = "https://inference.do-ai.run/v1/chat/completions"

    def __init__(self) -> None:
        self._model_access_key = os.getenv("MODEL_ACCESS_KEY")
        self._model_id = os.getenv("GRADIENT_MODEL_ID", "openai-gpt-oss-20b")
        if not self._model_access_key:
            raise RuntimeError("MODEL_ACCESS_KEY environment variable is required")

    async def explain_risk(
        self,
        location: str,
        latitude: float,
        longitude: float,
        forecast: Forecast,
        alerts: List[Alert],
        risk_score: int,
        risk_level: str,
    ) -> AIExplanation:
        """
        Call Gradient AI and ask for strictly-JSON explanation + recommendations.
        """
        system_prompt = (
            "You are a public safety assistant. You receive structured weather and "
            "hazard data for a specific location. Respond ONLY with JSON, no extra "
            "text. The JSON schema is:\n"
            '{ "explanation": string, "recommendations": string[] }.\n'
            "Use clear, calm language aimed at residents. Explain the risk level and "
            "what it practically means in the next 12–24 hours, then give 2–3 concise, "
            "actionable safety recommendations tailored to the conditions."
        )

        # Take at most the top 5 alerts by severity so we don't overload the model
        severity_rank = {"Extreme": 3, "Severe": 2, "Moderate": 1, "Minor": 0}
        top_alerts = sorted(
            alerts,
            key=lambda a: severity_rank.get(a.severity, 0),
            reverse=True,
        )[:5]

        body = {
            "model": self._model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Location: {location} ({lat},{lon})\n"
                        "Risk score: {score} (level: {level})\n"
                        "Current conditions: {current}\n"
                        "Short-term forecast (first 4 periods): {short}\n"
                        "Active alerts (top 5 by severity): {alerts}\n\n"
                        "Respond ONLY with JSON in the exact schema described in the "
                        "system message."
                    ).format(
                        location=location,
                        lat=latitude,
                        lon=longitude,
                        score=risk_score,
                        level=risk_level,
                        current=forecast.current_conditions.model_dump(),
                        short=[
                            p.model_dump() for p in forecast.short_term.periods[:4]
                        ],
                        alerts=[a.model_dump() for a in top_alerts],
                    ),
                },
            ],
            "max_tokens": 400,
            "temperature": 0.4,
        }

        headers = {
            "Authorization": f"Bearer {self._model_access_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(self._BASE_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        try:
            raw_text = data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Unexpected Gradient AI response format: {exc}") from exc

        import json
        parsed: dict | None = None

        # First, try to parse the whole string as JSON.
        try:
            parsed = json.loads(raw_text)
        except Exception:
            # Try to extract a JSON object substring if the model wrapped it in prose.
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(raw_text[start : end + 1])
                except Exception:
                    parsed = None

        if not isinstance(parsed, dict):
            # Fallback: treat the raw text as the explanation and provide generic recs.
            return AIExplanation(
                explanation=str(raw_text),
                recommendations=[
                    "Monitor local weather updates and alerts from official sources.",
                    "Avoid unnecessary travel during periods of elevated risk.",
                    "Prepare a basic emergency kit appropriate for your area and season.",
                ],
            )

        explanation = str(parsed.get("explanation", "") or "").strip()
        recs_raw = parsed.get("recommendations", [])
        if isinstance(recs_raw, str):
            recommendations = [recs_raw]
        elif isinstance(recs_raw, list):
            recommendations = [str(r) for r in recs_raw]
        else:
            recommendations = []

        if not explanation:
            explanation = raw_text

        if not recommendations:
            recommendations = [
                "Monitor local weather updates and alerts from official sources.",
                "Avoid unnecessary travel during periods of elevated risk.",
                "Prepare a basic emergency kit appropriate for your area and season.",
            ]

        return AIExplanation(
            explanation=explanation,
            recommendations=recommendations[:5],
        )

