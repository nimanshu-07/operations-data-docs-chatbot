import json
import sqlite3

SQL_PROMPT = """You are a SQL expert working with an operations database.

Schema:
{schema}

Rules:
- Write SELECT statements ONLY (no INSERT, UPDATE, DELETE, DROP, ALTER)
- Use exact column names from the schema above
- Return JSON only: {{"sql": "SELECT ...", "explanation": "what this query does"}}

Question: {question}
"""

INTERPRET_PROMPT = """You are an operations data analyst presenting query results to a user.

The user asked: {question}

SQL executed: {sql}

Query results (JSON):
{results}

Write a clear, concise natural-language answer based on the data.
- Be specific — use exact numbers, names, and dates from the results
- If results are empty, say no matching records were found
- Format numbers and dates readably
- Do not mention SQL in your answer
"""


def query_data(question, conn, tables, model):
    """
    Translates a natural-language question to SQL, executes it,
    and returns a dict: {answer, sql, rows, explanation}
    """
    from data_loader import get_schema_description
    schema = get_schema_description(tables)

    # Step 1: Generate SQL
    sql_response = model.generate_content(
        SQL_PROMPT.format(schema=schema, question=question),
        generation_config={"response_mime_type": "application/json"}
    )

    try:
        sql_data = json.loads(sql_response.text)
        sql = sql_data.get("sql", "").strip()
        explanation = sql_data.get("explanation", "")
    except Exception:
        return {"answer": "Could not generate a valid query.", "sql": None, "rows": [], "explanation": ""}

    # Safety: only allow SELECT
    if not sql.upper().lstrip().startswith("SELECT"):
        return {"answer": "Only SELECT queries are permitted.", "sql": sql, "rows": [], "explanation": ""}

    # Step 2: Execute
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        return {"answer": f"Query error: {e}", "sql": sql, "rows": [], "explanation": explanation}

    # Step 3: Interpret results in natural language
    results_json = json.dumps(rows[:20], indent=2, default=str)
    interpret_response = model.generate_content(
        INTERPRET_PROMPT.format(question=question, sql=sql, results=results_json)
    )

    return {
        "answer": interpret_response.text.strip(),
        "sql": sql,
        "rows": rows,
        "explanation": explanation
    }
