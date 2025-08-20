#!/usr/bin/env python3
"""
Email Summarizer Agent
Reads long emails from Gmail and generates short summaries using an LLM
(OpenAI or a local LLM via Ollama).

Quick start:
1) Create a Google Cloud project, enable Gmail API, download OAuth client credentials
   as `client_secret.json` and place it next to this script.
2) Install requirements: `pip install -r requirements.txt`
3) Set your LLM provider in environment variables:
   - For OpenAI: export OPENAI_API_KEY="sk-..."
   - For Ollama: ensure `ollama` is running locally (default http://localhost:11434)
4) Run:
   python email_summarizer_agent.py --provider openai --max 10 --query "in:inbox newer_than:7d"
   OR
   python email_summarizer_agent.py --provider ollama --model "llama3.1" --max 10
5) The script will open a browser on first run to complete Google OAuth.
6) Summaries are printed and saved to `summaries.md` by default.

Tested with Python 3.10+
"""

import os
import re
import base64
import argparse
from typing import List, Dict, Optional, Tuple

# Gmail API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# LLM imports
import requests
import tiktoken  # safe to use for simple token estimation (optional)
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def _ensure_token(client_secret_path: str = "client_secret.json",
                  token_path: str = "token.json") -> Credentials:
    if not os.path.exists(client_secret_path):
        raise FileNotFoundError(
            f"Missing {client_secret_path}. Download your OAuth client credentials "
            f"from Google Cloud Console (Gmail API) and place it next to this script."
        )
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return creds

def get_gmail_service() -> "googleapiclient.discovery.Resource":
    creds = _ensure_token()
    service = build("gmail", "v1", credentials=creds)
    return service

def list_messages(service, user_id: str = "me", query: str = "", max_results: int = 20) -> List[Dict]:
    resp = service.users().messages().list(userId=user_id, q=query, maxResults=max_results).execute()
    return resp.get("messages", [])

def get_message(service, msg_id: str, user_id: str = "me") -> Dict:
    return service.users().messages().get(userId=user_id, id=msg_id, format="full").execute()

def _walk_parts(part) -> List[Dict]:
    parts = []
    if "parts" in part:
        for p in part["parts"]:
            parts.extend(_walk_parts(p))
    else:
        parts.append(part)
    return parts

def _decode_base64url(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("utf-8"))

def extract_plain_text(payload: Dict) -> str:
    """
    Extracts plain text or converts HTML to text when needed.
    """
    text_chunks = []

    # Try headers for subject/from/date
    def get_header(name: str) -> str:
        for h in payload.get("headers", []):
            if h.get("name", "").lower() == name.lower():
                return h.get("value", "")
        return ""

    mime_payload = payload.get("body", {}).get("data")
    if mime_payload:
        data = _decode_base64url(mime_payload)
        text_chunks.append(data.decode(errors="ignore"))

    if "parts" in payload:
        for part in _walk_parts(payload):
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            data = body.get("data")
            if not data:
                continue
            decoded = _decode_base64url(data).decode(errors="ignore")
            if "text/plain" in mime_type:
                text_chunks.append(decoded)
            elif "text/html" in mime_type:
                # very basic HTML to text
                no_scripts = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", decoded)
                text = re.sub(r"(?s)<br\s*/?>", "\n", no_scripts)
                text = re.sub(r"(?s)</p>", "\n\n", text)
                text = re.sub(r"(?s)<.*?>", "", text)
                text_chunks.append(text)

    # Fallback to snippet if nothing else
    full_text = "\n".join([c for c in text_chunks if c]).strip()
    return full_text

# ---------------- LLM Providers ----------------

