import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type NodeTypes,
  type NodeProps,
} from "@xyflow/react";
import { Play, Square, Cog } from "lucide-react";
import { Skeleton } from "../ui/skeleton";
import { edgeTypes } from "../edges";
import { getLayoutedElements } from "../../hooks/useAutoLayout";
import { fetchWorkflowDetail } from "../../api/workflows";

// --- Template fetch ---

async function fetchTemplate(id: string) {
  const token = localStorage.getItem("token");
  const headers: HeadersInit = token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
  const res = await fetch(`/api/v1/templates/${id}`, { headers });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  const json = await res.json();
  return json.data as {
    activities: {
      id: string;
      name: string;
      activity_type: string;
      position_x: number | null;
      position_y: number | null;
    }[];
    flows: {
      id: string;
      source_activity_id: string;
      target_activity_id: string;
      flow_type: string;
    }[];
  };
}

// --- State colors ---

const STATE_BORDER_COLORS: Record<string, string> = {
  complete: "oklch(0.55 0.2 142)",
  active: "oklch(0.55 0.19 250)",
  dormant: "oklch(0.8 0 0)",
  paused: "oklch(0.6 0.15 80)",
  error: "oklch(0.55 0.2 27)",
};

const STATE_BG_COLORS: Record<string, string> = {
  complete: "oklch(0.55 0.2 142 / 0.1)",
  active: "oklch(0.55 0.19 250 / 0.1)",
  dormant: "transparent",
  paused: "oklch(0.6 0.15 80 / 0.1)",
  error: "oklch(0.55 0.2 27 / 0.1)",
};

function getBorderColor(state: string): string {
  return STATE_BORDER_COLORS[state] ?? STATE_BORDER_COLORS.dormant;
}

function getBgColor(state: string): string {
  return STATE_BG_COLORS[state] ?? STATE_BG_COLORS.dormant;
}

// --- Progress node components (defined outside to avoid re-registration) ---

function ProgressStartNode({ data }: NodeProps) {
  const state = (data as Record<string, unknown>).activityState as string ?? "dormant";
  return (
    <div
      className="flex items-center justify-center rounded-full"
      style={{
        width: 60,
        height: 60,
        border: `3px solid ${getBorderColor(state)}`,
        backgroundColor: getBgColor(state),
      }}
    >
      <Play className="w-5 h-5 text-muted-foreground" />
    </div>
  );
}

function ProgressEndNode({ data }: NodeProps) {
  const state = (data as Record<string, unknown>).activityState as string ?? "dormant";
  return (
    <div
      className="flex items-center justify-center rounded-full"
      style={{
        width: 60,
        height: 60,
        border: `3px solid ${getBorderColor(state)}`,
        backgroundColor: getBgColor(state),
      }}
    >
      <Square className="w-4 h-4 text-muted-foreground" />
    </div>
  );
}

function ProgressManualNode({ data }: NodeProps) {
  const d = data as Record<string, unknown>;
  const state = (d.activityState as string) ?? "dormant";
  const name = (d.name as string) ?? "Activity";
  return (
    <div
      className="flex items-center justify-center rounded-lg px-3"
      style={{
        width: 160,
        height: 64,
        border: `2px solid ${getBorderColor(state)}`,
        backgroundColor: getBgColor(state),
      }}
    >
      <span className="text-xs font-medium text-foreground truncate">
        {name}
      </span>
    </div>
  );
}

function ProgressAutoNode({ data }: NodeProps) {
  const d = data as Record<string, unknown>;
  const state = (d.activityState as string) ?? "dormant";
  const name = (d.name as string) ?? "Activity";
  return (
    <div
      className="flex items-center justify-center gap-1.5 rounded-lg px-3"
      style={{
        width: 160,
        height: 64,
        border: `2px solid ${getBorderColor(state)}`,
        backgroundColor: getBgColor(state),
      }}
    >
      <Cog className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      <span className="text-xs font-medium text-foreground truncate">
        {name}
      </span>
    </div>
  );
}

const progressNodeTypes: NodeTypes = {
  startNode: ProgressStartNode,
  endNode: ProgressEndNode,
  manualNode: ProgressManualNode,
  autoNode: ProgressAutoNode,
};

// --- Main component ---

interface WorkflowProgressGraphProps {
  workflowId: string;
}

export function WorkflowProgressGraph({
  workflowId,
}: WorkflowProgressGraphProps) {
  const {
    data: workflow,
    isLoading: workflowLoading,
  } = useQuery({
    queryKey: ["workflows", workflowId],
    queryFn: () => fetchWorkflowDetail(workflowId),
    enabled: !!workflowId,
  });

  const {
    data: template,
    isLoading: templateLoading,
  } = useQuery({
    queryKey: ["templates", workflow?.process_template_id],
    queryFn: () => fetchTemplate(workflow!.process_template_id),
    enabled: !!workflow?.process_template_id,
  });

  const { layoutedNodes, layoutedEdges } = useMemo(() => {
    if (!template || !workflow) {
      return { layoutedNodes: [], layoutedEdges: [] };
    }

    const stateMap = new Map(
      (workflow.activity_instances ?? []).map((ai) => [
        ai.activity_template_id,
        ai.state,
      ]),
    );

    const nodes: Node[] = template.activities.map((act) => ({
      id: act.id,
      type:
        act.activity_type === "start"
          ? "startNode"
          : act.activity_type === "end"
            ? "endNode"
            : act.activity_type + "Node",
      position: { x: act.position_x ?? 0, y: act.position_y ?? 0 },
      data: {
        name: act.name,
        activityState: stateMap.get(act.id) ?? "dormant",
      },
    }));

    const edges: Edge[] = template.flows.map((flow) => ({
      id: flow.id,
      source: flow.source_activity_id,
      target: flow.target_activity_id,
      type: flow.flow_type === "reject" ? "rejectEdge" : "normalEdge",
    }));

    const result = getLayoutedElements(nodes, edges, "LR");
    return { layoutedNodes: result.nodes, layoutedEdges: result.edges };
  }, [template, workflow]);

  if (workflowLoading || templateLoading) {
    return <Skeleton className="h-[300px] w-full rounded-lg" />;
  }

  if (!template || !workflow) {
    return (
      <div className="flex items-center justify-center h-[300px] border rounded-lg">
        <p className="text-sm text-muted-foreground">
          Unable to load workflow progress graph.
        </p>
      </div>
    );
  }

  return (
    <div className="h-[300px] border rounded-lg bg-background">
      <ReactFlowProvider>
        <ReactFlow
          nodes={layoutedNodes}
          edges={layoutedEdges}
          nodeTypes={progressNodeTypes}
          edgeTypes={edgeTypes}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnDrag={true}
          zoomOnScroll={true}
          fitView={true}
          proOptions={{ hideAttribution: true }}
        />
      </ReactFlowProvider>
    </div>
  );
}
