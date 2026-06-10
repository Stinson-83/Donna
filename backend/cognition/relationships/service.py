"""Relationship graph — the constellation is a real, queryable graph.

Nodes: people / projects / goals / patterns / memories / beliefs / questions.
Edges: supports / contradicts / related_to / causes / mentions / influences.

The frontend supplies positions (aesthetics); the backend supplies *what* exists
and how it connects — including which belief each memory/entity supports.
"""
from __future__ import annotations

from sqlalchemy import select

from backend.cognition.store import Belief, GraphEdge, GraphNode


async def upsert_node(session, *, user_id, label, kind, ref_id=None, weight=0.6) -> GraphNode:
    existing = (
        await session.execute(
            select(GraphNode).where(GraphNode.user_id == user_id, GraphNode.label == label)
        )
    ).scalar_one_or_none()
    if existing:
        existing.kind = kind
        if ref_id:
            existing.ref_id = ref_id
        await session.flush()
        return existing
    node = GraphNode(user_id=user_id, label=label, kind=kind, ref_id=ref_id, weight=weight)
    session.add(node)
    await session.flush()
    return node


async def add_edge(session, *, user_id, src, dst, relation, weight=0.5) -> GraphEdge:
    edge = GraphEdge(user_id=user_id, src=src, dst=dst, relation=relation, weight=weight)
    session.add(edge)
    await session.flush()
    return edge


async def build_graph(session, user_id: str) -> dict:
    nodes = (
        await session.execute(select(GraphNode).where(GraphNode.user_id == user_id))
    ).scalars().all()
    edges = (
        await session.execute(select(GraphEdge).where(GraphEdge.user_id == user_id))
    ).scalars().all()
    beliefs = {
        b.id: b
        for b in (await session.execute(select(Belief).where(Belief.user_id == user_id))).scalars().all()
    }

    by_id = {n.id: n for n in nodes}
    # attach the belief each entity supports (entity --supports--> belief node)
    supports: dict[str, dict] = {}
    for e in edges:
        if e.relation == "supports":
            dst = by_id.get(e.dst)
            if dst and dst.kind == "belief" and dst.ref_id in beliefs:
                b = beliefs[dst.ref_id]
                supports[e.src] = {"belief": b.statement, "confidence": b.confidence}

    out_nodes = [
        {
            "id": n.id,
            "label": n.label,
            "kind": n.kind,
            "weight": n.weight,
            "supports": supports.get(n.id),
        }
        for n in nodes
        if n.kind != "belief"  # belief nodes are internal anchors
    ]
    keep = {n["id"] for n in out_nodes}
    out_edges = [
        {"src": e.src, "dst": e.dst, "relation": e.relation, "weight": e.weight}
        for e in edges
        if e.src in keep and e.dst in keep
    ]
    return {"nodes": out_nodes, "edges": out_edges}
