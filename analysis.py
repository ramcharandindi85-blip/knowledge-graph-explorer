import networkx as nx
import pandas as pd

from database import init_db, load_graph_from_db, seed_database
from graph_engine import prerequisite_graph


def find_shortest_path(G, source, target, directed=True):
    graph = G if directed else G.to_undirected()
    try:
        return nx.shortest_path(graph, source, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def get_all_prerequisites(G, concept):
    H = prerequisite_graph(G)
    if concept not in H:
        return []
    needed = nx.ancestors(H, concept)
    return [n for n in nx.topological_sort(H) if n in needed]


def get_all_dependents(G, concept):
    H = prerequisite_graph(G)
    if concept not in H:
        return []
    unlocked = nx.descendants(H, concept)
    return [n for n in nx.topological_sort(H) if n in unlocked]


def get_degree_centrality(G):
    centrality = nx.degree_centrality(G)
    rows = []
    for name, value in centrality.items():
        rows.append(
            {
                "concept": name,
                "category": G.nodes[name]["category"],
                "degree": G.degree(name),
                "centrality": round(value, 3),
            }
        )
    df = pd.DataFrame(rows)
    df = df.sort_values(["centrality", "concept"], ascending=[False, True])
    return df.reset_index(drop=True)


def get_graph_statistics(G):
    H = prerequisite_graph(G)
    acyclic = nx.is_directed_acyclic_graph(H)
    longest = nx.dag_longest_path(H) if acyclic else []
    node_count = G.number_of_nodes()
    return {
        "nodes": node_count,
        "edges": G.number_of_edges(),
        "density": round(nx.density(G), 4),
        "average_degree": round(sum(d for _, d in G.degree()) / node_count, 2),
        "connected_components": nx.number_weakly_connected_components(G),
        "prerequisites_acyclic": acyclic,
        "longest_prerequisite_chain": longest,
        "chain_length": max(len(longest) - 1, 0),
    }


def main():
    init_db()
    seed_database()
    G = load_graph_from_db()

    print("SHORTEST PATHS")
    for source, target in [
        ("Programming Basics", "Graph Algorithms"),
        ("Programming Basics", "HTTP"),
        ("Programming Basics", "Machine Learning"),
    ]:
        path = find_shortest_path(G, source, target)
        if path:
            print(f"  {source} -> {target}: {' -> '.join(path)} ({len(path) - 1} steps)")
        else:
            print(f"  {source} -> {target}: no directed path")

    path = find_shortest_path(G, "Programming Basics", "Machine Learning", directed=False)
    print("  Ignoring direction:", " -> ".join(path))

    print("\nALL PREREQUISITES OF 'Graph Algorithms' (learning order)")
    print(" ", get_all_prerequisites(G, "Graph Algorithms"))

    print("\nCONCEPTS UNLOCKED BY 'Recursion'")
    print(" ", get_all_dependents(G, "Recursion"))

    print("\nTOP 5 CONCEPTS BY DEGREE CENTRALITY")
    print(get_degree_centrality(G).head(5).to_string())

    print("\nGRAPH STATISTICS")
    for key, value in get_graph_statistics(G).items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
