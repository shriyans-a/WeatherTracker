from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import AIExplanation, RiskAssessmentRequest, RiskAssessmentResponse
from .clients import GeocodingClient, NWSClient, GradientAIClient
from .risk_engine import RiskEngine


app = FastAPI(title="Weather Risk Assessment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

geocoder = GeocodingClient()
nws_client = NWSClient()
risk_engine = RiskEngine()
gradient_client = GradientAIClient()


@app.post("/api/assess-risk", response_model=RiskAssessmentResponse)
async def assess_risk(payload: RiskAssessmentRequest) -> RiskAssessmentResponse:
    try:
        coords = await geocoder.geocode(payload.location)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        forecast, alerts = await nws_client.fetch_forecast_and_alerts(
            coords.latitude, coords.longitude
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch NWS data: {exc}"
        ) from exc

    risk_score, risk_level = risk_engine.score(forecast=forecast, alerts=alerts)

    try:
        ai_output = await gradient_client.explain_risk(
            location=payload.location,
            latitude=coords.latitude,
            longitude=coords.longitude,
            forecast=forecast,
            alerts=alerts,
            risk_score=risk_score,
            risk_level=risk_level,
        )
    except Exception as exc:
        # Graceful fallback so the UI still works even if Gradient is unreachable.
        # We also surface a short technical note for debugging.
        ai_output = AIExplanation(
            explanation=(
                "We successfully computed a short-term weather risk score from live "
                "National Weather Service data, but the AI explanation service is "
                "temporarily unavailable. You can still use the numeric score and "
                "alerts above to understand relative risk.\n\n"
                f"(Technical details for debugging: Gradient AI error: {exc})"
            ),
            recommendations=[
                "Monitor local weather updates and alerts from official sources.",
                "Avoid unnecessary travel during periods of elevated risk.",
                "Prepare a basic emergency kit appropriate for your area and season.",
            ],
        )

    return RiskAssessmentResponse(
        location=payload.location,
        coordinates=coords,
        current_conditions=forecast.current_conditions,
        short_term_forecast=forecast.short_term,
        alerts=alerts,
        risk_score=risk_score,
        risk_level=risk_level,
        ai=ai_output,
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

