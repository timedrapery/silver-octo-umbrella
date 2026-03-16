from pathlib import Path

import networkx as nx

from app.models.case import Case


class GraphService:
    def build_graph(self, case: Case) -> nx.Graph:
        G = nx.Graph()
        G.add_node(f"case:{case.id}", label=case.name, node_type="case", title=case.name)

        for target in case.targets:
            node_id = f"target:{target.id}"
            G.add_node(node_id, label=target.value, node_type="target", title=f"{target.type.value}: {target.value}")
            G.add_edge(f"case:{case.id}", node_id)

        for finding in case.findings:
            node_id = f"finding:{finding.id}"
            G.add_node(
                node_id,
                label=finding.title[:30],
                node_type="finding",
                title=f"[{finding.severity.value}] {finding.title}",
            )
            G.add_edge(f"target:{finding.target_id}", node_id)

        return G

    def generate_pyvis_html(self, case: Case, output_path: str):
        from pyvis.network import Network

        G = self.build_graph(case)
        net = Network(height="600px", width="100%", bgcolor="#1e1e2e", font_color="white")

        color_map = {
            "case": "#7c6af7",
            "target": "#4ade80",
            "finding": "#f97316",
        }

        for node_id, attrs in G.nodes(data=True):
            node_type = attrs.get("node_type", "finding")
            net.add_node(
                node_id,
                label=attrs.get("label", node_id),
                title=attrs.get("title", node_id),
                color=color_map.get(node_type, "#ffffff"),
            )

        for src, dst in G.edges():
            net.add_edge(src, dst)

        net.set_options("""
        {
          "physics": {
            "enabled": true,
            "stabilization": {"iterations": 100}
          }
        }
        """)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        net.save_graph(str(output))

    def get_node_data(self, case: Case) -> dict:
        G = self.build_graph(case)
        nodes = [
            {"id": n, **attrs}
            for n, attrs in G.nodes(data=True)
        ]
        edges = [{"source": u, "target": v} for u, v in G.edges()]
        return {"nodes": nodes, "edges": edges}
