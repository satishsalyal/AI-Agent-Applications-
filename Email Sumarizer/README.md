 
# 📧 ➡️ ✨ Email Summarizer Agent (Gmail + LLM)


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

