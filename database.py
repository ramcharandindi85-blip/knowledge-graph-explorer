import os
import sqlite3

import pandas as pd

from graph_engine import build_graph
from load_data import load_sample_data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "knowledge_graph.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            description TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            relation_type TEXT NOT NULL,
            UNIQUE (source_id, target_id),
            FOREIGN KEY (source_id) REFERENCES concepts(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES concepts(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


def count_rows():
    conn = get_connection()
    concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
    relationships = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    conn.close()
    return concepts, relationships


def seed_database():
    concepts_count, _ = count_rows()
    if concepts_count > 0:
        return False

    concepts, relationships = load_sample_data()
    conn = get_connection()

    for _, row in concepts.iterrows():
        conn.execute(
            "INSERT INTO concepts (name, category, description) VALUES (?, ?, ?)",
            (row["name"], row["category"], row["description"]),
        )

    ids = dict(conn.execute("SELECT name, id FROM concepts").fetchall())
    for _, row in relationships.iterrows():
        conn.execute(
            "INSERT INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
            (ids[row["source"]], ids[row["target"]], row["relation_type"]),
        )

    conn.commit()
    conn.close()
    return True


def load_concepts_df():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT name, category, description FROM concepts ORDER BY id", conn
    )
    conn.close()
    return df


def load_relationships_df():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT s.name AS source, t.name AS target, r.relation_type
        FROM relationships r
        JOIN concepts s ON s.id = r.source_id
        JOIN concepts t ON t.id = r.target_id
        ORDER BY r.id
        """,
        conn,
    )
    conn.close()
    return df


def load_graph_from_db():
    return build_graph(load_concepts_df(), load_relationships_df())


def main():
    init_db()
    seeded = seed_database()
    if seeded:
        print("Database was empty, so it was filled from the CSV files.")
    else:
        print("Database already has data, nothing was added.")

    concepts_count, relationships_count = count_rows()
    print(f"Database file         : {DB_PATH}")
    print(f"Concepts in database  : {concepts_count}")
    print(f"Relationships in database : {relationships_count}")

    G = load_graph_from_db()
    print(f"Graph built from database: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")


if __name__ == "__main__":
    main()
