import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Node,
  type Edge,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react';
import { useQuery } from '@tanstack/react-query';

import { nodeTypes } from '../components/nodes';
import { edgeTypes } from '../components/edges';
import { useDesignerStore } from '../store/designerStore';
import {
  getTemplateDetail,
  addActivity,
  updateActivity,
  deleteActivity,
  addFlow,
  deleteFlow,
  validateTemplate,
  installTemplate,
} from '../api/templates';
import type { ActivityNodeData, FlowEdgeData } from '../types/designer';
import type {
  ActivityType,
  ProcessTemplateDetail,
  ValidationResult,
} from '../types/workflow';

/** Convert backend template to React Flow nodes/edges */
function templateToFlow(template: ProcessTemplateDetail): {
  nodes: Node<ActivityNodeData>[];
  edges: Edge<FlowEdgeData>[];
} {
  const nodes: Node<ActivityNodeData>[] = template.activities.map((a) => ({
    id: a.id,
    type: a.activity_type,
    position: { x: a.position_x ?? 0, y: a.position_y ?? 0 },
    data: {
      name: a.name,
      activityType: a.activity_type,
      description: a.description ?? undefined,
      performerType: a.performer_type,
      performerId: a.performer_id,
      triggerType: a.trigger_type,
      methodName: a.method_name,
      routingType: a.routing_type,
      performerList: a.performer_list,
      backendId: a.id,
    },
  }));

  const edges: Edge<FlowEdgeData>[] = template.flows.map((f) => ({
    id: f.id,
    source: f.source_activity_id,
    target: f.target_activity_id,
    type: f.flow_type,
    data: {
      flowType: f.flow_type,
      conditionExpression: f.condition_expression,
      displayLabel: f.display_label,
      backendId: f.id,
    },
  }));

  return { nodes, edges };
}

/** Palette item config */
const PALETTE_ITEMS: { type: ActivityType; label: string; color: string }[] = [
  { type: 'start', label: 'Start', color: 'bg-green-500' },
  { type: 'end', label: 'End', color: 'bg-red-500' },
  { type: 'manual', label: 'Manual', color: 'bg-blue-500' },
  { type: 'auto', label: 'Auto', color: 'bg-purple-500' },
];

