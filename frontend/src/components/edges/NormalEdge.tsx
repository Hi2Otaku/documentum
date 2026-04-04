import {
  BaseEdge,
  EdgeLabelRenderer,
  getStraightPath,
  type EdgeProps,
  type Edge,
} from '@xyflow/react';
import type { FlowEdgeData } from '../../types/workflow';

type NormalEdgeType = Edge<FlowEdgeData, 'normal'>;

export function NormalEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  selected,
  data,
}: EdgeProps<NormalEdgeType>) {
  const [edgePath, labelX, labelY] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: selected ? '#eab308' : '#3b82f6',
          strokeWidth: selected ? 2.5 : 2,
        }}
        markerEnd="url(#arrow-normal)"
      />
      {data?.displayLabel && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="bg-white text-xs px-1 py-0.5 rounded border border-gray-300 text-gray-600"
          >
            {data.displayLabel}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
