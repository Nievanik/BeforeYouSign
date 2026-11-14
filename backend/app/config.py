"""Only module that reads the environment (see docs/file-structure.md)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")
VEXCEL_API_KEY = os.getenv("VEXCEL_API_KEY", "")
MATTERPORT_API_KEY = os.getenv("MATTERPORT_API_KEY", "")
MATTERPORT_API_TOKEN = os.getenv("MATTERPORT_API_TOKEN", "")
# DEMO=1: Analyze replays a saved dataset (backend/demo_data/) and nothing calls an external API
DEMO = os.getenv("DEMO") == "1"
OFFLINE = os.getenv("OFFLINE") == "1" or DEMO
DEMO_DIR = Path(__file__).resolve().parents[1] / "demo_data"
COSTAR_DIR = Path(__file__).resolve().parents[2] / "Hackathon" / "API_docs" / "costar-kit"
OPENROUTER_VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL") or OPENROUTER_MODEL
USER_AGENT = "BeforeYouSign-hackathon/0.1"  # generic: no personal contact in requests
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")

# Overpass tag filters that mark a competitor / complement, per business type. All [..] parts must match.
# shortcut: only these 5 types; unknown types get an LLM-proposed mapping in Phase 4
_FOOD = '["amenity"~"cafe|restaurant|fast_food"]'
OSM_TAGS = {
    "boba": {"competitor": ['["cuisine"~"bubble_tea"]', _FOOD + '["name"~"boba|bubble tea|milk tea|tea house|teahouse",i]'],
             "complement": ['["amenity"~"school|university|college"]']},
    "coffee": {"competitor": ['["amenity"="cafe"]'], "complement": ['["amenity"~"university|college|library"]']},
    "fast_casual": {"competitor": ['["amenity"="fast_food"]'], "complement": ['["amenity"~"university|college|cinema"]']},
    "salon": {"competitor": ['["shop"~"hairdresser|beauty"]'], "complement": []},
    "boutique": {"competitor": ['["shop"~"clothes|boutique"]'], "complement": ['["shop"~"mall|department_store"]']},
}

BUSINESS_PROFILES = {
    "boba": {
        "typicalDailyCustomers": 110,
        "ticket": 8.00,
        "ticketSd": 1.25,
        "cogsMin": 0.25,
        "cogsMax": 0.35,
        "laborFixedMonthly": 7000.0,
        "laborVariablePct": 0.0,
        "otherFixedMonthly": 1500.0,
        "daysOpen": 30,
        "rampMin": 3,
        "rampMax": 9,
        "startupCost": 110000.0,
        "radiusMi": 1.0,
        "lambda": 2.0,
        "workerWeight": 0.5,
        "newCompetitorRatePerYear": 0.3,
        "rentShareMax": 0.15,
        "yelpCategories": "bubbletea",
    },
    "coffee": {
        "typicalDailyCustomers": 200,
        "ticket": 7.50,
        "ticketSd": 1.50,
        "cogsMin": 0.25,
        "cogsMax": 0.35,
        "laborFixedMonthly": 14400.0,
        "laborVariablePct": 0.0,
        "otherFixedMonthly": 1500.0,
        "daysOpen": 30,
        "rampMin": 3,
        "rampMax": 9,
        "startupCost": 150000.0,
        "radiusMi": 1.0,
        "lambda": 2.0,
        "workerWeight": 0.6,
        "newCompetitorRatePerYear": 0.3,
        "rentShareMax": 0.15,
        "yelpCategories": "coffee",
    },
    "fast_casual": {
        "typicalDailyCustomers": 200,
        "ticket": 16.00,
        "ticketSd": 3.00,
        "cogsMin": 0.26,
        "cogsMax": 0.32,
        "laborFixedMonthly": 28800.0,
        "laborVariablePct": 0.0,
        "otherFixedMonthly": 4000.0,
        "daysOpen": 30,
        "rampMin": 3,
        "rampMax": 9,
        "startupCost": 350000.0,
        "radiusMi": 1.5,
        "lambda": 2.0,
        "workerWeight": 0.8,
        "newCompetitorRatePerYear": 0.4,
        "rentShareMax": 0.10,
        "yelpCategories": "hotdogs,sandwiches,burgers",
    },
    "salon": {
        "typicalDailyCustomers": 25,
        "ticket": 70.00,
        "ticketSd": 15.00,
        "cogsMin": 0.05,
        "cogsMax": 0.12,
        "laborFixedMonthly": 3000.0,
        "laborVariablePct": 0.40,
        "otherFixedMonthly": 1500.0,
        "daysOpen": 26,
        "rampMin": 6,
        "rampMax": 12,
        "startupCost": 90000.0,
        "radiusMi": 3.0,
        "lambda": 1.5,
        "workerWeight": 0.1,
        "newCompetitorRatePerYear": 0.3,
        "rentShareMax": 0.15,
        "yelpCategories": "hair",
    },
    "boutique": {
        "typicalDailyCustomers": 25,
        "ticket": 80.00,
        "ticketSd": 20.00,
        "cogsMin": 0.42,
        "cogsMax": 0.52,
        "laborFixedMonthly": 7000.0,
        "laborVariablePct": 0.0,
        "otherFixedMonthly": 1500.0,
        "daysOpen": 30,
        "rampMin": 4,
        "rampMax": 10,
        "startupCost": 75000.0,
        "radiusMi": 3.0,
        "lambda": 1.5,
        "workerWeight": 0.2,
        "newCompetitorRatePerYear": 0.2,
        "rentShareMax": 0.15,
        "yelpCategories": "boutique,clothing",
    },
}
