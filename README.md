# MarketVision AI — Market Research Agent (n8n Implementation)

An AI agent workflow that takes a one-line research brief in chat, autonomously researches a market, analyzes competitors, builds a full go-to-market strategy, writes it to a Google Doc, exports it as a PDF, and emails the finished report — all with built-in retry logic and failure guardrails so a bad run never gets delivered as if it succeeded.

> **Status:** n8n implementation complete and tested.

---

## 1. Overview

Given a chat message describing a product/market (e.g. *"MarketVision AI — Research, Market Analysis, and GTM Strategy"*), the workflow:

1. **Researches** the market using an MCP server (primary) with a SerpAPI Google Search fallback
2. **Analyzes** the research into a competitor comparison and SWOT
3. **Builds a GTM strategy** — ICP, positioning, pricing tiers, 90-day plan, KPIs, 4Ps
4. **Assembles a 4-section report** (Research Findings, Market Analysis, GTM Strategy, Sources)
5. **Writes it to a new Google Doc**, then updates it with the full report body
6. **Shares the doc publicly (read-only)** and exports it as a PDF
7. **Emails the PDF** to the requester with run-duration metadata attached

The whole thing is one orchestrating agent (`AI Agent1`) calling three specialized sub-agents (`Research`, `Analyse`, `Strategise`) as tools, plus a strict, ordered system prompt that acts as the workflow's guardrails.

---

## 2. Architecture

```
Chat message
   │
   ▼
Start Run Timer  (stamps run start time)
   │
   ▼
AI Agent1  (orchestrator — Azure OpenAI "vt-agi-chat")
   │
   ├─ Research   (tool)  → MCP Client  → [fallback] Google Search (SerpAPI)
   ├─ Analyse    (tool)
   └─ Strategise (tool)
   │
   ▼
Create a document in Google Docs
   │
   ▼
Update a document in Google Docs   (writes the full report body)
   │
   ▼
Share document for PDF export      (anyone-with-link, read-only)
   │
   ▼
Download Doc as PDF  →  Fix PDF Filename  →  Send a message (Gmail, with PDF attached)
```

Each of `Research`, `Analyse`, and `Strategise` is itself a sub-agent with its own model, memory, and (for Research) tools — not just a prompt template.

---

## 3. Tools & Integrations

| Integration | Used for | Node(s) |
|---|---|---|
| **Azure OpenAI** (`vt-agi-chat` deployment) | LLM backing every agent (orchestrator + 3 sub-agents) | Azure OpenAI Chat Model |
| **MCP server** | Primary market/competitor research source | MCP Client (`http://host.docker.internal:8005/sse`) |
| **SerpAPI** | Fallback Google Search — only called if MCP errors or returns nothing usable | Google search in SerpApi |
| **Google Docs API** | Create + write the report | Create a document in Google Docs, Update a document in Google Docs |
| **Google Drive API** | Make the doc link-shareable; download as PDF | Share document for PDF export, Download Doc as PDF |
| **Gmail API** | Deliver the final PDF report | Send a message |

---

## 4. Prerequisites

- **n8n** instance (self-hosted or cloud) with the LangChain/AI Agent nodes enabled
- **n8n-nodes-serpapi** community node installed
- Credentials configured in n8n for:
  - Azure OpenAI API (deployment name must match `vt-agi-chat`, or update the model field)
  - Google Docs OAuth2
  - Google Drive OAuth2
  - Gmail OAuth2
  - SerpApi API key
- An MCP server reachable from the n8n container at the configured endpoint (default in this build: `http://host.docker.internal:8005/sse`) — update this if your MCP server runs elsewhere
- A Google Drive folder ID to create reports into (set in the "Create a document in Google Docs" node)

---

## 5. Setup

1. Import `Capstone_MCP-Market-Research_Agent.json` into n8n (Workflows → Import from File).
2. Attach your credentials to each node listed in §4 (Azure OpenAI, Google Docs, Google Drive, Gmail, SerpApi).
3. Update the MCP Client node's endpoint URL to point at your running MCP server.
4. Update the Google Docs "Create a document" node's `folderId` to a Drive folder you own.
5. Update the Gmail "Send a message" node's `sendTo` address to your recipient.
6. Activate the workflow (chat trigger is public — set `public: false` if you don't want an open webhook).
7. Open the chat panel and send a one-line brief, e.g.:
   > *"Research MarketVision AI — an AI-powered competitive & market intelligence tool — and produce a market analysis and GTM strategy."*

A finished run delivers a Google Docs link + PDF export link in-chat, and emails the PDF.

---

## 6. Guardrails built into the orchestrator prompt

These are enforced by the `AI Agent1` system prompt, not just left to chance:

- **Research failure guard** — if MCP fails, retry once with an explicit SerpAPI fallback; if that also fails, stop before Analyse/Strategise/Docs and report `RESEARCH_FAILED: <reason>` instead of continuing with empty data.
- **Strict section order** — Research → Analyse → Strategise must be called exactly once, in that order; no skipping ahead to a final answer.
- **Mandatory report structure** — four labeled sections (Research Findings, Market Analysis, GTM Strategy, Sources), each with required sub-sections (Competitor Comparison, SWOT, Pricing Tiers, 4Ps).
- **Placeholder ban** — before writing to Docs, the agent must self-check for filler text (`[INSERT ...]`, `(see Strategise output)`, `TBD`, etc.) and regenerate rather than submit it.
- **No Markdown pipe-tables** — Google Docs renders `| col | col |` as broken text, so all tabular content must be clean labeled bullets instead.
- **Update failure guard** — if writing the report to the Doc fails twice, stop and report the failure in plain text; never present a Docs/PDF link as successful if the write didn't actually succeed.
- **Call-count caps** — Research is capped at ≤8 MCP calls and ≤2 SerpAPI calls per run to control cost and avoid rate limits.

For the full test results validating each of these guardrails, see `TESTING.md`.

---

## 7. Known limitations / Roadmap

- No source snapshotting — cited URLs aren't archived, so a source could change or 404 after the fact
- Citation accuracy is enforced by prompt instruction, not by an automated check against raw Research output
- No automated post-write validation that re-reads the finished Google Doc for formatting drift
- No hard token/cost budget cap — cost is only visible after the fact via Azure AI Foundry's Monitor tab
- **Next up:** a CrewAI implementation of the same agent pipeline, to be tested against the identical rubric and compared on cost/latency/reliability.

---

## 8. Repo contents

| File | Description |
|---|---|
| `Capstone_MCP-Market-Research_Agent.json` | n8n workflow export |
| `TESTING.md` | Full test plan + results (unit, scenario, human-review, cost/latency/reliability) and risk mitigations |
| `MarketVision-AI-Report.pdf` | Example output from a live run (fixed brief: "MarketVision AI") |
