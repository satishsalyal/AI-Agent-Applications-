# Email Summarizer Agent (Gmail + LLM)
# 📧 ➡️ ✨ Email Summarizer Agent  

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)  
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-orange)](https://platform.openai.com/)  
[![Ollama](https://img.shields.io/badge/Ollama-llama3.1-green)](https://ollama.ai)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)  

A lightweight Python agent that connects to **Gmail API**, fetches your emails, and generates **short, crisp summaries** using either **OpenAI GPT** or a **local Ollama model**.  
Save time by scanning bullet-point summaries of long emails directly in Markdown.  

---

## 📂 Project Structure  



Reads long emails and generates short, crisp summaries using either OpenAI or a local LLM via Ollama.

## Features
- Gmail OAuth + search query filter (e.g., `is:unread`, `newer_than:7d`, `from:boss@`)
- Robust MIME extraction (handles plain text & HTML)
- Handles long emails with map-reduce summarization
- Choose **OpenAI** (`gpt-4o-mini` by default) or **Ollama** (`llama3.1` by default)
- Outputs Markdown (`summaries.md`) with subject, from, date, Gmail link, and summary

## Setup

1. **Clone & move into folder**
   ```bash
   cd email_summarizer_agent
   ```

2. **Enable Gmail API & download OAuth credentials**
   - Create a Google Cloud project → Enable **Gmail API**.
   - Create **OAuth client ID (Desktop app)**.
   - Download JSON and save as `client_secret.json` next to the script.

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set your LLM**
   - **OpenAI**: `export OPENAI_API_KEY="sk-..."`
   - **Ollama**: Install & run `ollama` locally (default endpoint `http://localhost:11434`), pull a model:
     ```bash
     ollama pull llama3.1
     ```

## Usage

```bash
python email_summarizer_agent.py --provider openai --max 10 --query "in:inbox newer_than:7d"
# or
python email_summarizer_agent.py --provider ollama --model llama3.1 --max 5 --query "is:unread category:primary"
```

**Common Gmail queries**
- `in:inbox newer_than:7d`
- `is:unread category:primary`
- `from:someone@example.com after:2025/08/01 before:2025/08/20`

The first run opens a browser for Google OAuth. Subsequent runs reuse `token.json`.

## Output
Summaries are printed and saved to `summaries.md` like:

```md
### Project Update
- **From:** Jane Doe <jane@company.com>
- **Date:** Tue, 19 Aug 2025 10:02:55 +0530
- **Gmail ID:** 18c1234a56b7c8d9
- **Link:** https://mail.google.com/mail/u/0/#inbox/18c1234a56b7c8d9

• Budget approved. • Deliverables due Friday. • You to confirm resource plan. • Risks: vendor delay. • Tone: positive, time-sensitive.
```

## Tips
- Use narrower queries (e.g., `is:unread`) to keep token costs low.
- For very long emails, the script chunk-summarizes then compresses.
- You can change the summarization style by editing the `system_prompt` in the code.

## Troubleshooting
- **`Missing client_secret.json`**: Make sure you downloaded OAuth credentials and placed them next to the script.
- **OpenAI 401**: Set `OPENAI_API_KEY`.
- **ConnectionError to Ollama**: Start `ollama serve` and `ollama pull` your model.
- **Rate limits**: Reduce `--max` or narrow your `--query`.

## Security
- The script requests `gmail.readonly` scope and stores `token.json` locally. Keep it safe.
- Do not commit keys or OAuth files to public repos.
