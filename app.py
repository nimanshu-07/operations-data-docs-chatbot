import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from config import GENERATION_MODEL, DATA_FOLDER
from data_loader import load_csv_files, get_schema_description
from doc_ingest import ingest_docs
from doc_retriever import retrieve
from router import classify_query
from data_agent import query_data
from generator import generate_doc_answer, format_response

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

BANNER = """
╔══════════════════════════════════════════════════════╗
║     Operations Data & Documentation Chatbot          ║
║  Ask questions about your data or documentation.     ║
║  Commands: /sources  /sql  /reset  /help  /quit      ║
╚══════════════════════════════════════════════════════╝"""

HELP_TEXT = """
Commands:
  /sources  — show document sources used in last answer
  /sql      — show the SQL query from last data answer
  /reset    — clear conversation history
  /help     — show this message
  /quit     — exit

Tips:
  - Drop CSVs into the 'data/' folder for structured queries
  - Drop PDFs or TXTs into the 'docs/' folder for document search
  - Re-run the app after adding new files (or use doc_ingest.py --reset)
"""


def main():
    print(BANNER)

    model = genai.GenerativeModel(GENERATION_MODEL)

    # Load structured data from CSV files
    print("\nLoading structured data...")
    conn, tables = load_csv_files(DATA_FOLDER)
    schema_desc = get_schema_description(tables)
    if tables:
        print(f"  Tables loaded: {', '.join(tables.keys())}")
    else:
        print("  No CSV data found. Add CSVs to the 'data/' folder.")

    # Ingest documents into ChromaDB
    print("Indexing documents (skips already-indexed files)...")
    ingest_docs()

    print("\nReady. Ask a question or type /help.\n")

    history = []
    last_doc_result = None
    last_data_result = None

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue

        # --- Commands ---
        cmd = question.lower()

        if cmd == "/quit":
            print("Goodbye!")
            break

        if cmd == "/help":
            print(HELP_TEXT)
            continue

        if cmd == "/reset":
            history = []
            last_doc_result = last_data_result = None
            print("Conversation history cleared.\n")
            continue

        if cmd == "/sources":
            if last_doc_result and last_doc_result.get("sources"):
                print("\nSources used:")
                for s in last_doc_result["sources"]:
                    print(f"  - {s.get('file', '?')} (page {s.get('page', '?')})")
            else:
                print("No document sources from the last answer.")
            print()
            continue

        if cmd == "/sql":
            if last_data_result and last_data_result.get("sql"):
                print(f"\nSQL: {last_data_result['sql']}\n")
            else:
                print("No SQL query from the last answer.\n")
            continue

        # --- Route and answer ---
        last_doc_result = None
        last_data_result = None

        try:
            route = classify_query(question, schema_desc, model)

            if route in ("data", "both") and tables:
                last_data_result = query_data(question, conn, tables, model)

            if route in ("docs", "both"):
                chunks = retrieve(question)
                last_doc_result = generate_doc_answer(question, chunks, history, model)

            if route == "general" or (route in ("data", "both") and not tables):
                response = model.generate_content(question)
                answer = response.text.strip()
                print(f"\nAssistant: {answer}\n")
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": answer})
                if len(history) > 8:
                    history = history[-8:]
                continue

            answer = format_response(route, last_doc_result, last_data_result)
            print(f"\nAssistant: {answer}\n")

            # Keep a summary in history (avoid huge data dumps)
            history_answer = answer.split("\n")[0][:300]
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": history_answer})
            if len(history) > 8:
                history = history[-8:]

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
