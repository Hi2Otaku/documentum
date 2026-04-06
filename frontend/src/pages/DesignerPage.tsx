import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router';
import { ReactFlowProvider, useReactFlow } from '@xyflow/react';
import { useQuery } from '@tanstack/react-query';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Canvas } from '../components/designer/Canvas';
import { NodePalette } from '../components/designer/NodePalette';
import { PropertiesPanel } from '../components/designer/PropertiesPanel';
import { ErrorPanel } from '../components/designer/ErrorPanel';
import { Toolbar } from '../components/designer/Toolbar';
import { ContextMenu } from '../components/designer/ContextMenu';
import { useDesignerStore } from '../stores/designerStore';
import { getTemplateDetail, updateTemplate } from '../api/templates';
import { useSaveTemplate } from '../hooks/useSaveTemplate';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { getLayoutedElements } from '../hooks/useAutoLayout';
import type { ProcessTemplateDetail } from '../types/workflow';
import type { ActivityNodeData, FlowEdgeData } from '../types/designer';

/** Convert backend activities to React Flow nodes */
function activitiesToNodes(
  template: ProcessTemplateDetail,
): Node<ActivityNodeData>[] {
  return template.activities.map((a) => ({
    id: a.id,
    type:
      a.activity_type === 'start'
        ? 'startNode'
        : a.activity_type === 'end'
          ? 'endNode'
          : a.activity_type === 'manual'
            ? 'manualNode'
            : 'autoNode',
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
      expectedDurationHours: a.expected_duration_hours,
      escalationAction: a.escalation_action,
      warningThresholdHours: a.warning_threshold_hours,
      backendId: a.id,
    },
  }));
}

/** Convert backend flows to React Flow edges */
function flowsToEdges(
  template: ProcessTemplateDetail,
): Edge<FlowEdgeData>[] {
  return template.flows.map((f) => ({
    id: f.id,
    source: f.source_activity_id,
    target: f.target_activity_id,
    type: f.flow_type === 'reject' ? 'rejectEdge' : 'normalEdge',
    data: {
      flowType: f.flow_type,
      conditionExpression: f.condition_expression,
      displayLabel: f.display_label,
      backendId: f.id,
    },
  }));
}

function DesignerInner() {
  const { id } = useParams<{ id: string }>();
  const isDirty = useDesignerStore((s) => s.isDirty);
  const { setCenter } = useReactFlow();

  const {
    data: template,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['templates', id, 'detail'],
    queryFn: () => getTemplateDetail(id!),
    enabled: !!id,
  });

  // Save template hook -- pass initialData for correct snapshot initialization
  const {
    save,
    validateAndInstall,
    saving,
    validating,
    validationErrors,
    variables,
    setVariables,
  } = useSaveTemplate(id!, template);

  // Keyboard shortcuts
  useKeyboardShortcuts({ onSave: save });

  // Context menu state
  const [contextMenuPos, setContextMenuPos] = useState<{ x: number; y: number } | null>(null);
  const [contextMenuTarget, setContextMenuTarget] = useState<{
    type: 'node' | 'edge' | 'pane';
    id?: string;
  } | null>(null);

  const handleCloseContextMenu = useCallback(() => {
    setContextMenuPos(null);
    setContextMenuTarget(null);
  }, []);

  const handleNodeContextMenu = useCallback(
    (event: React.MouseEvent | MouseEvent, node: Node) => {
      event.preventDefault();
      setContextMenuPos({ x: (event as MouseEvent).clientX, y: (event as MouseEvent).clientY });
      setContextMenuTarget({ type: 'node', id: node.id });
    },
    [],
  );

  const handleEdgeContextMenu = useCallback(
    (event: React.MouseEvent | MouseEvent, edge: Edge) => {
      event.preventDefault();
      setContextMenuPos({ x: (event as MouseEvent).clientX, y: (event as MouseEvent).clientY });
      setContextMenuTarget({ type: 'edge', id: edge.id });
    },
    [],
  );

  const handlePaneContextMenu = useCallback(
    (event: React.MouseEvent | MouseEvent) => {
      event.preventDefault();
      setContextMenuPos({ x: (event as MouseEvent).clientX, y: (event as MouseEvent).clientY });
      setContextMenuTarget({ type: 'pane' });
    },
    [],
  );

  const handleErrorClick = useCallback(
    (entityId: string) => {
      const nodes = useDesignerStore.getState().nodes;
      const node = nodes.find(
        (n) =>
          n.id === entityId ||
          (n.data as ActivityNodeData).backendId === entityId,
      );
      if (node) {
        setCenter(node.position.x, node.position.y, { zoom: 1.5, duration: 300 });
        useDesignerStore.getState().setSelectedNode(node.id);
      }
    },
    [setCenter],
  );

  // Load template data into store on mount
  useEffect(() => {
    if (!template || !id) return;

    let nodes = activitiesToNodes(template);
    let edges = flowsToEdges(template);

    // If no position data exists, run auto-layout
    const allZero = nodes.every(
      (n) =>
        (n.position.x === 0 || n.position.x == null) &&
        (n.position.y === 0 || n.position.y == null),
    );
    if (allZero && nodes.length > 0) {
      const layouted = getLayoutedElements(nodes, edges);
      nodes = layouted.nodes as typeof nodes;
      edges = layouted.edges as typeof edges;
    }

    useDesignerStore.getState().loadTemplate(id, nodes, edges);
  }, [template, id]);

  // Warn on unsaved changes before navigating away
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  // Cleanup store on unmount
  useEffect(() => {
    return () => {
      useDesignerStore.getState().reset();
    };
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-muted-foreground">Loading template...</span>
        </div>
      </div>
    );
  }

  if (isError || !template) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <p className="text-destructive text-lg">Could not load template</p>
          <Link to="/templates" className="text-primary underline">
            Back to Templates
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      <Toolbar
        templateName={template.name}
        onSave={save}
        onValidateInstall={validateAndInstall}
        saving={saving}
        validating={validating}
      />
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />
        <div className="flex-1 relative">
          <Canvas
            onNodeContextMenu={handleNodeContextMenu}
            onEdgeContextMenu={handleEdgeContextMenu}
            onPaneContextMenu={handlePaneContextMenu}
          />
        </div>
        <PropertiesPanel
          variables={variables}
          onVariablesChange={setVariables}
          templateName={template.name}
          templateDescription={template.description ?? ''}
          onTemplateMetaChange={(name, description) => {
            updateTemplate(id!, { name, description });
          }}
        />
      </div>
      <ErrorPanel errors={validationErrors} onErrorClick={handleErrorClick} />
      <ContextMenu
        position={contextMenuPos}
        target={contextMenuTarget}
        onClose={handleCloseContextMenu}
      />
    </div>
  );
}

export function DesignerPage() {
  return (
    <ReactFlowProvider>
      <DesignerInner />
    </ReactFlowProvider>
  );
}
