import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
  type Edge,
} from '@xyflow/react';
import type { FlowEdgeData } from '../../types/designer';

type RejectEdgeType = Edge<FlowEdgeData, 'rejectEdge'>;

export function RejectEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps<RejectEdgeType>) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const label = data?.displayLabel || 'Reject';

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: '#ef4444',
          strokeWidth: 2,
          strokeDasharray: '8 4',
        }}
        markerEnd="url(#react-flow__arrowclosed)"
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="bg-white px-2 py-0.5 rounded text-sm text-red-500 border border-red-200"
        >
          {label}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
