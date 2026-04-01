# operations-data-docs-chatbot
Python chatbot for natural-language querying over CSV data and technical documentation using SQLite, ChromaDB, and Gemini.

# Operations Data & Documentation Chatbot

A Python-based chatbot for natural-language queries over **structured datasets (CSV)** and **technical documentation (PDF/TXT)**.  
It combines data processing, prompt design, retrieval, and structured output generation in a single local workflow.

---

## Overview

This chatbot can answer two kinds of questions:

- **Structured data questions** from CSV files
- **Documentation questions** from PDF and TXT files

It routes each question to the correct processing path, retrieves the relevant information, and generates a clean natural-language answer.

---

## How It Works

```text
Your question
      │
   router.py        ← classifies: data / docs / both / general
    ↙      ↘
data_agent  doc_retriever    ← fetch relevant info
    ↘      ↙
  generator.py      ← format structured answer
      │
   Output

```
---

## Documentation pipeline
1. PDF and TXT documents are chunked into smaller sections 
2. Chunks are embedded and stored in ChromaDB 
3. Relevant chunks are retrieved using similarity search 
4. Gemini answers using the retrieved context 

---
