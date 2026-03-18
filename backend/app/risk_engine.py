from __future__ import annotations

from typing import List, Tuple

from .schemas import Alert, Forecast


class RiskEngine:
    """
    Simple, transparent rule-based risk engine.

    Produces a score from 0–100 and a categorical level
    based on NWS alert severity and short-term weather signals.
    """

    def score(self, forecast: Forecast, alerts: List[Alert]) -> Tuple[int, str]:
        # --- Alerts component (cap 40 pts) ---
        alert_score = 0

        # Best alert drives the base; additional alerts add only a little.
        severity_base = {"Extreme": 40, "Severe": 30, "Moderate": 20, "Minor": 10}
        urgency_bonus = {"immediate": 5, "expected": 3}

        if alerts:
            # Base from the single highest-severity alert
            best = max(alerts, key=lambda a: severity_base.get(a.severity, 0))
            alert_score += severity_base.get(best.severity, 0)
            if best.urgency:
                alert_score += urgency_bonus.get(best.urgency.lower(), 0)

            # Small incremental bonuses for additional alerts
            for alert in alerts:
                if alert is best:
                    continue
                if alert.severity in {"Extreme", "Severe"}:
                    alert_score += 2
                elif alert.severity == "Moderate":
                    alert_score += 1

        alert_score = min(alert_score, 40)

        # --- Current conditions component (cap 30 pts) ---
        cc_score = 0
        cc = forecast.current_conditions
        if cc.is_thunderstorm:
            cc_score += 15
        if cc.is_high_wind:
            cc_score += 15
        if cc.is_extreme_heat:
            cc_score += 15
        if cc.is_heavy_precipitation:
            cc_score += 10

        if cc.wind_speed_kph and cc.wind_speed_kph >= 40:
            cc_score += 10

        if cc.temperature_c is not None:
            if cc.temperature_c >= 35:
                cc_score += 15
            elif cc.temperature_c <= -10:
                cc_score += 10

        cc_score = min(cc_score, 30)

        # --- Short-term forecast component (cap 30 pts, next ~12–24 hours) ---
        st_score = 0
        for period in forecast.short_term.periods[:4]:
            if period.is_thunderstorm:
                st_score += 10
            if period.is_high_wind:
                st_score += 10
            if period.is_extreme_heat:
                st_score += 10
            if period.is_heavy_precipitation:
                st_score += 8

            if period.temperature_c is not None:
                if period.temperature_c >= 35:
                    st_score += 8
                elif period.temperature_c <= -10:
                    st_score += 6

        st_score = min(st_score, 30)

        score = alert_score + cc_score + st_score
        score = max(0, min(100, score))

        if score < 25:
            level = "Low"
        elif score < 50:
            level = "Moderate"
        elif score < 75:
            level = "High"
        else:
            level = "Extreme"

        return score, level

