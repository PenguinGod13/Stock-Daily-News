import json

import requests

OLLAMA_CHAT_URL = "https://ollama.com/api/chat"

DIGEST_SYSTEM_PROMPT = """You are a financial digest writer. You will receive JSON \
describing a user's stock watchlist (with price moves, ownership, and recent \
headlines) and broader market/sector trends.

IMPORTANT: A numeric summary table (ticker, price, % change, P&L) is already \
shown separately in the email. Do NOT reproduce price data, percentages, or \
ticker symbols as a list or table in your response — that would be redundant. \
Your job is to provide narrative context, explanation, and insight only.

Write a concise morning digest in Markdown with exactly these four sections, \
in this order:

1. TL;DR - 2-3 sentences on the overall morning picture.
2. Your movers - for tickers where is_mover is true: a short sentence or two \
explaining WHY they moved, based on their headlines. Include unrealised P&L \
context for owned tickers. If no tickers are movers, say so briefly.
3. Rest of your watchlist - for non-mover tickers: one sentence of news \
context or notable observation per ticker (NOT price data — the table covers \
that). If there is no interesting context, skip this section entirely rather \
than writing filler.
4. Market pulse & hot sectors - themes and sectors from the market trends data, \
including ones outside the user's watchlist.

Be factual and concise. Do not invent headlines or events not present in the \
input. Do not use markdown tables."""


def build_prompt(ticker_records, market_trends):
    return json.dumps({"tickers": ticker_records, "market_trends": market_trends})


def call_ollama_chat(ollama_api_key, prompt, model="gpt-oss:120b"):
    resp = requests.post(
        OLLAMA_CHAT_URL,
        headers={"Authorization": f"Bearer {ollama_api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": DIGEST_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def build_fallback_digest(ticker_records, market_trends):
    lines = ["# Morning Digest (fallback — AI summary unavailable)", ""]

    movers = [r for r in ticker_records if r["is_mover"]]
    lines.append("## Your movers")
    if movers:
        for r in movers:
            pl_str = (
                f", P&L: ${r['unrealized_pl']:.2f}"
                if r.get("unrealized_pl") is not None
                else ""
            )
            lines.append(f"- {r['ticker']}: {r['pct_change']:.2f}%{pl_str}")
            for headline in r.get("top_headlines", [])[:3]:
                lines.append(f"  - {headline['headline']}")
    else:
        lines.append("- No tickers moved beyond the threshold today.")
    lines.append("")

    lines.append("## Rest of your watchlist")
    rest = [r for r in ticker_records if not r["is_mover"]]
    if rest:
        for r in rest:
            lines.append(f"- {r['ticker']}: {r['pct_change']:.2f}%")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Market pulse & hot sectors")
    if market_trends:
        for t in market_trends[:5]:
            lines.append(f"- {t['title']}")
    else:
        lines.append("- No market trend data available.")

    return "\n".join(lines)


def build_digest(ollama_api_key, ticker_records, market_trends, model="gpt-oss:120b"):
    prompt = build_prompt(ticker_records, market_trends)
    last_error = None
    for _ in range(2):
        try:
            return call_ollama_chat(ollama_api_key, prompt, model=model)
        except Exception as e:
            last_error = e
    return build_fallback_digest(ticker_records, market_trends)