function DesignerCanvas() {
  const { id: templateId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node<ActivityNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge<FlowEdgeData>>([]);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationResult | null>(null);

  const selectNode = useDesignerStore((s) => s.selectNode);
  const markDirty = useDesignerStore((s) => s.markDirty);

  // Load template data
  const { data: template } = useQuery({
    queryKey: ['template', templateId],
    queryFn: () => getTemplateDetail(templateId!),
    enabled: !!templateId,
  });

  useEffect(() => {
    if (template) {
      const { nodes: n, edges: e } = templateToFlow(template);
      setNodes(n);
      setEdges(e);
    }
  }, [template, setNodes, setEdges]);

  // Handle new edge connections
  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdge: Edge<FlowEdgeData> = {
        ...connection,
        id: `e-${Date.now()}`,
        type: 'normal',
        data: { flowType: 'normal' },
      } as Edge<FlowEdgeData>;
      setEdges((eds) => addEdge(newEdge, eds));
      markDirty();
    },
    [setEdges, markDirty],
  );

  // Handle drop from palette
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const activityType = event.dataTransfer.getData(
        'application/workflow-node',
      ) as ActivityType;
      if (!activityType) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node<ActivityNodeData> = {
        id: `new-${Date.now()}`,
        type: activityType,
        position,
        data: {
          name: `${activityType.charAt(0).toUpperCase() + activityType.slice(1)} Activity`,
          activityType,
        },
      };

      setNodes((nds) => [...nds, newNode]);
      markDirty();
    },
    [screenToFlowPosition, setNodes, markDirty],
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode],
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // ---- Save to backend ----
  const handleSave = useCallback(async () => {
    if (!templateId) return;
    setStatusMsg('Saving...');
    try {
      // Get current backend state
      const current = await getTemplateDetail(templateId);
      const existingActivityIds = new Set(current.activities.map((a) => a.id));
      const existingFlowIds = new Set(current.flows.map((f) => f.id));

      // Map: node.id -> backendId for new nodes
      const nodeIdToBackendId = new Map<string, string>();

      // Save activities
      for (const node of nodes) {
        const backendId = node.data.backendId;
        if (backendId && existingActivityIds.has(backendId)) {
          // Update existing
          await updateActivity(templateId, backendId, {
            name: node.data.name,
            description: node.data.description,
            performer_type: node.data.performerType,
            performer_id: node.data.performerId,
            trigger_type: node.data.triggerType,
            method_name: node.data.methodName,
            position_x: node.position.x,
            position_y: node.position.y,
            routing_type: node.data.routingType,
            performer_list: node.data.performerList,
          });
          nodeIdToBackendId.set(node.id, backendId);
          existingActivityIds.delete(backendId);
        } else {
          // Create new
          const created = await addActivity(templateId, {
            name: node.data.name,
            activity_type: node.data.activityType,
            description: node.data.description,
            performer_type: node.data.performerType,
            performer_id: node.data.performerId,
            trigger_type: node.data.triggerType ?? 'or_join',
            method_name: node.data.methodName,
            position_x: node.position.x,
            position_y: node.position.y,
            routing_type: node.data.routingType,
            performer_list: node.data.performerList,
          });
          nodeIdToBackendId.set(node.id, created.id);
        }
      }

      // Delete removed activities
      for (const removedId of existingActivityIds) {
        await deleteActivity(templateId, removedId);
      }

      // Delete all existing flows and recreate
      for (const flowId of existingFlowIds) {
        await deleteFlow(templateId, flowId);
      }

      // Create flows
      for (const edge of edges) {
        const sourceBackendId =
          nodeIdToBackendId.get(edge.source) ?? edge.source;
        const targetBackendId =
          nodeIdToBackendId.get(edge.target) ?? edge.target;
        await addFlow(templateId, {
          source_activity_id: sourceBackendId,
          target_activity_id: targetBackendId,
          flow_type: edge.data?.flowType ?? 'normal',
          condition_expression: edge.data?.conditionExpression,
          display_label: edge.data?.displayLabel,
        });
      }

      // Reload from backend
      const updated = await getTemplateDetail(templateId);
      const { nodes: n, edges: e } = templateToFlow(updated);
      setNodes(n);
      setEdges(e);
      useDesignerStore.getState().markClean();
      setStatusMsg('Saved successfully');
      setTimeout(() => setStatusMsg(null), 2000);
    } catch (err) {
      setStatusMsg(`Save failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, [templateId, nodes, edges, setNodes, setEdges]);

  // ---- Validate ----
  const handleValidate = useCallback(async () => {
    if (!templateId) return;
    setStatusMsg('Validating...');
    try {
      const result = await validateTemplate(templateId);
      setValidationErrors(result);
      setStatusMsg(result.valid ? 'Template is valid' : `${result.errors.length} validation error(s)`);
      if (result.valid) {
        setTimeout(() => setStatusMsg(null), 2000);
      }
    } catch (err) {
      setStatusMsg(`Validation failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, [templateId]);

  // ---- Install ----
  const handleInstall = useCallback(async () => {
    if (!templateId) return;
    setStatusMsg('Installing...');
    try {
      await installTemplate(templateId);
      setStatusMsg('Template installed successfully');
      setTimeout(() => setStatusMsg(null), 2000);
    } catch (err) {
      setStatusMsg(`Install failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, [templateId]);

  return (
    <div className="flex h-screen flex-col">
      {/* Toolbar */}
      <header className="flex items-center justify-between bg-white border-b border-gray-200 px-4 py-2">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/templates')}
            className="text-gray-500 hover:text-gray-700 text-sm"
          >
            &larr; Templates
          </button>
          <h1 className="text-lg font-semibold text-gray-800">
            {template?.name ?? 'Loading...'}
          </h1>
          {template && (
            <span className="text-xs text-gray-400">v{template.version}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {statusMsg && (
            <span className="text-sm text-gray-500 mr-2">{statusMsg}</span>
          )}
          <button
            onClick={handleSave}
            className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-blue-700"
          >
            Save
          </button>
          <button
            onClick={handleValidate}
            className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded text-sm font-medium hover:bg-gray-200 border"
          >
            Validate
          </button>
          <button
            onClick={handleInstall}
            className="bg-green-600 text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-green-700"
          >
            Install
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Palette sidebar */}
        <aside className="w-48 bg-gray-50 border-r border-gray-200 p-3 flex flex-col gap-2">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
            Activities
          </h2>
          {PALETTE_ITEMS.map((item) => (
            <div
              key={item.type}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData('application/workflow-node', item.type);
                e.dataTransfer.effectAllowed = 'move';
              }}
              className={`flex items-center gap-2 px-3 py-2 rounded cursor-grab active:cursor-grabbing text-white text-sm font-medium ${item.color} hover:opacity-90 shadow-sm`}
            >
              {item.label}
            </div>
          ))}

          {/* Validation errors */}
          {validationErrors && !validationErrors.valid && (
            <div className="mt-4">
              <h3 className="text-xs font-semibold text-red-600 uppercase tracking-wider mb-1">
                Errors
              </h3>
              <ul className="text-xs text-red-600 space-y-1">
                {validationErrors.errors.map((e, i) => (
                  <li key={i} className="bg-red-50 rounded p-1.5">
                    {e.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        {/* Canvas */}
        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            deleteKeyCode="Delete"
          >
            <Background />
            <Controls />
            <MiniMap
              nodeColor={(n) => {
                switch (n.type) {
                  case 'start':
                    return '#22c55e';
                  case 'end':
                    return '#ef4444';
                  case 'manual':
                    return '#3b82f6';
                  case 'auto':
                    return '#a855f7';
                  default:
                    return '#94a3b8';
                }
              }}
            />
            {/* SVG marker defs for edge arrows */}
            <svg>
              <defs>
                <marker
                  id="arrow-normal"
                  viewBox="0 0 10 10"
                  refX="10"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#3b82f6" />
                </marker>
                <marker
                  id="arrow-reject"
                  viewBox="0 0 10 10"
                  refX="10"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444" />
                </marker>
              </defs>
            </svg>
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}

export function DesignerPage() {
  return (
    <ReactFlowProvider>
      <DesignerCanvas />
    </ReactFlowProvider>
  );
}