def summarize_with_openai(text: str, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None) -> str:
    """
    Summarize using OpenAI SDK via REST (no dependency on openai package to keep it light).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Export it before using --provider openai.")
    if not system_prompt:
        system_prompt = (
            "You are an email summarizer. Produce a crisp summary (4-6 bullet points) with: "
            "• key points • action items • deadlines • links/IDs • sentiment. "
            "Keep it under 120 words, neutral tone."
        )
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text[:20000]},  # basic guard
        ],
        "temperature": 0.2,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()

def summarize_with_ollama(text: str, model: str = "llama3.1", system_prompt: Optional[str] = None) -> str:
    if not system_prompt:
        system_prompt = (
            "You are an email summarizer. Produce a crisp summary (4-6 bullet points) with: "
            "• key points • action items • deadlines • links/IDs • sentiment. "
            "Keep it under 120 words, neutral tone."
        )
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": f"{system_prompt}\n\nEmail:\n{text[:20000]}",
        "stream": False,
        "options": {"temperature": 0.2},
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "").strip()

def estimate_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)

def chunk_text(text: str, max_tokens: int = 6000) -> List[str]:
    # very rough chunking by characters; could be improved by sentence boundaries
    approx_chars = max_tokens * 4
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+approx_chars])
        i += approx_chars
    return chunks

def summarize_long_text(text: str, provider: str, model: str) -> str:
    tokens = estimate_tokens(text)
    if tokens < 6000:
        return run_summary(text, provider, model)
    # map-reduce: summarize chunks then summarize the summaries
    chunk_summaries = []
    for chunk in chunk_text(text, 5000):
        chunk_summaries.append(run_summary(chunk, provider, model))
    combined = "\n\n".join(chunk_summaries)
    return run_summary(f"Combine and compress these partial summaries into one under 150 words:\n{combined}",
                       provider, model)

def run_summary(text: str, provider: str, model: str) -> str:
    if provider == "openai":
        return summarize_with_openai(text, model=model)
    elif provider == "ollama":
        return summarize_with_ollama(text, model=model)
    else:
        raise ValueError("provider must be 'openai' or 'ollama'")

# ---------------- Formatting ----------------

def format_summary_md(meta: Dict, summary: str) -> str:
    subject = meta.get("subject", "(no subject)")
    frm = meta.get("from", "(unknown sender)")
    date = meta.get("date", "")
    link = meta.get("permalink", "")
    msg_id = meta.get("id", "")
    lines = [
        f"### {subject}",
        f"- **From:** {frm}",
        f"- **Date:** {date}",
        f"- **Gmail ID:** `{msg_id}`",
    ]
    if link:
        lines.append(f"- **Link:** {link}")
    lines.append("")
    lines.append(summary)
    lines.append("\n---\n")
    return "\n".join(lines)

def parse_headers(payload: Dict) -> Dict[str, str]:
    out = {}
    for h in payload.get("headers", []):
        name = h.get("name", "")
        val = h.get("value", "")
        lname = name.lower()
        if lname in {"subject", "from", "date", "message-id"}:
            out[lname] = val
    return out

# ---------------- Main flow ----------------

def fetch_and_summarize(service, provider: str, model: str, query: str, max_results: int,
                        out_path: str = "summaries.md") -> Tuple[int, str]:
    msgs = list_messages(service, query=query, max_results=max_results)
    if not msgs:
        return 0, "# No messages matched your query.\n"

    md_sections = [f"# Email Summaries ({datetime.now().isoformat(timespec='seconds')})\n"]
    summarized = 0

    for m in msgs:
        raw = get_message(service, m["id"])
        payload = raw.get("payload", {})
        headers = parse_headers(payload)
        text = extract_plain_text(payload)

        if not text.strip():
            # skip empty emails
            continue

        summary = summarize_long_text(text, provider=provider, model=model)
        meta = {
            "subject": headers.get("subject", "(no subject)"),
            "from": headers.get("from", "(unknown sender)"),
            "date": headers.get("date", ""),
            "id": raw.get("id", ""),
            "permalink": f"https://mail.google.com/mail/u/0/#inbox/{raw.get('id', '')}"
        }
        md_sections.append(format_summary_md(meta, summary))
        summarized += 1

    md = "\n".join(md_sections)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    return summarized, out_path

def main():
    parser = argparse.ArgumentParser(description="Email Summarizer Agent (Gmail + LLM)")
    parser.add_argument("--provider", choices=["openai", "ollama"], default="openai",
                        help="LLM provider to use.")
    parser.add_argument("--model", default=None, help="Model name. openai default: gpt-4o-mini, ollama default: llama3.1")
    parser.add_argument("--query", default="in:inbox newer_than:7d",
                        help="Gmail search query. Examples:\n"
                             "  in:inbox newer_than:7d\n"
                             "  is:unread category:primary\n"
                             "  from:boss@example.com after:2025/08/01 before:2025/08/20")
    parser.add_argument("--max", type=int, default=10, help="Max messages to summarize")
    parser.add_argument("--out", default="summaries.md", help="Output Markdown file")
    args = parser.parse_args()

    provider = args.provider
    model = args.model or ("gpt-4o-mini" if provider == "openai" else "llama3.1")

    service = get_gmail_service()
    count, path = fetch_and_summarize(service, provider, model, args.query, args.max, args.out)
    print(f"Summarized {count} email(s). Saved to {path}")

if __name__ == "__main__":
    main()
