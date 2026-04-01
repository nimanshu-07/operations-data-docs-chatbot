import json

STRUCTURED_DOC_PROMPT = """You are a helpful assistant answering questions from operations documentation.

{history_text}Document context:
{context}

Question: {question}

Respond with JSON only using these fields:
- "answer": your answer based strictly on the context (say "I don't know based on the provided documents" if not found)
- "confidence": "high" if clearly stated in context, "medium" if inferred, "low" if uncertain
- "sources": list of {{"file": "filename", "page": 1}} for each source used
- "follow_up_suggestions": up to 2 related questions the user might want to ask next
"""


def generate_doc_answer(question, chunks, history, model):
    """
    Generates a structured JSON answer from retrieved document chunks.
    Returns dict with: answer, confidence, sources, follow_up_suggestions
    """
    from doc_retriever import format_context

    context = format_context(chunks) if chunks else "No relevant documents found."

    history_text = ""
    if history:
        history_text = "Conversation so far:\n"
        for turn in history:
            role = "User" if turn["role"] == "user" else "Assistant"
            history_text += f"{role}: {turn['content']}\n"
        history_text += "\n"

    prompt = STRUCTURED_DOC_PROMPT.format(
        history_text=history_text,
        context=context,
        question=question
    )

    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )

    try:
        return json.loads(response.text)
    except Exception:
        return {
            "answer": response.text.strip(),
            "confidence": "medium",
            "sources": [],
            "follow_up_suggestions": []
        }


def format_response(route, doc_result=None, data_result=None):
    """Formats the final display output."""
    lines = []

    # --- Structured data section ---
    if route in ("data", "both") and data_result:
        lines.append(data_result.get("answer", ""))

        rows = data_result.get("rows", [])
        if rows:
            cols = list(rows[0].keys())
            col_widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
            header = "  ".join(c.ljust(col_widths[c]) for c in cols)
            separator = "  ".join("-" * col_widths[c] for c in cols)
            lines.append(f"\n{header}")
            lines.append(separator)
            for row in rows[:15]:
                lines.append("  ".join(str(row.get(c, "")).ljust(col_widths[c]) for c in cols))
            if len(rows) > 15:
                lines.append(f"... ({len(rows) - 15} more rows)")

    # --- Documentation section ---
    if route in ("docs", "both") and doc_result:
        if route == "both":
            lines.append("\nFrom documentation:")
        lines.append(doc_result.get("answer", ""))

        confidence = doc_result.get("confidence", "")
        if confidence:
            lines.append(f"\n[Confidence: {confidence}]")

        sources = doc_result.get("sources", [])
        if sources:
            lines.append("Sources:")
            for s in sources:
                lines.append(f"  - {s.get('file', '?')} (page {s.get('page', '?')})")

        suggestions = doc_result.get("follow_up_suggestions", [])
        if suggestions:
            lines.append("\nYou might also ask:")
            for s in suggestions:
                lines.append(f"  • {s}")

    if not lines:
        return "I couldn't find relevant information for your question."

    return "\n".join(lines)
