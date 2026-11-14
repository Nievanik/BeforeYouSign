"""LLM vision (OpenRouter): storefront visibility and road access from the aerial image."""
import base64
import hashlib
import json
import re

from app import config, http
from app.cache import cached

URL = "https://openrouter.ai/api/v1/chat/completions"
PROMPT = """This is a top-down aerial photo of a retail site; the parcel is outlined in gold.
Score it for a small walk-in business. Reply with ONLY a JSON object:
{"visibilityScore": 1-5, "visibilityReason": "<one short sentence>",
 "roadAccessScore": 1-5, "roadAccessReason": "<one short sentence>"}
visibility = how easily passing drivers/pedestrians would notice the storefront (frontage on a main road, corner, setback).
roadAccess = how easy it is to drive in and park (driveways, lot size, medians)."""


def score_aerial(jpeg: bytes) -> dict:
    """{visibilityScore, visibilityReason, roadAccessScore, roadAccessReason}"""
    def fetch():
        r = http.request("POST", URL, headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}, json={
            "model": config.OPENROUTER_VISION_MODEL,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}}]}]})
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", text, re.S)  # models sometimes wrap the JSON in prose or code fences
        if not m:
            raise ValueError(f"vision reply had no JSON: {text[:200]}")
        out = json.loads(m.group(0))
        for k in ("visibilityScore", "roadAccessScore"):
            out[k] = min(5, max(1, int(out[k])))
        return {k: out[k] for k in ("visibilityScore", "visibilityReason", "roadAccessScore", "roadAccessReason")}

    key = {"img": hashlib.sha1(jpeg).hexdigest(), "model": config.OPENROUTER_VISION_MODEL, "prompt": PROMPT}
    return cached("vision", key, fetch)
