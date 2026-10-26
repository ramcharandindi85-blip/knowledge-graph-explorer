import networkx as nx
import pandas as pd

from database import get_connection, load_graph_from_db
from graph_engine import prerequisite_graph

RELATION_TYPES = ["prerequisite", "related"]


def clean(text):
    return (text or "").strip()


def find_concept_id(conn, name):
    row = conn.execute("SELECT id FROM concepts WHERE name = ?", (name,)).fetchone()
    return row[0] if row else None


def name_is_taken(conn, name, ignore_id=None):
    row = conn.execute(
        "SELECT id FROM concepts WHERE LOWER(name) = LOWER(?)", (name,)
    ).fetchone()
    return row is not None and row[0] != ignore_id


def would_create_cycle(source, target):
    H = prerequisite_graph(load_graph_from_db())
    if source not in H or target not in H:
        return False
    return nx.has_path(H, target, source)


def get_categories():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT category FROM concepts ORDER BY category").fetchall()
    conn.close()
    return [r[0] for r in rows]


def search_concepts(text="", category=None):
    text = clean(text)
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"

    query = (
        "SELECT name, category, description FROM concepts "
        "WHERE (name LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')"
    )
    params = [pattern, pattern]
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY name"

    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def add_concept(name, category, description=""):
    name, category, description = clean(name), clean(category), clean(description)
    if not name:
        return False, "Concept name cannot be empty."
    if not category:
        return False, "Category cannot be empty."

    conn = get_connection()
    try:
        if name_is_taken(conn, name):
            return False, f"A concept named '{name}' already exists."
        conn.execute(
            "INSERT INTO concepts (name, category, description) VALUES (?, ?, ?)",
            (name, category, description),
        )
        conn.commit()
        return True, f"Added concept '{name}'."
    finally:
        conn.close()


def update_concept(old_name, new_name, category, description=""):
    new_name, category, description = clean(new_name), clean(category), clean(description)
    if not new_name:
        return False, "Concept name cannot be empty."
    if not category:
        return False, "Category cannot be empty."

    conn = get_connection()
    try:
        concept_id = find_concept_id(conn, old_name)
        if concept_id is None:
            return False, f"Concept '{old_name}' does not exist."
        if name_is_taken(conn, new_name, ignore_id=concept_id):
            return False, f"A concept named '{new_name}' already exists."
        conn.execute(
            "UPDATE concepts SET name = ?, category = ?, description = ? WHERE id = ?",
            (new_name, category, description, concept_id),
        )
        conn.commit()
        return True, f"Updated concept '{new_name}'."
    finally:
        conn.close()


def delete_concept(name):
    conn = get_connection()
    try:
        concept_id = find_concept_id(conn, name)
        if concept_id is None:
            return False, f"Concept '{name}' does not exist."
        removed = conn.execute(
            "SELECT COUNT(*) FROM relationships WHERE source_id = ? OR target_id = ?",
            (concept_id, concept_id),
        ).fetchone()[0]
        conn.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))
        conn.commit()
        return True, f"Deleted concept '{name}' and {removed} related relationship(s)."
    finally:
        conn.close()


def add_relationship(source, target, relation_type):
    source, target, relation_type = clean(source), clean(target), clean(relation_type)
    if relation_type not in RELATION_TYPES:
        return False, f"Relationship type must be one of {RELATION_TYPES}."
    if source == target:
        return False, "A concept cannot be related to itself."
    if relation_type == "prerequisite" and would_create_cycle(source, target):
        return False, f"Not added: '{target}' already leads back to '{source}', so this would create a cycle."

    conn = get_connection()
    try:
        source_id = find_concept_id(conn, source)
        target_id = find_concept_id(conn, target)
        if source_id is None or target_id is None:
            return False, "Both concepts must exist."
        existing = conn.execute(
            "SELECT 1 FROM relationships WHERE source_id = ? AND target_id = ?",
            (source_id, target_id),
        ).fetchone()
        if existing:
            return False, f"A relationship from '{source}' to '{target}' already exists."
        conn.execute(
            "INSERT INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
            (source_id, target_id, relation_type),
        )
        conn.commit()
        return True, f"Added: {source} -> {target} ({relation_type})."
    finally:
        conn.close()


def update_relationship(source, target, new_type):
    new_type = clean(new_type)
    if new_type not in RELATION_TYPES:
        return False, f"Relationship type must be one of {RELATION_TYPES}."
    if new_type == "prerequisite" and would_create_cycle(source, target):
        return False, f"Not changed: '{target}' already leads back to '{source}', so this would create a cycle."

    conn = get_connection()
    try:
        source_id = find_concept_id(conn, source)
        target_id = find_concept_id(conn, target)
        if source_id is None or target_id is None:
            return False, "Both concepts must exist."
        cursor = conn.execute(
            "UPDATE relationships SET relation_type = ? WHERE source_id = ? AND target_id = ?",
            (new_type, source_id, target_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return False, f"No relationship from '{source}' to '{target}'."
        return True, f"Updated: {source} -> {target} is now '{new_type}'."
    finally:
        conn.close()


def delete_relationship(source, target):
    conn = get_connection()
    try:
        source_id = find_concept_id(conn, source)
        target_id = find_concept_id(conn, target)
        if source_id is None or target_id is None:
            return False, "Both concepts must exist."
        cursor = conn.execute(
            "DELETE FROM relationships WHERE source_id = ? AND target_id = ?",
            (source_id, target_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return False, f"No relationship from '{source}' to '{target}'."
        return True, f"Deleted relationship {source} -> {target}."
    finally:
        conn.close()
