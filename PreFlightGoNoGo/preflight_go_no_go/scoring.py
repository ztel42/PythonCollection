"""Combine METAR, Kp, and sun into FLY / MARGINAL / DON'T FLY."""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

from .models import (
    FactorResult,
    GoNoGoReport,
    KpReading,
    MetarObservation,
    SunTimes,
    Thresholds,
    Verdict,
    worse,
)


# Thunderstorm / severe weather tokens in METAR wxString
_TS_RE = re.compile(r"(?:\+|-|VC)?TS|SQ|FC|DS|SS|GR", re.I)
_HEAVY_PRECIP_RE = re.compile(r"\+(?:RA|SN|DZ|PL|SG|IC|UP)", re.I)
_PRECIP_RE = re.compile(r"(?:\+|-|VC)?(?:RA|SN|DZ|PL|SG|IC|UP|SH)", re.I)
_FOG_RE = re.compile(r"\b(?:FZFG|FG|BR)\b", re.I)


def score_wind(obs: MetarObservation, t: Thresholds) -> FactorResult:
    wind = obs.wind_kt
    gust = obs.gust_kt
    parts: List[str] = []
    verdict = Verdict.FLY

    if wind is not None:
        parts.append(f"sustained {wind:.0f} kt")
        if wind >= t.wind_nofly_kt:
            verdict = worse(verdict, Verdict.DONT_FLY)
        elif wind >= t.wind_marginal_kt:
            verdict = worse(verdict, Verdict.MARGINAL)
    if gust is not None:
        parts.append(f"gust {gust:.0f} kt")
        if gust >= t.gust_nofly_kt:
            verdict = worse(verdict, Verdict.DONT_FLY)
        elif gust >= t.gust_marginal_kt:
            verdict = worse(verdict, Verdict.MARGINAL)

    if not parts:
        return FactorResult("wind", Verdict.FLY, "wind not reported")
    detail = ", ".join(parts)
    if verdict == Verdict.FLY:
        detail += " (ok)"
    return FactorResult("wind", verdict, detail)


def score_visibility(obs: MetarObservation, t: Thresholds) -> FactorResult:
    vis = obs.vis_sm
    if vis is None:
        return FactorResult("visibility", Verdict.FLY, "visibility not reported")
    label = f"{vis:g}+ SM" if vis >= 10 else f"{vis:g} SM"
    if vis < t.vis_nofly_sm:
        return FactorResult("visibility", Verdict.DONT_FLY, f"{label} (< {t.vis_nofly_sm:g} SM)")
    if vis < t.vis_marginal_sm:
        return FactorResult("visibility", Verdict.MARGINAL, f"{label} (< {t.vis_marginal_sm:g} SM)")
    return FactorResult("visibility", Verdict.FLY, f"{label} (ok)")


def score_ceiling(obs: MetarObservation, t: Thresholds) -> FactorResult:
    ceil = obs.ceiling_ft
    if ceil is None:
        cover = (obs.cover or "CLR/SKC/FEW/SCT").upper()
        return FactorResult("ceiling", Verdict.FLY, f"no BKN/OVC ceiling ({cover})")
    if ceil < t.ceiling_nofly_ft:
        return FactorResult(
            "ceiling",
            Verdict.DONT_FLY,
            f"{ceil} ft AGL (< {t.ceiling_nofly_ft:.0f} ft)",
        )
    if ceil < t.ceiling_marginal_ft:
        return FactorResult(
            "ceiling",
            Verdict.MARGINAL,
            f"{ceil} ft AGL (< {t.ceiling_marginal_ft:.0f} ft)",
        )
    return FactorResult("ceiling", Verdict.FLY, f"{ceil} ft AGL (ok)")


