from __future__ import annotations

import json
import os

from openai import OpenAI

from .models import ResearchFinding, VerificationFinding


MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
client = OpenAI()


RESEARCH_SYSTEM = """You are an API integration researcher.
Use ONLY the source text supplied by the caller. Do not rely on memory.
Your job is to determine whether the named app can be turned into an agent-callable
toolkit today.

Rules:
1. Prefer explicit developer documentation over marketing copy.
2. Do not claim OAuth, API keys, MCP, pricing gates, or public API availability unless
   the supplied sources support it.
3. Evidence URLs must be among the supplied source URLs.
4. 'none-found' for MCP means no official MCP was found in the supplied official pages;
   it does NOT prove no MCP exists anywhere.
5. Buildability 'yes' requires a documented programmable surface and a realistic auth path.
6. If evidence is weak, use 'unknown' and lower confidence.
7. Return concise, reviewer-friendly language.
"""


def research_from_context(app: dict, source_context: str) -> ResearchFinding:
    prompt = f"""Research this app from the supplied official pages.

APP:
{json.dumps(app, ensure_ascii=False)}

OFFICIAL SOURCE MATERIAL:
{source_context}

Return the structured fields exactly as required by the schema.
"""
    response = client.responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": RESEARCH_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        text_format=ResearchFinding,
    )
    return response.output_parsed


VERIFY_SYSTEM = """You are a skeptical verification agent.
You receive a first-pass finding plus freshly rendered official documentation.
Check each material field independently. Only mark a field as matching if the new
official evidence supports the same claim. Put corrected values in `corrections`.
Do not reward plausible guesses. Evidence URLs must come from the supplied pages.
"""


def verify_from_context(
    app: dict,
    first_pass: dict,
    source_context: str,
) -> VerificationFinding:
    prompt = f"""APP:
{json.dumps(app, ensure_ascii=False)}

FIRST PASS:
{json.dumps(first_pass, ensure_ascii=False)}

FRESH OFFICIAL SOURCE MATERIAL:
{source_context}

Check: auth_methods, access_model, api_surface, mcp_status, buildability,
main_blocker. Return corrections only where needed.
"""
    response = client.responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": VERIFY_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        text_format=VerificationFinding,
    )
    return response.output_parsed
