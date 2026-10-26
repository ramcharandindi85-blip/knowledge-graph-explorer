import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONCEPTS_CSV = os.path.join(BASE_DIR, "data", "concepts.csv")
RELATIONSHIPS_CSV = os.path.join(BASE_DIR, "data", "relationships.csv")

CONCEPT_COLUMNS = ["name", "category", "description"]
RELATIONSHIP_COLUMNS = ["source", "target", "relation_type"]


def load_sample_data():
    concepts = pd.read_csv(CONCEPTS_CSV)
    relationships = pd.read_csv(RELATIONSHIPS_CSV)
    return concepts, relationships


def validate_data(concepts, relationships):
    errors = []

    if list(concepts.columns) != CONCEPT_COLUMNS:
        errors.append(f"concepts.csv columns should be {CONCEPT_COLUMNS}")
    if list(relationships.columns) != RELATIONSHIP_COLUMNS:
        errors.append(f"relationships.csv columns should be {RELATIONSHIP_COLUMNS}")
    if errors:
        return errors

    if concepts["name"].isna().any():
        errors.append("Some concepts have an empty name.")
    duplicates = concepts[concepts["name"].duplicated()]["name"].tolist()
    if duplicates:
        errors.append(f"Duplicate concept names: {duplicates}")

    known = set(concepts["name"])
    for _, row in relationships.iterrows():
        if row["source"] not in known:
            errors.append(f"Unknown source concept: {row['source']}")
        if row["target"] not in known:
            errors.append(f"Unknown target concept: {row['target']}")
        if row["source"] == row["target"]:
            errors.append(f"Self-relationship not allowed: {row['source']}")

    dup_rel = relationships[relationships.duplicated(subset=["source", "target"])]
    if not dup_rel.empty:
        errors.append(f"Duplicate relationships: {dup_rel[['source', 'target']].values.tolist()}")

    return errors


def main():
    concepts, relationships = load_sample_data()
    errors = validate_data(concepts, relationships)

    print(f"Concepts loaded      : {len(concepts)}")
    print(f"Relationships loaded : {len(relationships)}")
    print("\nConcepts per category:")
    print(concepts["category"].value_counts().to_string())
    print("\nRelationships per type:")
    print(relationships["relation_type"].value_counts().to_string())

    print("\n" + "-" * 40)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(" -", e)
    else:
        print("VALIDATION PASSED: no problems found.")


if __name__ == "__main__":
    main()