def score_weather(obs: MetarObservation) -> FactorResult:
    wx = (obs.wx_string or "").strip()
    if not wx:
        return FactorResult("weather", Verdict.FLY, "no significant weather")
    if _TS_RE.search(wx):
        return FactorResult("weather", Verdict.DONT_FLY, f"thunderstorm/severe: {wx}")
    if _HEAVY_PRECIP_RE.search(wx):
        return FactorResult("weather", Verdict.DONT_FLY, f"heavy precip: {wx}")
    if re.search(r"FZFG|FZRA|FZDZ", wx, re.I):
        return FactorResult("weather", Verdict.DONT_FLY, f"freezing/fog hazard: {wx}")
    if _FOG_RE.search(wx) and (obs.vis_sm is not None and obs.vis_sm < 3):
        return FactorResult("weather", Verdict.DONT_FLY, f"fog/mist with low vis: {wx}")
    if _PRECIP_RE.search(wx) or _FOG_RE.search(wx):
        return FactorResult("weather", Verdict.MARGINAL, f"precip/mist: {wx}")
    return FactorResult("weather", Verdict.FLY, f"wx {wx} (noted)")


def score_kp(kp: Optional[KpReading], t: Thresholds) -> FactorResult:
    if kp is None:
        return FactorResult("kp", Verdict.FLY, "Kp unavailable (skipped)")
    val = kp.estimated_kp if kp.estimated_kp is not None else kp.kp_index
    # Prefer estimated when available for finer thresholding, but also respect integer kp_index
    use = max(float(kp.kp_index), float(val) if val is not None else 0.0)
    if use >= t.kp_nofly:
        return FactorResult(
            "kp",
            Verdict.DONT_FLY,
            f"Kp {use:g} (≥ {t.kp_nofly:g}) — elevated GPS scintillation risk",
        )
    if use >= t.kp_marginal:
        return FactorResult(
            "kp",
            Verdict.MARGINAL,
            f"Kp {use:g} (≥ {t.kp_marginal:g}) — geomagnetic activity may affect GPS",
        )
    return FactorResult("kp", Verdict.FLY, f"Kp {use:g} (ok)")


def score_sun(sun: Optional[SunTimes], t: Thresholds) -> FactorResult:
    if sun is None:
        return FactorResult("daylight", Verdict.FLY, "sun times unavailable (skipped)")
    if sun.is_daylight:
        return FactorResult(
            "daylight",
            Verdict.FLY,
            f"{sun.phase.replace('_', ' ')} — civil daylight (ok)",
        )
    if t.night_is_nofly:
        return FactorResult("daylight", Verdict.DONT_FLY, "night (outside civil twilight)")
    if t.night_is_marginal:
        return FactorResult("daylight", Verdict.MARGINAL, "night (outside civil twilight)")
    return FactorResult("daylight", Verdict.FLY, "night (night ops allowed by config)")


def evaluate(
    primary: Optional[MetarObservation],
    nearby: Sequence[MetarObservation],
    kp: Optional[KpReading],
    sun: Optional[SunTimes],
    thresholds: Thresholds,
    *,
    location_label: str,
    lat: Optional[float],
    lon: Optional[float],
    generated_at,
) -> GoNoGoReport:
    factors: List[FactorResult] = []
    if primary is None:
        factors.append(FactorResult("metar", Verdict.DONT_FLY, "no METAR available"))
    else:
        factors.append(score_wind(primary, thresholds))
        factors.append(score_visibility(primary, thresholds))
        factors.append(score_ceiling(primary, thresholds))
        factors.append(score_weather(primary))

    factors.append(score_kp(kp, thresholds))
    factors.append(score_sun(sun, thresholds))

    overall = Verdict.FLY
    for f in factors:
        overall = worse(overall, f.verdict)

    return GoNoGoReport(
        verdict=overall,
        factors=factors,
        primary_metar=primary,
        nearby_metars=list(nearby),
        kp=kp,
        sun=sun,
        location_label=location_label,
        lat=lat,
        lon=lon,
        generated_at=generated_at,
        thresholds=thresholds,
    )
