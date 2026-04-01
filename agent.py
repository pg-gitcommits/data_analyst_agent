import anthropic
import subprocess
import sys
import os
import tempfile
import re

client = anthropic.Anthropic()
MODEL = "claude-opus-4-6"

TOOLS = [
    {
        "name": "run_python",
        "description": (
            "Execute Python code to analyze data. "
            "Use pandas, matplotlib, seaborn, or any standard library. "
            "To display a chart, save it with plt.savefig('chart.png', bbox_inches='tight') "
            "and print 'CHART:chart.png'. "
            "Always print results you want the user to see. "
            "The dataframe is pre-loaded as `df`."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Valid Python code to execute."
                }
            },
            "required": ["code"]
        }
    }
]

SYSTEM_PROMPT = """You are a concise data analyst agent. The user uploads a CSV and asks questions.

You have a `run_python` tool. Use it to analyze data and create charts (save with plt.savefig('chart.png')).

Rules:
- Run only 1-2 tool calls maximum per question. No unnecessary exploration.
- Keep answers short — 2-4 sentences max. No bullet points, no lengthy explanations.
- Only show what directly answers the question.
- If a chart says it all, just show the chart with one sentence."""


def execute_python(code: str, csv_path: str, chart_dir: str) -> dict:
    """Run code in a subprocess with the CSV pre-loaded as df."""
    setup = f"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv({repr(csv_path)})
import os
os.chdir({repr(chart_dir)})
"""
    full_code = setup + "\n" + code

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(full_code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        charts = []
        lines = []
        for line in stdout.splitlines():
            if line.startswith("CHART:"):
                chart_file = line[6:].strip()
                full_chart_path = os.path.join(chart_dir, chart_file)
                if os.path.exists(full_chart_path):
                    charts.append(full_chart_path)
            else:
                lines.append(line)

        output = "\n".join(lines).strip()
        if stderr:
            output += f"\n\n[stderr]:\n{stderr}"

        return {"output": output or "(no output)", "charts": charts, "error": bool(result.returncode)}
    except subprocess.TimeoutExpired:
        return {"output": "Error: code execution timed out (30s limit).", "charts": [], "error": True}
    finally:
        os.unlink(tmp_path)


def run_agent(csv_path: str, user_question: str, chart_dir: str, message_history: list = None, on_text=None, on_tool=None, on_result=None):
    messages = message_history if message_history else []
    messages.append({"role": "user", "content": user_question})
    """
    Agentic loop with persistent message history. Yields events as dicts:
      {"type": "text", "content": str}
      {"type": "tool_call", "code": str}
      {"type": "tool_result", "output": str, "charts": list}
      {"type": "done"}

    Args:
      csv_path: path to the uploaded CSV file
      user_question: the user's current question
      chart_dir: directory to save generated charts
      message_history: list of previous messages for multi-turn conversation
    """

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Collect assistant message content
        assistant_content = []

        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
                if on_text:
                    on_text(block.text)
                yield {"type": "text", "content": block.text}

            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

                code = block.input.get("code", "")
                if on_tool:
                    on_tool(code)
                yield {"type": "tool_call", "code": code}

                exec_result = execute_python(code, csv_path, chart_dir)
                if on_result:
                    on_result(exec_result)
                yield {"type": "tool_result", "output": exec_result["output"], "charts": exec_result["charts"]}

                # Append assistant turn + tool result to messages
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": exec_result["output"]
                    }]
                })
                assistant_content = []  # reset for next iteration
                break  # re-enter loop with updated messages

        else:
            # No tool use in this response — we're done
            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})
            yield {"type": "done"}
            break

        if response.stop_reason == "end_turn" and not any(b.type == "tool_use" for b in response.content):
            yield {"type": "done"}
            break
