"""OpenRouter: a LangChain chat model for the agent, and cached one-shot JSON calls."""
import json
import re

from langchain_openai import ChatOpenAI

from app import config, http
from app.cache import cached

URL = "https://openrouter.ai/api/v1"


def chat_model() -> ChatOpenAI:
    # the OpenAI client retries 429s itself, honouring Retry-After
    return ChatOpenAI(base_url=URL, api_key=config.OPENROUTER_API_KEY, model=config.OPENROUTER_MODEL,
                      max_retries=4, timeout=60, temperature=0)


def ask_json(prompt: str) -> dict:
    """One prompt -> one JSON object. Cached by model + prompt, so reruns cost nothing."""
    def fetch():
        r = http.request("POST", URL + "/chat/completions", headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
                         json={"model": config.OPENROUTER_MODEL, "temperature": 0,
                               "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"] or ""
        m = re.search(r"\{.*\}", text, re.S)  # models sometimes wrap the JSON in prose or code fences
        if not m:
            raise ValueError(f"LLM reply had no JSON: {text[:200]}")
        return json.loads(m.group(0))

    return cached("llm", {"model": config.OPENROUTER_MODEL, "prompt": prompt}, fetch)
