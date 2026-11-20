"""Run the assignment's 10 real Groq questions; record observed calls, never invented results."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import requests
from tool_call import run_question

CASES = [
    ("lecture", "When is Lecture 12 of 100xEngineers Cohort 8, and what is it about?", ["get_lecture"]),
    ("lecture", "Which tools do we use in the seventh class?", ["get_lecture"]),
    ("lecture", "What is an API?", []),
    ("lecture", "Is session ten a combined one or separate?", ["get_lecture"]),
    ("lecture", "In lecture 3 of Harvard CS50, which language is taught?", []),
    ("glossary", "According to my project glossary, what is MFA? Give its example.", ["get_security_term"]),
    ("glossary", "Look up SIEM in my cybersecurity study notes.", ["get_security_term"]),
    ("glossary", "What does the project glossary say about least privilege?", ["get_security_term"]),
    ("glossary", "Does my project glossary contain quantum firewall?", ["get_security_term"]),
    ("glossary", "What is 2 + 2?", []),
]
ROOT = Path(__file__).parent


def render_table(results):
    rows = ["| Question | Should it ask for the tool? | Did it? |",
            "|---|---|---|"]
    for row in results:
        expected = ", ".join(row["expected_tools"]) or "No"
        if row.get("error"):
            observed = "Run failed; see evaluation_results.json"
        else:
            observed = ", ".join(row["observed_tools"]) or "No"
            observed += " (matched)" if row["matched"] else " (mismatch)"
        rows.append(f"| {row['question']} | {expected} | {observed} |")
    return "\n".join(rows)


def update_readme(results):
    path = ROOT / "README.md"
    content = path.read_text()
    for group in ("lecture", "glossary"):
        start = f"<!-- {group}-evaluation:start -->"
        end = f"<!-- {group}-evaluation:end -->"
        before, rest = content.split(start, 1)
        _, after = rest.split(end, 1)
        table = render_table([row for row in results if row["group"] == group])
        content = before + start + "\n" + table + "\n" + end + after
    path.write_text(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-readme", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("GROQ_API_KEY"):
        parser.error("Add GROQ_API_KEY to .env next to tool_call.py before running model evaluations.")
    results = []
    for group, question, expected in CASES:
        row = {"group": group, "question": question, "expected_tools": expected}
        try:
            result = run_question(question)
            observed = sorted({call["name"] for call in result["tool_calls"]})
            row.update(result, observed_tools=observed,
                       matched=observed == sorted(expected))
        except (RuntimeError, requests.RequestException) as exc:
            row.update(error=str(exc), observed_tools=[], matched=False)
        results.append(row)
        # Persist progress if the provider becomes unavailable partway through.
        (ROOT / "evaluation_results.json").write_text(json.dumps({
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            "results": results,
        }, indent=2, ensure_ascii=False) + "\n")
        print(f"{'PASS' if row['matched'] else 'FAIL'}: {question}", flush=True)
    if args.update_readme:
        update_readme(results)
    return 0 if all(row["matched"] for row in results) else 1


if __name__ == "__main__":
    sys.exit(main())
