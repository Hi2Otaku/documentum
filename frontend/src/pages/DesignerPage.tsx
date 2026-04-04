import { useEffect } from 'react';
import { useParams, Link } from 'react-router';
import { ReactFlowProvider } from '@xyflow/react';
import { useQuery } from '@tanstack/react-query';
import type { Node, Edge } from '@xyflow/react';

import { Canvas } from '../components/designer/Canvas';
import { NodePalette } from '../components/designer/NodePalette';
import { PropertiesPanel } from '../components/designer/PropertiesPanel';
import { ErrorPanel } from '../components/designer/ErrorPanel';
import { Toolbar } from '../components/designer/Toolbar';
import { useDesignerStore } from '../stores/designerStore';
import { getTemplateDetail } from '../api/templates';
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

  const {
    data: template,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['templates', id, 'detail'],
    queryFn: () => getTemplateDetail(id!),
    enabled: !!id,
  });

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
        onSave={() => {}}
        onValidateInstall={() => {}}
        saving={false}
        validating={false}
      />
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />
        <div className="flex-1 relative">
          <Canvas />
        </div>
        <PropertiesPanel />
      </div>
      <ErrorPanel errors={[]} onErrorClick={() => {}} />
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
