import * as dagre from '@dagrejs/dagre';
import type { Node, Edge } from '@xyflow/react';
const NODE_DIMENSIONS: Record<string, { width: number; height: number }> = {
  start: { width: 60, height: 60 },
  end: { width: 60, height: 60 },
  startNode: { width: 60, height: 60 },
  endNode: { width: 60, height: 60 },
  manual: { width: 172, height: 64 },
  auto: { width: 172, height: 64 },
  manualNode: { width: 172, height: 64 },
  autoNode: { width: 172, height: 64 },
};

const DEFAULT_DIMENSIONS = { width: 172, height: 64 };

export function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'LR' | 'TB' = 'LR',
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));

  g.setGraph({
    rankdir: direction,
    nodesep: 50,
    ranksep: 80,
  });

  for (const node of nodes) {
    const dims =
      NODE_DIMENSIONS[node.type ?? ''] ?? DEFAULT_DIMENSIONS;
    g.setNode(node.id, { width: dims.width, height: dims.height });
  }

  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = g.node(node.id);
    const dims =
      NODE_DIMENSIONS[node.type ?? ''] ?? DEFAULT_DIMENSIONS;

    return {
      ...node,
      position: {
        x: nodeWithPosition.x - dims.width / 2,
        y: nodeWithPosition.y - dims.height / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}
