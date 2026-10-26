import streamlit as st

from analysis import (
    find_shortest_path,
    get_all_dependents,
    get_all_prerequisites,
    get_degree_centrality,
    get_graph_statistics,
)
from crud import (
    RELATION_TYPES,
    add_concept,
    add_relationship,
    delete_concept,
    delete_relationship,
    get_categories,
    search_concepts,
    update_concept,
    update_relationship,
)
from csv_io import export_concepts_csv, export_relationships_csv, import_csv_files
from database import init_db, load_graph_from_db, load_relationships_df, seed_database
from graph_engine import get_direct_dependents, get_direct_prerequisites
from graph_view import build_figure

st.set_page_config(page_title="Knowledge Graph Explorer", layout="wide")

init_db()
seed_database()
G = load_graph_from_db()
names = sorted(G.nodes())
categories = get_categories()


def finish(result):
    ok, message = result
    if ok:
        st.session_state["flash"] = message
        st.rerun()
    else:
        st.error(message)


def pick_category(selected, typed):
    return typed.strip() or selected


st.title("Knowledge Graph Explorer")
st.caption("Relationships between computer science concepts")

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

st.sidebar.header("Filter")
selected_categories = st.sidebar.multiselect("Show categories", categories, default=categories)
visible = [n for n, d in G.nodes(data=True) if d["category"] in selected_categories]

st.sidebar.header("Shortest path")
if len(names) >= 2:
    source = st.sidebar.selectbox("From", names, index=names.index("Programming Basics") if "Programming Basics" in names else 0)
    target = st.sidebar.selectbox("To", names, index=names.index("Graph Algorithms") if "Graph Algorithms" in names else 1)
    ignore_direction = st.sidebar.checkbox("Ignore edge direction")
    show_path = st.sidebar.checkbox("Highlight path in graph", value=True)
    path = find_shortest_path(G, source, target, directed=not ignore_direction)
else:
    source = target = None
    path = None
    show_path = False
    st.sidebar.info("Add at least two concepts to find paths.")

graph_tab, search_tab, prereq_tab, stats_tab, manage_tab, io_tab = st.tabs(
    ["Graph", "Search", "Prerequisites", "Statistics", "Manage", "Import / Export"]
)

with graph_tab:
    if source is not None:
        if path:
            st.success(" -> ".join(path) + f"  ({len(path) - 1} steps)")
        else:
            st.warning(f"No path from {source} to {target}. Try ticking 'Ignore edge direction'.")

    if not visible:
        st.info("No concepts to show. Select at least one category in the sidebar.")
    else:
        path_to_draw = path if (show_path and path and all(n in visible for n in path)) else None
        if show_path and path and path_to_draw is None:
            st.info("The path is hidden because some of its concepts are in filtered-out categories.")
        st.plotly_chart(build_figure(G, path_to_draw, visible), width="stretch")
        st.caption(
            "Grey arrows: prerequisite. Light blue arrows: related. "
            "Red: highlighted shortest path. Hover over a node for details."
        )

with search_tab:
    col_text, col_cat = st.columns([3, 1])
    text = col_text.text_input("Search by name or description")
    category_choice = col_cat.selectbox("Category", ["All"] + categories)
    results = search_concepts(text, None if category_choice == "All" else category_choice)
    results["connections"] = results["name"].map(lambda n: G.degree(n))
    st.write(f"{len(results)} concept(s) found")
    st.dataframe(results, width="stretch", hide_index=True)

