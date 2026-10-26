# Knowledge Graph Explorer

An interactive application that visualises and analyses relationships between computer science concepts. ITW III project by D. Sai Ram Charan (2025BCD0013).

Concepts (for example *Arrays*, *Recursion*, *SQL*) are stored as nodes of a directed graph, and relationships between them (*prerequisite* or *related*) as edges. The app lets you explore the graph, find paths, list prerequisites and measure which concepts matter most.

## Features

- Interactive graph, coloured by category, with a category filter
- Add, search, edit and delete concepts and relationships
- Shortest path between two concepts, highlighted in the graph
- Direct and indirect prerequisites in a valid learning order
- Degree centrality and graph statistics
- Permanent storage in SQLite
- CSV import (add or replace, with row-by-row validation) and CSV export
- Rejects duplicates, self-relationships and prerequisite cycles

## Technology

Python, NetworkX, SQLite, Pandas, Streamlit, Plotly, Matplotlib, Jupyter Notebook.

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python check_setup.py
```

On macOS/Linux, activate with `source venv/bin/activate`.

## Run

```
streamlit run app.py
```

The database `data/knowledge_graph.db` is created automatically on the first run from the sample files in `data/`.

The notebook with all experiments and outputs is in `notebooks/knowledge_graph_explorer.ipynb`:

```
jupyter notebook
```

## Project structure

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit application (six tabs) |
| `graph_view.py` | Draws the interactive graph |
| `graph_engine.py` | Builds the NetworkX graph |
| `analysis.py` | Shortest paths, prerequisites, centrality, statistics |
| `database.py` | SQLite tables and storage |
| `crud.py` | Add, edit, delete, search with validation |
| `csv_io.py` | CSV import and export |
| `load_data.py` | Loads and validates the sample CSV files |
| `check_setup.py` | Checks that all libraries are installed |
| `data/` | Sample dataset (35 concepts, 49 relationships) |
| `notebooks/` | Jupyter Notebook |
| `reports/` | Project report (PDF) |
| `test_concepts.csv`, `test_relationships.csv` | Deliberately faulty files for testing the CSV import |
