import io

import networkx as nx
import pandas as pd

from database import get_connection, load_concepts_df, load_relationships_df

CONCEPT_REQUIRED = ["name", "category"]
RELATIONSHIP_REQUIRED = ["source", "target"]
VALID_TYPES = ["prerequisite", "related"]
MAX_ROWS = 5000
MAX_NOTES = 50


def export_concepts_csv():
    return load_concepts_df().to_csv(index=False).encode("utf-8-sig")


def export_relationships_csv():
    return load_relationships_df().to_csv(index=False).encode("utf-8-sig")


def new_report(mode):
    return {
        "ok": False,
        "mode": mode,
        "added_concepts": 0,
        "skipped_concepts": 0,
        "added_relationships": 0,
        "skipped_relationships": 0,
        "errors": [],
        "warnings": [],
        "more_warnings": 0,
    }


def warn(report, message):
    if len(report["warnings"]) < MAX_NOTES:
        report["warnings"].append(message)
    else:
        report["more_warnings"] += 1


def read_csv_bytes(data, label):
    if not data or not data.strip():
        return None, f"{label}: the file is empty."

    df = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            return None, f"{label}: the file is empty."
        except pd.errors.ParserError as error:
            return None, f"{label}: could not read it as a CSV file ({error})."

    df.columns = [str(c).strip().lower() for c in df.columns]
    if len(df) == 0:
        return None, f"{label}: the file has a header row but no data rows."
    if len(df) > MAX_ROWS:
        return None, f"{label}: too many rows ({len(df)}). The limit is {MAX_ROWS}."
    return df, None


def check_columns(df, required, label):
    missing = [c for c in required if c not in df.columns]
    if not missing:
        return None
    message = f"{label}: missing required column(s) {missing}. Columns found: {list(df.columns)}."
    if any(";" in c or "\t" in c for c in df.columns):
        message += " The file looks like it is not comma-separated. Save it as a comma-separated CSV."
    return message


def import_data(report, concepts_df, relationships_df):
    mode = report["mode"]
    if mode not in ("merge", "replace"):
        report["errors"].append("Import mode must be 'merge' or 'replace'.")
        return report
    if concepts_df is None and relationships_df is None:
        report["errors"].append("Choose at least one file to import.")
        return report
    if mode == "replace" and concepts_df is None:
        report["errors"].append("Replace mode needs a concepts file.")
        return report

    conn = get_connection()
    try:
        canonical = {}
        pairs = set()
        H = nx.DiGraph()

        if mode == "merge":
            canonical = {n.lower(): n for n in load_concepts_df()["name"]}
            for row in load_relationships_df().itertuples():
                pairs.add((row.source, row.target))
                if row.relation_type == "prerequisite":
                    H.add_edge(row.source, row.target)

        new_concepts = []
        if concepts_df is not None:
            for n, row in enumerate(concepts_df.to_dict("records"), start=1):
                name = row.get("name", "").strip()
                category = row.get("category", "").strip()
                description = row.get("description", "").strip()
                if not name:
                    warn(report, f"Concepts row {n}: empty name, skipped.")
                elif not category:
                    warn(report, f"Concepts row {n} ('{name}'): empty category, skipped.")
                elif name.lower() in canonical:
                    warn(report, f"Concepts row {n}: '{name}' already exists, skipped.")
                else:
                    canonical[name.lower()] = name
                    new_concepts.append((name, category, description))
                    continue
                report["skipped_concepts"] += 1

        if mode == "replace" and not new_concepts:
            report["errors"].append("No valid concepts were found, so the database was not changed.")
            return report

        new_relationships = []
        if relationships_df is not None:
            for n, row in enumerate(relationships_df.to_dict("records"), start=1):
                source_raw = row.get("source", "").strip()
                target_raw = row.get("target", "").strip()
                relation_type = row.get("relation_type", "").strip().lower() or "prerequisite"
                source = canonical.get(source_raw.lower())
                target = canonical.get(target_raw.lower())
                prefix = f"Relationships row {n} ({source_raw} -> {target_raw})"

                if source is None or target is None:
                    warn(report, f"{prefix}: unknown concept, skipped.")
                elif source == target:
                    warn(report, f"{prefix}: a concept cannot be related to itself, skipped.")
                elif relation_type not in VALID_TYPES:
                    warn(report, f"{prefix}: type '{relation_type}' is not allowed, skipped.")
                elif (source, target) in pairs:
                    warn(report, f"{prefix}: relationship already exists, skipped.")
                elif (
                    relation_type == "prerequisite"
                    and source in H
                    and target in H
                    and nx.has_path(H, target, source)
                ):
                    warn(report, f"{prefix}: would create a prerequisite cycle, skipped.")
                else:
                    pairs.add((source, target))
                    if relation_type == "prerequisite":
                        H.add_edge(source, target)
                    new_relationships.append((source, target, relation_type))
                    continue
                report["skipped_relationships"] += 1

        if mode == "replace":
            conn.execute("DELETE FROM relationships")
            conn.execute("DELETE FROM concepts")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('concepts', 'relationships')")

        conn.executemany(
            "INSERT INTO concepts (name, category, description) VALUES (?, ?, ?)", new_concepts
        )
        ids = dict(conn.execute("SELECT name, id FROM concepts").fetchall())
        conn.executemany(
            "INSERT INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
            [(ids[s], ids[t], r) for s, t, r in new_relationships],
        )
        conn.commit()

        report["added_concepts"] = len(new_concepts)
        report["added_relationships"] = len(new_relationships)
        report["ok"] = True
    except Exception as error:
        conn.rollback()
        report["errors"].append(f"The import failed and nothing was changed: {error}")
    finally:
        conn.close()
    return report


def import_csv_files(concepts_bytes=None, relationships_bytes=None, mode="merge"):
    report = new_report(mode)
    concepts_df = None
    relationships_df = None

    if concepts_bytes is not None:
        concepts_df, error = read_csv_bytes(concepts_bytes, "Concepts file")
        if error is None:
            error = check_columns(concepts_df, CONCEPT_REQUIRED, "Concepts file")
        if error:
            report["errors"].append(error)

    if relationships_bytes is not None:
        relationships_df, error = read_csv_bytes(relationships_bytes, "Relationships file")
        if error is None:
            error = check_columns(relationships_df, RELATIONSHIP_REQUIRED, "Relationships file")
        if error:
            report["errors"].append(error)

    if report["errors"]:
        return report
    return import_data(report, concepts_df, relationships_df)
