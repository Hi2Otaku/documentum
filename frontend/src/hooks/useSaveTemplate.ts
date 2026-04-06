import { useState, useEffect, useCallback, useRef } from 'react';
import type { Node, Edge } from '@xyflow/react';
import { toast } from 'sonner';

import {
  addActivity as createActivity,
  updateActivity,
  deleteActivity,
  addFlow as createFlow,
  updateFlow,
  deleteFlow,
  createVariable,
  updateVariable,
  deleteVariable,
  validateTemplate,
  installTemplate,
} from '../api/templates';
import { useDesignerStore } from '../stores/designerStore';
import { useUiStore } from '../stores/uiStore';
import type { ProcessTemplateDetail, ProcessVariable, ValidationErrorDetail } from '../types/workflow';
import type { ActivityNodeData, FlowEdgeData } from '../types/designer';

interface SavedSnapshot {
  nodes: Node[];
  edges: Edge[];
}

export function useSaveTemplate(templateId: string, initialData?: ProcessTemplateDetail) {
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrorDetail[]>([]);
  const [variables, setVariables] = useState<ProcessVariable[]>([]);

  const lastSavedSnapshot = useRef<SavedSnapshot | null>(null);
  const lastSavedVariables = useRef<ProcessVariable[]>([]);

  // Initialize from loaded data
  useEffect(() => {
    if (!initialData) return;

    // Initialize variables from loaded template
    setVariables(initialData.variables ?? []);
    lastSavedVariables.current = structuredClone(initialData.variables ?? []);

    // Initialize snapshot from current store state (already loaded by DesignerPage)
    const storeState = useDesignerStore.getState();
    lastSavedSnapshot.current = {
      nodes: structuredClone(storeState.nodes),
      edges: structuredClone(storeState.edges),
    };
  }, [initialData]);

  const save = useCallback(async () => {
    setSaving(true);
    try {
      const { nodes: currentNodes, edges: currentEdges } = useDesignerStore.getState();
      const savedNodes = lastSavedSnapshot.current?.nodes ?? [];
      const savedEdges = lastSavedSnapshot.current?.edges ?? [];

      // Build lookup maps for saved state
      const savedNodeMap = new Map<string, Node>();
      for (const n of savedNodes) {
        const bid = (n.data as ActivityNodeData)?.backendId;
        if (bid) savedNodeMap.set(bid, n);
      }

      const savedEdgeMap = new Map<string, Edge>();
      for (const e of savedEdges) {
        const bid = (e.data as FlowEdgeData)?.backendId;
        if (bid) savedEdgeMap.set(bid, e);
      }

      // --- Activity CRUD ---
      // 1. Find new nodes (no backendId) -> create
      const newNodes = currentNodes.filter((n) => !(n.data as ActivityNodeData).backendId);
      // 2. Find existing nodes that changed -> update
      const existingNodes = currentNodes.filter((n) => (n.data as ActivityNodeData).backendId);
      // 3. Find deleted nodes (in saved but not in current)
      const currentBackendIds = new Set(
        currentNodes
          .map((n) => (n.data as ActivityNodeData).backendId)
          .filter(Boolean),
      );
      const deletedNodeIds = [...savedNodeMap.keys()].filter(
        (bid) => !currentBackendIds.has(bid),
      );

      // Delete activities first (to avoid flow FK issues)
      for (const bid of deletedNodeIds) {
        await deleteActivity(templateId, bid);
      }

      // Create new activities
      const newIdMap = new Map<string, string>(); // local id -> backend id
      for (const node of newNodes) {
        const data = node.data as ActivityNodeData;
        const result = await createActivity(templateId, {
          name: data.name,
          activity_type: data.activityType,
          description: data.description,
          performer_type: data.performerType,
          performer_id: data.performerId,
          trigger_type: data.triggerType,
          method_name: data.methodName,
          position_x: node.position.x,
          position_y: node.position.y,
          routing_type: data.routingType,
          performer_list: data.performerList,
          expected_duration_hours: data.expectedDurationHours ?? null,
          escalation_action: data.escalationAction ?? null,
          warning_threshold_hours: data.warningThresholdHours ?? null,
        });
        newIdMap.set(node.id, result.id);
        // Update node in store with backendId
        useDesignerStore.getState().updateNodeData(node.id, { backendId: result.id });
      }

      // Update existing activities
      for (const node of existingNodes) {
        const data = node.data as ActivityNodeData;
        const bid = data.backendId!;
        const savedNode = savedNodeMap.get(bid);
        // Always update to sync position and data changes
        if (savedNode) {
          await updateActivity(templateId, bid, {
            name: data.name,
            description: data.description,
            performer_type: data.performerType,
            performer_id: data.performerId,
            trigger_type: data.triggerType,
            method_name: data.methodName,
            position_x: node.position.x,
            position_y: node.position.y,
            routing_type: data.routingType,
            performer_list: data.performerList,
            expected_duration_hours: data.expectedDurationHours ?? null,
            escalation_action: data.escalationAction ?? null,
            warning_threshold_hours: data.warningThresholdHours ?? null,
          });
        }
      }

      // --- Flow CRUD ---
      // Delete removed edges
      const currentEdgeBackendIds = new Set(
        currentEdges
          .map((e) => (e.data as FlowEdgeData)?.backendId)
          .filter(Boolean),
      );
      const deletedEdgeIds = [...savedEdgeMap.keys()].filter(
        (bid) => !currentEdgeBackendIds.has(bid),
      );
      for (const bid of deletedEdgeIds) {
        await deleteFlow(templateId, bid);
      }

      // Create new edges
      for (const edge of currentEdges) {
        const data = (edge.data ?? { flowType: 'normal' }) as FlowEdgeData;
        if (data.backendId) continue; // existing edge

        // Resolve source/target to backend IDs
        const sourceBackendId =
          newIdMap.get(edge.source) ??
          (currentNodes.find((n) => n.id === edge.source)?.data as ActivityNodeData)?.backendId ??
          edge.source;
        const targetBackendId =
          newIdMap.get(edge.target) ??
          (currentNodes.find((n) => n.id === edge.target)?.data as ActivityNodeData)?.backendId ??
          edge.target;

        const result = await createFlow(templateId, {
          source_activity_id: sourceBackendId,
          target_activity_id: targetBackendId,
          flow_type: data.flowType,
          condition_expression: data.conditionExpression,
          display_label: data.displayLabel,
        });
        // Update edge in store with backendId
        useDesignerStore.getState().updateEdgeData(edge.id, { backendId: result.id });
      }

      // Update existing edges that changed
      for (const edge of currentEdges) {
        const data = (edge.data ?? { flowType: 'normal' }) as FlowEdgeData;
        if (!data.backendId) continue;
        const saved = savedEdgeMap.get(data.backendId);
        if (!saved) continue;
        const savedData = (saved.data ?? { flowType: 'normal' }) as FlowEdgeData;
        if (
          data.flowType !== savedData.flowType ||
          data.conditionExpression !== savedData.conditionExpression ||
          data.displayLabel !== savedData.displayLabel
        ) {
          await updateFlow(templateId, data.backendId, {
            flow_type: data.flowType,
            condition_expression: data.conditionExpression,
            display_label: data.displayLabel,
          });
        }
      }

      // --- Variable CRUD ---
      const currentVars = variables;
      const savedVars = lastSavedVariables.current;
      const savedVarMap = new Map(savedVars.map((v) => [v.id, v]));
      const currentVarIds = new Set(currentVars.filter((v) => v.id).map((v) => v.id));

      // Delete removed variables
      for (const sv of savedVars) {
        if (!currentVarIds.has(sv.id)) {
          await deleteVariable(templateId, sv.id);
        }
      }

      // Create or update variables
      const updatedVars: ProcessVariable[] = [];
      for (const v of currentVars) {
        if (!v.id || !savedVarMap.has(v.id)) {
          // New variable
          const result = await createVariable(templateId, {
            name: v.name,
            variable_type: v.variable_type,
            string_value: v.string_value,
            int_value: v.int_value,
            bool_value: v.bool_value,
            date_value: v.date_value,
          });
          updatedVars.push(result);
        } else {
          const saved = savedVarMap.get(v.id)!;
          if (
            v.name !== saved.name ||
            v.variable_type !== saved.variable_type ||
            v.string_value !== saved.string_value ||
            v.int_value !== saved.int_value ||
            v.bool_value !== saved.bool_value ||
            v.date_value !== saved.date_value
          ) {
            const result = await updateVariable(templateId, v.id, {
              name: v.name,
              variable_type: v.variable_type,
              string_value: v.string_value,
              int_value: v.int_value,
              bool_value: v.bool_value,
              date_value: v.date_value,
            });
            updatedVars.push(result);
          } else {
            updatedVars.push(v);
          }
        }
      }

      // Update local state
      setVariables(updatedVars);
      lastSavedVariables.current = structuredClone(updatedVars);

      // Update snapshot
      const freshState = useDesignerStore.getState();
      lastSavedSnapshot.current = {
        nodes: structuredClone(freshState.nodes),
        edges: structuredClone(freshState.edges),
      };
      useDesignerStore.getState().setClean();
      toast.success('Template saved');
    } catch (err) {
      console.error('Save failed:', err);
      toast.error('Failed to save template. Check your connection and try again.', {
        action: {
          label: 'Retry',
          onClick: () => save(),
        },
      });
    } finally {
      setSaving(false);
    }
  }, [templateId, variables]);

  const validateAndInstall = useCallback(async () => {
    setValidating(true);
    try {
      // Save first
      await save();

      // Validate
      const result = await validateTemplate(templateId);
      if (result.valid) {
        await installTemplate(templateId);
        setValidationErrors([]);
        toast.success('Template installed successfully');
      } else {
        setValidationErrors(result.errors);
        toast.error(`${result.errors.length} validation errors found`);
        useUiStore.getState().setErrorPanelExpanded(true);

        // Mark nodes with errors
        const store = useDesignerStore.getState();
        const errorEntityIds = new Set(
          result.errors.map((e) => e.entity_id).filter(Boolean),
        );
        const updatedNodes = store.nodes.map((node) => {
          const data = node.data as ActivityNodeData;
          const hasError =
            errorEntityIds.has(data.backendId ?? '') || errorEntityIds.has(node.id);
          return { ...node, data: { ...node.data, hasError } };
        });
        useDesignerStore.setState({ nodes: updatedNodes });
      }
    } catch (err) {
      console.error('Validate/install failed:', err);
      toast.error('Validation failed. Please try again.');
    } finally {
      setValidating(false);
    }
  }, [templateId, save]);

  return {
    save,
    validateAndInstall,
    saving,
    validating,
    validationErrors,
    variables,
    setVariables,
  };
}
