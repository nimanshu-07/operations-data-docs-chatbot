import json

ROUTER_PROMPT = """You are a query router for an operations chatbot.

Available structured data tables:
{schema}

Classify the user's question into one of these routes:
- "data"    : needs querying structured/tabular data (counts, filters, aggregations, trends)
- "docs"    : needs searching documentation or knowledge base
- "both"    : needs both structured data and documentation
- "general" : conversational, greeting, or clearly out-of-scope

Respond with JSON only:
{{"route": "data" | "docs" | "both" | "general", "reason": "brief explanation"}}

Question: {question}
"""


def classify_query(question, schema_description, model):
    """Returns one of: 'data', 'docs', 'both', 'general'."""
    prompt = ROUTER_PROMPT.format(schema=schema_description, question=question)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    try:
        result = json.loads(response.text)
        return result.get("route", "general")
    except Exception:
        return "general"
