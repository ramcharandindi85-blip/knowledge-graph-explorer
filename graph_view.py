import networkx as nx
import plotly.graph_objects as go

PALETTE = [
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#B279A2",
    "#E45756",
    "#72B7B2",
    "#9D755D",
    "#BAB0AC",
]

PREREQUISITE_COLOR = "#8A8F98"
RELATED_COLOR = "#7FB7E6"
PATH_COLOR = "#E02424"


def category_colors(G):
    categories = sorted({data["category"] for _, data in G.nodes(data=True)})
    return {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(categories)}


def add_edge_arrow(fig, pos, u, v, color, width):
    fig.add_annotation(
        x=pos[v][0],
        y=pos[v][1],
        ax=pos[u][0],
        ay=pos[u][1],
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowhead=3,
        arrowsize=1.2,
        arrowwidth=width,
        arrowcolor=color,
        standoff=12,
        startstandoff=12,
    )


def build_figure(G, path=None, visible=None):
    path = path or []
    path_nodes = set(path)
    path_edges = set(zip(path, path[1:]))
    visible = set(G.nodes()) if visible is None else set(visible)
    pos = nx.spring_layout(G, seed=42, k=1.2)
    colors = category_colors(G)

    fig = go.Figure()

    for u, v, data in G.edges(data=True):
        if u not in visible or v not in visible:
            continue
        if (u, v) in path_edges or (v, u) in path_edges:
            continue
        color = PREREQUISITE_COLOR if data["relation_type"] == "prerequisite" else RELATED_COLOR
        add_edge_arrow(fig, pos, u, v, color, 1.2)

    for u, v, data in G.edges(data=True):
        if u not in visible or v not in visible:
            continue
        if (u, v) in path_edges or (v, u) in path_edges:
            add_edge_arrow(fig, pos, u, v, PATH_COLOR, 3)

    for category, color in colors.items():
        names = [n for n, d in G.nodes(data=True) if d["category"] == category and n in visible]
        if not names:
            continue
        hover = [
            f"<b>{n}</b><br>Category: {category}<br>{G.nodes[n]['description']}"
            f"<br>Connections: {G.degree(n)}"
            for n in names
        ]
        fig.add_trace(
            go.Scatter(
                x=[pos[n][0] for n in names],
                y=[pos[n][1] for n in names],
                mode="markers+text",
                name=category,
                text=names,
                textposition="top center",
                textfont=dict(size=10),
                hovertext=hover,
                hoverinfo="text",
                marker=dict(
                    size=[24 if n in path_nodes else 18 for n in names],
                    color=color,
                    line=dict(
                        width=[4 if n in path_nodes else 1 for n in names],
                        color=[PATH_COLOR if n in path_nodes else "white" for n in names],
                    ),
                ),
            )
        )

    fig.update_layout(
        height=750,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        legend=dict(title="Category"),
    )
    return fig
