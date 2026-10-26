import networkx as nx

from load_data import load_sample_data


def build_graph(concepts, relationships):
    G = nx.DiGraph()
    for _, row in concepts.iterrows():
        G.add_node(row["name"], category=row["category"], description=row["description"])
    for _, row in relationships.iterrows():
        G.add_edge(row["source"], row["target"], relation_type=row["relation_type"])
    return G


def load_graph():
    concepts, relationships = load_sample_data()
    return build_graph(concepts, relationships)


def get_direct_prerequisites(G, concept):
    return [u for u, v, d in G.in_edges(concept, data=True) if d["relation_type"] == "prerequisite"]


def get_direct_dependents(G, concept):
    return [v for u, v, d in G.out_edges(concept, data=True) if d["relation_type"] == "prerequisite"]


def prerequisite_graph(G):
    edges = [(u, v) for u, v, d in G.edges(data=True) if d["relation_type"] == "prerequisite"]
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes(data=True))
    H.add_edges_from(edges)
    return H


def main():
    G = load_graph()
    print(f"Nodes (concepts)      : {G.number_of_nodes()}")
    print(f"Edges (relationships) : {G.number_of_edges()}")

    H = prerequisite_graph(G)
    print(f"Prerequisite edges    : {H.number_of_edges()}")
    print(f"Prerequisites acyclic : {nx.is_directed_acyclic_graph(H)}")

    concept = "Sorting"
    print(f"\nDetails of '{concept}':")
    print("  category    :", G.nodes[concept]["category"])
    print("  description :", G.nodes[concept]["description"])

    print("\nDirect prerequisites of 'Graph Algorithms':")
    print(" ", get_direct_prerequisites(G, "Graph Algorithms"))

    print("\nConcepts that directly depend on 'Arrays':")
    print(" ", get_direct_dependents(G, "Arrays"))


if __name__ == "__main__":
    main()
