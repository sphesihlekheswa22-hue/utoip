#!/usr/bin/env python3
"""Generate marketing ad copy for UITOP via OpenRouter (or OpenAI).

Usage (from project root, with .env or env vars set):

  python tools/generate_ad_copy.py
  python tools/generate_ad_copy.py --format linkedin --audience "mid-size companies"
  python tools/generate_ad_copy.py --format video-30s --org-name "Acme Corp"
  python tools/generate_ad_copy.py --prompt-file my-brief.txt

Requires OPENROUTER_API_KEY (or OPENAI_API_KEY) in environment or .env.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

SYSTEM = """You are a B2B SaaS marketing copywriter for UITOP — Unified IT Operations Platform.
UITOP is a workplace IT management product for any organisation (business, school, hospital, NGO, government):
infrastructure inventory, monitoring, helpdesk, assets, security visibility, and IT Copilot — one platform.

Rules:
- Professional, credible, commercial tone (not municipal or government-only).
- Tagline: "One Platform. Every Workplace."
- Avoid hype without substance; mention concrete outcomes (visibility, faster tickets, fewer blind spots).
- Output exactly what the user asks for (headlines, body, CTA, video script with scene directions if requested).
- Do not invent fake customer names unless asked for fictional examples.
"""


def _formats() -> dict[str, str]:
    return {
        "linkedin": (
            "Write a LinkedIn sponsored post: hook line, 3 short paragraphs, bullet benefits (4), "
            "CTA with placeholder link [YOUR-URL]. Max ~900 characters for the main post."
        ),
        "google-search": (
            "Write Google Search ads: 3 headlines (30 chars each), 2 descriptions (90 chars each), "
            "and 5 sitelink ideas with descriptions."
        ),
        "facebook": (
            "Write a Facebook/Instagram feed ad: primary text, headline, description, CTA button label suggestion."
        ),
        "video-30s": (
            "Write a 30-second TV/social video ad script with: VO lines, on-screen text cues, "
            "and b-roll suggestions. End with logo slate and tagline."
        ),
        "video-60s": (
            "Write a 60-second explainer video script: problem (15s), solution UITOP (30s), proof/outcomes (10s), CTA (5s). "
            "Include VO and visual directions."
        ),
        "email": (
            "Write a cold outbound email to an IT Director: subject line + 3 variants, body under 150 words, soft CTA."
        ),
        "billboard": (
            "Write 3 billboard/tagline options (max 7 words each) plus one subline each."
        ),
    }


def build_user_prompt(
    *,
    fmt: str,
    audience: str,
    org_name: str,
    extra: str,
) -> str:
    task = _formats().get(fmt, fmt)
    parts = [
        f"Format/task:\n{task}",
        f"Target audience: {audience}",
        f"Optional white-label org name in examples: {org_name}",
        "Product name: UITOP — Unified IT Operations Platform",
        "Brand green accent (for designer notes only): #16865D",
    ]
    if extra.strip():
        parts.append(f"Additional brief:\n{extra.strip()}")
    return "\n\n".join(parts)


def call_ai(user_prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-..."):
        raise SystemExit(
            "Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env (see .env.example)."
        )

    import openai

    use_openrouter = api_key.startswith("sk-or-") or bool(os.getenv("OPENROUTER_API_KEY"))
    if use_openrouter:
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
                "X-OpenRouter-Title": os.getenv("OPENROUTER_SITE_NAME", "UITOP Ad Generator"),
            },
        )
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    else:
        client = openai.OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2000,
        temperature=0.7,
    )
    content = response.choices[0].message.content
    return (content or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate UITOP ad copy with AI")
    parser.add_argument(
        "--format",
        "-f",
        default="video-30s",
        choices=sorted(_formats().keys()),
        help="Ad format preset",
    )
    parser.add_argument(
        "--audience",
        "-a",
        default="IT leaders and operations teams at SMEs and mid-market organisations",
    )
    parser.add_argument("--org-name", default=os.getenv("ORG_NAME", "Your Organization"))
    parser.add_argument("--prompt-file", type=Path, help="Extra brief from a text file")
    parser.add_argument("--out", type=Path, help="Save output to file")
    args = parser.parse_args()

    extra = ""
    if args.prompt_file and args.prompt_file.is_file():
        extra = args.prompt_file.read_text(encoding="utf-8")

    prompt = build_user_prompt(
        fmt=args.format,
        audience=args.audience,
        org_name=args.org_name,
        extra=extra,
    )
    print(f"Generating ({args.format})…\n", file=sys.stderr)
    text = call_ai(prompt)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"\nSaved to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
