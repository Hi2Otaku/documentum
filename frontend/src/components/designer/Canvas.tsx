import { useCallback } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  useReactFlow,
  type Connection,
  type Node,
} from '@xyflow/react';
import { nodeTypes } from '../nodes';
import { edgeTypes } from '../edges';
import { useDesignerStore } from '../../stores/designerStore';
import type { ActivityNodeData } from '../../types/designer';

const DEFAULT_NODE_DATA: Record<string, { name: string; activityType: string }> = {
  startNode: { name: 'Start', activityType: 'start' },
  endNode: { name: 'End', activityType: 'end' },
  manualNode: { name: 'New Manual Activity', activityType: 'manual' },
  autoNode: { name: 'New Auto Activity', activityType: 'auto' },
};

export function Canvas() {
  const { screenToFlowPosition } = useReactFlow();

  const nodes = useDesignerStore((s) => s.nodes);
  const edges = useDesignerStore((s) => s.edges);
  const onNodesChange = useDesignerStore((s) => s.onNodesChange);
  const onEdgesChange = useDesignerStore((s) => s.onEdgesChange);
  const addEdge = useDesignerStore((s) => s.addEdge);
  const addNode = useDesignerStore((s) => s.addNode);
  const setSelectedNode = useDesignerStore((s) => s.setSelectedNode);
  const setSelectedEdge = useDesignerStore((s) => s.setSelectedEdge);
  const clearSelection = useDesignerStore((s) => s.clearSelection);

  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdge = {
        id: crypto.randomUUID(),
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        type: 'normalEdge',
        data: { flowType: 'normal' as const },
      };
      addEdge(newEdge);
    },
    [addEdge],
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node.id);
    },
    [setSelectedNode],
  );

  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: { id: string }) => {
      setSelectedEdge(edge.id);
    },
    [setSelectedEdge],
  );

  const onPaneClick = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData('application/reactflow');
      if (!nodeType) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const defaults = DEFAULT_NODE_DATA[nodeType] ?? {
        name: 'New Activity',
        activityType: 'manual',
      };

      const newNode: Node<ActivityNodeData> = {
        id: crypto.randomUUID(),
        type: nodeType,
        position,
        data: {
          name: defaults.name,
          activityType: defaults.activityType as ActivityNodeData['activityType'],
        },
      };

      addNode(newNode);
      setSelectedNode(newNode.id);
    },
    [screenToFlowPosition, addNode, setSelectedNode],
  );

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        snapToGrid={true}
        snapGrid={[20, 20]}
        fitView
        connectionLineStyle={{ strokeDasharray: '5 5' }}
        defaultEdgeOptions={{ type: 'normalEdge' }}
        multiSelectionKeyCode="Shift"
        selectionOnDrag={true}
        deleteKeyCode="Delete"
      >
        <Background variant={BackgroundVariant.Dots} />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            switch (n.type) {
              case 'start':
              case 'startNode':
                return '#22c55e';
              case 'end':
              case 'endNode':
                return '#ef4444';
              case 'manual':
              case 'manualNode':
                return '#3b82f6';
              case 'auto':
              case 'autoNode':
                return '#a855f7';
              default:
                return '#94a3b8';
            }
          }}
        />
      </ReactFlow>
    </div>
  );
}