with prereq_tab:
    if not names:
        st.info("There are no concepts yet.")
    else:
        concept = st.selectbox(
            "Choose a concept",
            names,
            index=names.index("Graph Algorithms") if "Graph Algorithms" in names else 0,
        )
        st.write(f"**Category:** {G.nodes[concept]['category']}")
        st.write(G.nodes[concept]["description"])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("Direct prerequisites")
            direct = get_direct_prerequisites(G, concept)
            if direct:
                for name in direct:
                    st.write("-", name)
            else:
                st.write("None. This is a starting concept.")

        with col2:
            st.subheader("All prerequisites")
            st.caption("In a valid learning order")
            everything = get_all_prerequisites(G, concept)
            if everything:
                for i, name in enumerate(everything, start=1):
                    st.write(f"{i}. {name}")
            else:
                st.write("None.")

        with col3:
            st.subheader("Unlocks")
            st.caption("Direct, then all")
            direct_next = get_direct_dependents(G, concept)
            st.write("Directly:", ", ".join(direct_next) if direct_next else "nothing")
            all_next = get_all_dependents(G, concept)
            st.write("Eventually:", ", ".join(all_next) if all_next else "nothing")

with stats_tab:
    if G.number_of_nodes() == 0:
        st.info("There are no concepts yet.")
    else:
        stats = get_graph_statistics(G)

        row1 = st.columns(3)
        row1[0].metric("Concepts", stats["nodes"])
        row1[1].metric("Relationships", stats["edges"])
        row1[2].metric("Density", stats["density"])

        row2 = st.columns(3)
        row2[0].metric("Average degree", stats["average_degree"])
        row2[1].metric("Connected components", stats["connected_components"])
        row2[2].metric("Longest prerequisite chain", stats["chain_length"])

        if stats["longest_prerequisite_chain"]:
            st.write("**Longest chain:**", " -> ".join(stats["longest_prerequisite_chain"]))

        st.subheader("Degree centrality")
        centrality = get_degree_centrality(G)
        st.bar_chart(centrality.head(10).set_index("concept")["centrality"])
        st.dataframe(centrality, width="stretch")

with manage_tab:
    action = st.radio(
        "What do you want to do?",
        [
            "Add concept",
            "Edit concept",
            "Delete concept",
            "Add relationship",
            "Edit relationship",
            "Delete relationship",
        ],
        horizontal=True,
    )

    relationships_df = load_relationships_df()
    relationship_labels = {
        f"{r.source} -> {r.target} ({r.relation_type})": (r.source, r.target, r.relation_type)
        for r in relationships_df.itertuples()
    }

    if action == "Add concept":
        with st.form("add_concept_form", clear_on_submit=True):
            new_name = st.text_input("Name")
            chosen = st.selectbox("Category", categories) if categories else ""
            typed = st.text_input("Or type a new category")
            new_description = st.text_area("Description")
            if st.form_submit_button("Add concept"):
                finish(add_concept(new_name, pick_category(chosen, typed), new_description))

    elif action == "Edit concept":
        if not names:
            st.info("There are no concepts to edit.")
        else:
            old_name = st.selectbox("Concept to edit", names, key="edit_concept_pick")
            current = G.nodes[old_name]
            with st.form("edit_concept_form"):
                new_name = st.text_input("Name", value=old_name, key=f"edit_name_{old_name}")
                chosen = st.selectbox(
                    "Category",
                    categories,
                    index=categories.index(current["category"]),
                    key=f"edit_cat_{old_name}",
                )
                typed = st.text_input("Or type a new category", key=f"edit_newcat_{old_name}")
                new_description = st.text_area(
                    "Description", value=current["description"] or "", key=f"edit_desc_{old_name}"
                )
                if st.form_submit_button("Save changes"):
                    finish(update_concept(old_name, new_name, pick_category(chosen, typed), new_description))

    elif action == "Delete concept":
        if not names:
            st.info("There are no concepts to delete.")
        else:
            victim = st.selectbox("Concept to delete", names, key="delete_concept_pick")
            st.warning("Deleting a concept also deletes all of its relationships.")
            confirmed = st.checkbox("Yes, delete it", key="delete_concept_confirm")
            if st.button("Delete concept"):
                if confirmed:
                    finish(delete_concept(victim))
                else:
                    st.error("Tick the confirmation box first.")

    elif action == "Add relationship":
        if len(names) < 2:
            st.info("You need at least two concepts first.")
        else:
            with st.form("add_relationship_form", clear_on_submit=True):
                new_source = st.selectbox("From (the prerequisite)", names)
                new_target = st.selectbox("To (the concept that needs it)", names, index=1)
                new_type = st.selectbox("Type", RELATION_TYPES)
                if st.form_submit_button("Add relationship"):
                    finish(add_relationship(new_source, new_target, new_type))

    elif action == "Edit relationship":
        if not relationship_labels:
            st.info("There are no relationships to edit.")
        else:
            label = st.selectbox("Relationship", list(relationship_labels), key="edit_rel_pick")
            rel_source, rel_target, rel_type = relationship_labels[label]
            with st.form("edit_relationship_form"):
                new_type = st.selectbox(
                    "New type", RELATION_TYPES, index=RELATION_TYPES.index(rel_type), key=f"edit_rel_type_{label}"
                )
                if st.form_submit_button("Save changes"):
                    finish(update_relationship(rel_source, rel_target, new_type))

    elif action == "Delete relationship":
        if not relationship_labels:
            st.info("There are no relationships to delete.")
        else:
            label = st.selectbox("Relationship", list(relationship_labels), key="delete_rel_pick")
            rel_source, rel_target, _ = relationship_labels[label]
            if st.button("Delete relationship"):
                finish(delete_relationship(rel_source, rel_target))


