"""Turn the user's sentence into a BusinessBrief, and find (or have the LLM propose) the business profile."""
from app import config
from app.llm import ask_json
from app.models import BusinessBrief
from app.sim import PROFILE_FIELDS

BRIEF_PROMPT = """Extract a site-search brief from this request to open a small business.
Request: {query!r}
Reply with ONLY JSON:
{{"businessType": "<short lowercase type; use one of {types} if it fits, else your own words>",
  "city": "Houston" or "Los Angeles" (default "Houston"),
  "maxRentMonthly": <number, US dollars per month; 6000 if not given>,
  "sizeSqftMin": <number or null>, "sizeSqftMax": <number or null>,
  "parkingRequired": <true only if the request says parking is needed or a must, else false>,
  "mustHaves": [<other short requirements such as "corner lot", "drive-thru">]}}"""

PROFILE_PROMPT = """Give typical small-business numbers for a new "{kind}" in a US city. Reply with ONLY JSON with
these numeric keys: {fields}.
Meanings: typicalDailyCustomers (customers/day at an established shop), ticket and ticketSd (US$ per visit),
cogsMin/cogsMax and laborVariablePct and rentShareMax (fractions 0-1), laborFixedMonthly and otherFixedMonthly
(US$/month), daysOpen (per month), rampMin/rampMax (months to reach steady sales), startupCost (US$),
radiusMi (miles customers travel), lambda (distance decay 1.5-2.5), workerWeight (0-1, how much a nearby worker
counts vs a resident), newCompetitorRatePerYear (new rivals opening nearby per year)."""


def parse_brief(query: str) -> BusinessBrief:
    types = sorted(getattr(config, "BUSINESS_PROFILES", {}))
    raw = ask_json(BRIEF_PROMPT.format(query=query, types=types or ["boba", "coffee", "hair salon"]))
    if raw.get("city") not in ("Houston", "Los Angeles"):
        raw["city"] = "Houston"  # the CoStar kit covers only these two cities
    return BusinessBrief(**{k: v for k, v in raw.items() if v is not None})


def profile_for(business_type: str) -> tuple[dict, bool]:
    """(profile, is_ai_estimate). Preset profiles win; anything else is proposed by the LLM and flagged."""
    presets = getattr(config, "BUSINESS_PROFILES", {})
    if business_type in presets:
        return presets[business_type], False
    raw = ask_json(PROFILE_PROMPT.format(kind=business_type, fields=", ".join(sorted(PROFILE_FIELDS))))
    missing = PROFILE_FIELDS - set(raw)
    if missing:
        raise ValueError(f"LLM profile for {business_type!r} is missing {sorted(missing)}")
    return {k: float(raw[k]) for k in PROFILE_FIELDS}, True
