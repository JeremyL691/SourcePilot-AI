from __future__ import annotations

import json
from pathlib import Path

from app.database import SessionLocal, init_db
from app.retrieval.search import search_documents


def main() -> None:
    init_db()
    questions_path = Path("evals/questions.jsonl")
    report_path = Path("evals/eval_report.md")
    rows = []
    with SessionLocal() as db, questions_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            example = json.loads(line)
            hits = search_documents(db, example["question"], top_k=5)
            joined = " ".join(hit.snippet.lower() for hit in hits)
            expected = [term.lower() for term in example.get("expected_source_keywords", [])]
            keyword_hits = sum(1 for term in expected if term in joined)
            citation_ok = bool(hits) if example.get("must_have_citation") else True
            rows.append((example["question"], len(hits), keyword_hits, citation_ok, example.get("expected_tool", "search_documents")))

    total = len(rows) or 1
    citation_score = sum(1 for row in rows if row[3]) / total
    keyword_score = sum(row[2] for row in rows) / max(1, sum(len(json.loads(line).get("expected_source_keywords", [])) for line in questions_path.open("r", encoding="utf-8")))
    lines = [
        "# SourceHero AI Eval Report",
        "",
        f"- Questions: {len(rows)}",
        f"- Citation availability score: {citation_score:.2%}",
        f"- Keyword coverage score: {keyword_score:.2%}",
        "",
        "| Question | Hits | Keyword Hits | Citation OK | Expected Tool |",
        "|---|---:|---:|---|---|",
    ]
    for question, hits, keyword_hits, citation_ok, tool in rows:
        lines.append(f"| {question} | {hits} | {keyword_hits} | {citation_ok} | {tool} |")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()

