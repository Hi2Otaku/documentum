import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
  type Edge,
} from '@xyflow/react';
import type { FlowEdgeData } from '../../types/designer';

type ConditionalEdgeType = Edge<FlowEdgeData, 'conditionalEdge'>;

export function ConditionalEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps<ConditionalEdgeType>) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const conditionText = data?.conditionExpression
    ? data.conditionExpression.length > 20
      ? `${data.conditionExpression.substring(0, 20)}...`
      : data.conditionExpression
    : undefined;

  const label = data?.displayLabel || conditionText;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: '#3b82f6',
          strokeWidth: 2,
          strokeDasharray: '2 4',
        }}
        markerEnd="url(#react-flow__arrowclosed)"
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="bg-white px-2 py-0.5 rounded text-sm text-blue-500 border border-blue-200"
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
