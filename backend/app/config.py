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
OFFLINE = os.getenv("OFFLINE") == "1"
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
