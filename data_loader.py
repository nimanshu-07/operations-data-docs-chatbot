import os
import sqlite3
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def load_csv_files(data_folder):
    """
    Loads all CSVs from data_folder into an in-memory SQLite database.
    Returns (connection, tables_dict) where tables_dict maps table_name -> [columns].
    """
    conn = sqlite3.connect(":memory:")
    tables = {}

    if not os.path.exists(data_folder):
        logger.warning(f"Data folder '{data_folder}' not found.")
        return conn, tables

    csv_files = [f for f in os.listdir(data_folder) if f.endswith(".csv")]
    if not csv_files:
        logger.warning(f"No CSV files found in '{data_folder}'")
        return conn, tables

    for filename in sorted(csv_files):
        table_name = os.path.splitext(filename)[0].lower().replace(" ", "_").replace("-", "_")
        filepath = os.path.join(data_folder, filename)
        try:
            df = pd.read_csv(filepath)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            tables[table_name] = list(df.columns)
            logger.info(f"Loaded '{filename}' as table '{table_name}' ({len(df)} rows, {len(df.columns)} cols)")
        except Exception as e:
            logger.error(f"Failed to load '{filename}': {e}")

    return conn, tables


def get_schema_description(tables):
    """Returns a human-readable string of all tables and their columns."""
    if not tables:
        return "No structured data loaded."
    lines = []
    for table, cols in tables.items():
        lines.append(f"Table '{table}': {', '.join(cols)}")
    return "\n".join(lines)
