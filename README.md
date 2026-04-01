# Data Analyst Agent

An autonomous AI agent that analyzes CSV files by writing and executing Python code in a loop — powered by Claude's tool use API.

Upload a CSV, ask a question in plain English, and watch the agent plan, write code, run it, interpret results, and answer you — all without any hand-holding.

---

## Demo

> "What are the top 10 products by revenue? Show a bar chart."

The agent will:
1. Explore the dataset (shape, columns, dtypes)
2. Write pandas code to compute the answer
3. Execute it locally via subprocess
4. Generate a matplotlib chart
5. Summarize findings in plain English

---

## Architecture

```
User question
     │
     ▼
┌─────────────────────────────────────┐
│           Agentic Loop              │
│                                     │
│  Claude (claude-opus-4-6)           │
│    ├─ decides what code to write    │
│    ├─ calls run_python tool         │
│    └─ interprets output             │
│                                     │
│  run_python tool                    │
│    ├─ injects df = pd.read_csv(...) │
│    ├─ executes code via subprocess  │
│    └─ returns stdout + chart paths  │
│                                     │
│  Loop continues until end_turn      │
└─────────────────────────────────────┘
     │
     ▼
Streamlit UI (streaming step-by-step)
```

Key agentic properties:
- **Multi-step reasoning**: the agent runs multiple tool calls per question
- **Self-directed**: it decides what to explore without being told
- **Error-aware**: stderr is returned to the model so it can self-correct
- **Stateful**: full message history is maintained across turns

---

## Setup

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/data-analyst-agent
cd data-analyst-agent
pip install -r requirements.txt
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or create a `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run

```bash
streamlit run app.py
```

Open http://localhost:8501

---

## Project Structure

```
data-analyst-agent/
├── agent.py          # Agentic loop + tool execution
├── app.py            # Streamlit UI
├── requirements.txt
└── README.md
```

### `agent.py`
- `run_agent(csv_path, question, chart_dir)` — generator that yields events
- `execute_python(code, csv_path, chart_dir)` — runs code in subprocess, captures stdout + charts
- `TOOLS` — Claude tool definition for `run_python`

### `app.py`
- Streamlit UI with file upload, question input, step-by-step rendering
- Streams agent events live as they arrive

---

## Example questions to try

- "Give me a summary of this dataset"
- "Which columns have missing values and how many?"
- "Show the distribution of [column_name]"
- "What are the top 10 rows by [column]? Show as a bar chart."
- "Is there a correlation between [col_a] and [col_b]?"
- "Group by [category_col] and show average [numeric_col]"

---

## Extending this project

Ideas to take it further:
- **Multi-turn conversation**: pass history between questions so the agent remembers context
- **E2B sandbox**: replace subprocess with [E2B](https://e2b.dev) for secure cloud execution
- **More tools**: add `save_csv`, `run_sql`, `fetch_url` tools
- **Export**: let users download the generated code as a `.py` file
- **Memory**: summarize past analyses and inject as context

---

## Tech stack

| Layer | Tech |
|---|---|
| LLM | Anthropic Claude (claude-opus-4-6) |
| Agent framework | Raw tool use loop (no LangChain) |
| Code execution | Python subprocess |
| UI | Streamlit |
| Data | pandas, matplotlib, seaborn |

---

## Skills demonstrated

| Skill | How it shows up |
|---|---|
| Python | End-to-end project — agent logic, file I/O, subprocess, Streamlit UI |
| Anthropic Claude API | Tool use, multi-step agentic loop, message history management |
| Agentic AI | Agent that plans, writes code, executes, interprets, and loops autonomously |
| Tool use / function calling | Custom `run_python` tool definition and execution cycle |
| Data analysis | pandas, matplotlib, seaborn for CSV exploration and visualization |
| Streamlit | Interactive web UI with live streaming, file upload, session state |
| HTML/CSS | Custom dark theme UI via injected styles in Streamlit |
| Software design | Clean separation of agent logic (`agent.py`) and UI (`app.py`) |

---

## License

MIT