def show_import_report(report):
    if report["ok"]:
        st.success(
            f"Imported {report['added_concepts']} concept(s) and {report['added_relationships']} "
            f"relationship(s). Skipped {report['skipped_concepts']} concept row(s) and "
            f"{report['skipped_relationships']} relationship row(s)."
        )
    for message in report["errors"]:
        st.error(message)
    total_notes = len(report["warnings"]) + report["more_warnings"]
    if total_notes:
        with st.expander(f"{total_notes} note(s) about skipped rows"):
            for message in report["warnings"]:
                st.write("-", message)
            if report["more_warnings"]:
                st.write(f"...and {report['more_warnings']} more.")


with io_tab:
    st.subheader("Export")
    export_cols = st.columns(2)
    export_cols[0].download_button(
        "Download concepts.csv", export_concepts_csv(), file_name="concepts.csv", mime="text/csv"
    )
    export_cols[1].download_button(
        "Download relationships.csv",
        export_relationships_csv(),
        file_name="relationships.csv",
        mime="text/csv",
    )

    st.subheader("Import")
    st.caption(
        "Concepts file: columns name and category (description is optional). "
        "Relationships file: columns source and target (relation_type is optional, "
        "either prerequisite or related). You can upload one file or both."
    )

    if "import_report" in st.session_state:
        show_import_report(st.session_state.pop("import_report"))

    mode_label = st.radio(
        "Import mode",
        ["Add to existing data", "Replace everything"],
        key="import_mode",
    )
    concepts_file = st.file_uploader("Concepts CSV", type="csv", key="import_concepts_file")
    relationships_file = st.file_uploader("Relationships CSV", type="csv", key="import_relationships_file")

    replace_mode = mode_label == "Replace everything"
    replace_confirmed = True
    if replace_mode:
        st.warning("Replace mode deletes ALL current concepts and relationships first.")
        replace_confirmed = st.checkbox("Yes, replace all existing data", key="import_replace_confirm")

    if st.button("Import"):
        if concepts_file is None and relationships_file is None:
            st.error("Choose at least one file to import.")
        elif replace_mode and not replace_confirmed:
            st.error("Tick the confirmation box first.")
        else:
            report = import_csv_files(
                concepts_file.getvalue() if concepts_file else None,
                relationships_file.getvalue() if relationships_file else None,
                "replace" if replace_mode else "merge",
            )
            if report["ok"]:
                st.session_state["import_report"] = report
                st.rerun()
            else:
                show_import_report(report)
