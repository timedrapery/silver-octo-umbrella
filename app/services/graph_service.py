from pathlib import Path

import networkx as nx

from app.models.case import Case
from app.services.normalization import build_entity_map

# Colour palette for the dark-themed graph
_NODE_COLORS: dict[str, str] = {
    "case": "#7c6af7",
    "target": "#4ade80",
    "ip": "#38bdf8",
    "subdomain": "#34d399",
    "domain": "#a78bfa",
    "organization": "#fb923c",
    "software": "#94a3b8",
    "person": "#f472b6",
    "platform": "#fb7185",
    "finding": "#f97316",  # fallback
}


class GraphService:
    def build_graph(self, case: Case) -> nx.DiGraph:
        """
        Build a directed graph that includes:
        - A case node
        - Target nodes connected to the case
        - Entity nodes (IP, domain, subdomain, org, software, person, platform)
          extracted from findings and connected to their originating target
        """
        G = nx.DiGraph()
        G.add_node(
            f"case:{case.id}",
            label=case.name[:25],
            node_type="case",
            title=case.name,
        )

        # Index targets by id for quick lookup
        target_by_id = {t.id: t for t in case.targets}

        for target in case.targets:
            nid = f"target:{target.id}"
            G.add_node(
                nid,
                label=target.value[:30],
                node_type="target",
                title=f"{target.type.value}: {target.value}",
            )
            G.add_edge(f"case:{case.id}", nid, rel="has_target")

        # Extract deduplicated entities from all findings
        entity_map = build_entity_map(case)

        # Build a map: finding_id → target_id (for connecting entities to their target)
        finding_target: dict[str, str] = {f.id: f.target_id for f in case.findings}

        # Add entity nodes and connect them to their originating target
        for node_id, entity in entity_map.items():
            G.add_node(
                node_id,
                label=entity.value[:30],
                node_type=entity.entity_type,
                title=f"[{entity.entity_type.upper()}] {entity.value}",
            )
            # Connect to the first source target we find
            connected = False
            for fid in entity.source_finding_ids:
                tid = finding_target.get(fid)
                if tid:
                    target_node = f"target:{tid}"
                    if target_node in G.nodes:
                        G.add_edge(target_node, node_id, rel="discovered")
                        connected = True
                        break
            # If no target link found (edge case), connect to case
            if not connected:
                G.add_edge(f"case:{case.id}", node_id, rel="discovered")

        return G

    def generate_pyvis_html(self, case: Case, output_path: str) -> None:
        try:
            from pyvis.network import Network
        except ImportError:
            # Write a minimal fallback HTML so the WebView doesn't go blank
            Path(output_path).write_text(
                "<html><body style='background:#1e1e2e;color:#9ca3af;padding:32px'>"
                "<p>pyvis is not installed — run: pip install pyvis</p></body></html>",
                encoding="utf-8",
            )
            return

        G = self.build_graph(case)
        net = Network(height="600px", width="100%", bgcolor="#1e1e2e", font_color="white")
        net.directed = True

        for node_id, attrs in G.nodes(data=True):
            node_type = attrs.get("node_type", "finding")
            net.add_node(
                node_id,
                label=attrs.get("label", node_id),
                title=attrs.get("title", node_id),
                color=_NODE_COLORS.get(node_type, "#ffffff"),
            )

        for src, dst, edge_data in G.edges(data=True):
            net.add_edge(src, dst, title=edge_data.get("rel", ""))

        net.set_options("""
        {
          "physics": {
            "enabled": true,
            "stabilization": {"iterations": 150},
            "barnesHut": {"gravitationalConstant": -8000}
          }
        }
        """)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        net.save_graph(str(output))

    def get_node_data(self, case: Case) -> dict:
        G = self.build_graph(case)
        nodes = [{"id": n, **attrs} for n, attrs in G.nodes(data=True)]
        edges = [{"source": u, "target": v} for u, v in G.edges()]
        return {"nodes": nodes, "edges": edges}
