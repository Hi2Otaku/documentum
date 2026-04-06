import { useState, useCallback, useEffect } from 'react';
import { useDesignerStore } from '../../stores/designerStore';
import type { ActivityNodeData, FlowEdgeData } from '../../types/designer';
import type { ProcessVariable } from '../../types/workflow';

// ---- Node Properties ----
function NodeProperties({
  nodeId,
  data,
  incomingEdgeCount,
  outgoingEdgeCount,
}: {
  nodeId: string;
  data: ActivityNodeData;
  incomingEdgeCount: number;
  outgoingEdgeCount: number;
}) {
  const updateNodeData = useDesignerStore((s) => s.updateNodeData);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Activity Properties</h3>

      {/* Activity type badge */}
      <div>
        <span className="text-xs font-medium text-muted-foreground">Type</span>
        <div className="mt-1">
          <span
            className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${
              data.activityType === 'start'
                ? 'bg-green-100 text-green-800'
                : data.activityType === 'end'
                  ? 'bg-red-100 text-red-800'
                  : data.activityType === 'manual'
                    ? 'bg-blue-100 text-blue-800'
                    : data.activityType === 'sub_workflow'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-orange-100 text-orange-800'
            }`}
          >
            {data.activityType}
          </span>
        </div>
      </div>

      {/* Name */}
      <div>
        <label className="text-sm font-medium" htmlFor="node-name">
          Name
        </label>
        <input
          id="node-name"
          type="text"
          className="mt-1 w-full rounded border px-3 py-2 text-sm"
          value={data.name ?? ''}
          onChange={(e) => updateNodeData(nodeId, { name: e.target.value })}
        />
      </div>

      {/* Description */}
      <div>
        <label className="text-sm font-medium" htmlFor="node-description">
          Description
        </label>
        <textarea
          id="node-description"
          className="mt-1 w-full rounded border px-3 py-2 text-sm min-h-[60px]"
          value={data.description ?? ''}
          onChange={(e) =>
            updateNodeData(nodeId, { description: e.target.value })
          }
        />
      </div>

      {/* Performer section (manual nodes only) */}
      {data.activityType === 'manual' && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-muted-foreground">
            Performer
          </h4>

          <div>
            <label className="text-sm font-medium" htmlFor="performer-type">
              Type
            </label>
            <select
              id="performer-type"
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
              value={data.performerType ?? ''}
              onChange={(e) =>
                updateNodeData(nodeId, {
                  performerType: e.target.value || null,
                  performerId: null,
                  performerList: null,
                })
              }
            >
              <option value="">Select...</option>
              <option value="supervisor">Supervisor</option>
              <option value="user">User</option>
              <option value="group">Group</option>
              <option value="sequential">Sequential</option>
              <option value="runtime_selection">Runtime Selection</option>
            </select>
          </div>

          {/* User picker */}
          {data.performerType === 'user' && (
            <div>
              <label className="text-sm font-medium" htmlFor="performer-user">
                User
              </label>
              <input
                id="performer-user"
                type="text"
                className="mt-1 w-full rounded border px-3 py-2 text-sm"
                placeholder="User ID"
                value={data.performerId ?? ''}
                onChange={(e) =>
                  updateNodeData(nodeId, { performerId: e.target.value || null })
                }
              />
            </div>
          )}

          {/* Group picker */}
          {data.performerType === 'group' && (
            <div>
              <label className="text-sm font-medium" htmlFor="performer-group">
                Group
              </label>
              <input
                id="performer-group"
                type="text"
                className="mt-1 w-full rounded border px-3 py-2 text-sm"
                placeholder="Group ID"
                value={data.performerId ?? ''}
                onChange={(e) =>
                  updateNodeData(nodeId, { performerId: e.target.value || null })
                }
              />
            </div>
          )}

          {/* Sequential performer list */}
          {data.performerType === 'sequential' && (
            <SequentialPerformerList
              nodeId={nodeId}
              performerList={data.performerList ?? []}
            />
          )}
        </div>
      )}

      {/* Trigger type (when 2+ incoming edges) */}
      {incomingEdgeCount >= 2 && (
        <div>
          <label className="text-sm font-medium" htmlFor="trigger-type">
            Trigger Type
          </label>
          <select
            id="trigger-type"
            className="mt-1 w-full rounded border px-3 py-2 text-sm"
            value={data.triggerType ?? 'or_join'}
            onChange={(e) =>
              updateNodeData(nodeId, {
                triggerType: e.target.value as 'and_join' | 'or_join',
              })
            }
          >
            <option value="and_join">AND-join</option>
            <option value="or_join">OR-join</option>
          </select>
        </div>
      )}

      {/* Routing type (when 2+ outgoing edges) */}
      {outgoingEdgeCount >= 2 && (
        <div>
          <label className="text-sm font-medium" htmlFor="routing-type">
            Routing Type
          </label>
          <select
            id="routing-type"
            className="mt-1 w-full rounded border px-3 py-2 text-sm"
            value={data.routingType ?? ''}
            onChange={(e) =>
              updateNodeData(nodeId, { routingType: e.target.value || null })
            }
          >
            <option value="">None</option>
            <option value="conditional">Conditional</option>
            <option value="performer_chosen">Performer Chosen</option>
            <option value="broadcast">Broadcast</option>
          </select>
        </div>
      )}

      {/* Method name (auto nodes only) */}
      {data.activityType === 'auto' && (
        <div>
          <label className="text-sm font-medium" htmlFor="method-name">
            Method Name
          </label>
          <input
            id="method-name"
            type="text"
            className="mt-1 w-full rounded border px-3 py-2 text-sm"
            placeholder="e.g. send_notification"
            value={data.methodName ?? ''}
            onChange={(e) =>
              updateNodeData(nodeId, { methodName: e.target.value || null })
            }
          />
        </div>
      )}

      {/* Sub-workflow configuration */}
      {data.activityType === 'sub_workflow' && (
        <SubWorkflowConfig
          nodeId={nodeId}
          subTemplateId={data.subTemplateId ?? null}
          variableMapping={data.variableMapping ?? null}
        />
      )}
    </div>
  );
}

// ---- Sub-Workflow Config ----
interface TemplateSummary {
  id: string;
  name: string;
}

function SubWorkflowConfig({
  nodeId,
  subTemplateId,
  variableMapping,
}: {
  nodeId: string;
  subTemplateId: string | null;
  variableMapping: Record<string, string> | null;
}) {
  const updateNodeData = useDesignerStore((s) => s.updateNodeData);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [mappingRows, setMappingRows] = useState<{ parentVar: string; childVar: string }[]>([]);

  // Fetch available templates
  useEffect(() => {
    fetch('/api/templates?state=active')
      .then((res) => (res.ok ? res.json() : { data: [] }))
      .then((json) => {
        const list = Array.isArray(json.data) ? json.data : Array.isArray(json) ? json : [];
        setTemplates(
          list.map((t: { id: string; name: string }) => ({ id: t.id, name: t.name })),
        );
      })
      .catch(() => setTemplates([]));
  }, []);

  // Sync mapping rows from data prop
  useEffect(() => {
    if (variableMapping) {
      setMappingRows(
        Object.entries(variableMapping).map(([parentVar, childVar]) => ({
          parentVar,
          childVar,
        })),
      );
    } else {
      setMappingRows([]);
    }
  }, [variableMapping]);

  const handleTemplateChange = (value: string) => {
    updateNodeData(nodeId, { subTemplateId: value || null });
  };

  const syncMapping = (rows: { parentVar: string; childVar: string }[]) => {
    const obj: Record<string, string> = {};
    for (const row of rows) {
      if (row.parentVar.trim()) {
        obj[row.parentVar.trim()] = row.childVar.trim();
      }
    }
    updateNodeData(nodeId, {
      variableMapping: Object.keys(obj).length > 0 ? obj : null,
    });
  };

  const addRow = () => {
    const next = [...mappingRows, { parentVar: '', childVar: '' }];
    setMappingRows(next);
  };

  const removeRow = (index: number) => {
    const next = mappingRows.filter((_, i) => i !== index);
    setMappingRows(next);
    syncMapping(next);
  };

  const updateRow = (index: number, field: 'parentVar' | 'childVar', value: string) => {
    const next = [...mappingRows];
    next[index] = { ...next[index], [field]: value };
    setMappingRows(next);
    syncMapping(next);
  };

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-muted-foreground">
        Sub-Workflow
      </h4>

      {/* Template selector */}
      <div>
        <label className="text-sm font-medium" htmlFor="sub-template">
          Sub-Workflow Template
        </label>
        <select
          id="sub-template"
          className="mt-1 w-full rounded border px-3 py-2 text-sm"
          value={subTemplateId ?? ''}
          onChange={(e) => handleTemplateChange(e.target.value)}
        >
          <option value="" disabled>
            Select a template...
          </option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      {/* Variable mapping editor */}
      <div>
        <label className="text-sm font-medium">
          Variable Mapping (Parent -&gt; Child)
        </label>
        <div className="mt-1 space-y-2">
          {mappingRows.map((row, idx) => (
            <div key={idx} className="flex items-center gap-1">
              <input
                type="text"
                className="flex-1 rounded border px-2 py-1 text-sm"
                placeholder="Parent var"
                value={row.parentVar}
                onChange={(e) => updateRow(idx, 'parentVar', e.target.value)}
              />
              <span className="text-xs text-muted-foreground shrink-0">-&gt;</span>
              <input
                type="text"
                className="flex-1 rounded border px-2 py-1 text-sm"
                placeholder="Child var"
                value={row.childVar}
                onChange={(e) => updateRow(idx, 'childVar', e.target.value)}
              />
              <button
                onClick={() => removeRow(idx)}
                className="px-2 text-red-500 hover:text-red-700 text-sm"
                aria-label="Remove mapping"
              >
                x
              </button>
            </div>
          ))}
          <button
            onClick={addRow}
            className="text-sm text-primary hover:underline"
          >
            + Add Mapping
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Sequential Performer List ----
function SequentialPerformerList({
  nodeId,
  performerList,
}: {
  nodeId: string;
  performerList: string[];
}) {
  const updateNodeData = useDesignerStore((s) => s.updateNodeData);

  const addPerformer = () => {
    updateNodeData(nodeId, { performerList: [...performerList, ''] });
  };

  const removePerformer = (index: number) => {
    const updated = performerList.filter((_, i) => i !== index);
    updateNodeData(nodeId, { performerList: updated });
  };

  const updatePerformer = (index: number, value: string) => {
    const updated = [...performerList];
    updated[index] = value;
    updateNodeData(nodeId, { performerList: updated });
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Sequential Performers</label>
      {performerList.map((userId, idx) => (
        <div key={idx} className="flex gap-1">
          <input
            type="text"
            className="flex-1 rounded border px-2 py-1 text-sm"
            placeholder="User ID"
            value={userId}
            onChange={(e) => updatePerformer(idx, e.target.value)}
          />
          <button
            onClick={() => removePerformer(idx)}
            className="px-2 text-red-500 hover:text-red-700 text-sm"
            aria-label="Remove performer"
          >
            x
          </button>
        </div>
      ))}
      <button
        onClick={addPerformer}
        className="text-sm text-primary hover:underline"
      >
        + Add performer
      </button>
    </div>
  );
}

// ---- Edge Properties ----
function EdgeProperties({
  edgeId,
  data,
  sourceRoutingType,
}: {
  edgeId: string;
  data: FlowEdgeData;
  sourceRoutingType: string | null | undefined;
}) {
  const updateEdgeData = useDesignerStore((s) => s.updateEdgeData);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Flow Properties</h3>

      {/* Flow type */}
      <div>
        <label className="text-sm font-medium" htmlFor="flow-type">
          Flow Type
        </label>
        <select
          id="flow-type"
          className="mt-1 w-full rounded border px-3 py-2 text-sm"
          value={data.flowType ?? 'normal'}
          onChange={(e) =>
            updateEdgeData(edgeId, {
              flowType: e.target.value as 'normal' | 'reject',
            })
          }
        >
          <option value="normal">Normal</option>
          <option value="reject">Reject</option>
        </select>
      </div>

      {/* Label */}
      <div>
        <label className="text-sm font-medium" htmlFor="flow-label">
          Label
        </label>
        <input
          id="flow-label"
          type="text"
          className="mt-1 w-full rounded border px-3 py-2 text-sm"
          value={data.displayLabel ?? ''}
          onChange={(e) =>
            updateEdgeData(edgeId, { displayLabel: e.target.value || null })
          }
        />
      </div>

      {/* Condition expression (when source has conditional routing) */}
      {sourceRoutingType === 'conditional' && (
        <div>
          <label className="text-sm font-medium" htmlFor="condition-expr">
            Condition Expression
          </label>
          <textarea
            id="condition-expr"
            className="mt-1 w-full rounded border px-3 py-2 text-sm min-h-[60px] font-mono"
            placeholder="e.g. approved == true"
            value={data.conditionExpression ?? ''}
            onChange={(e) =>
              updateEdgeData(edgeId, {
                conditionExpression: e.target.value || null,
              })
            }
          />
        </div>
      )}
    </div>
  );
}

// ---- Template Info + Variables (no selection) ----
interface TemplatePanelProps {
  variables: ProcessVariable[];
  onVariablesChange: (vars: ProcessVariable[]) => void;
  templateName: string;
  templateDescription: string;
  onTemplateMetaChange: (name: string, description: string) => void;
}

function TemplatePanel({
  variables,
  onVariablesChange,
  templateName: initialName,
  templateDescription: initialDesc,
  onTemplateMetaChange,
}: TemplatePanelProps) {
  const [activeTab, setActiveTab] = useState<'template' | 'variables'>(
    'template',
  );
  const [templateName, setTemplateName] = useState(initialName);
  const [templateDescription, setTemplateDescription] = useState(initialDesc);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newVarName, setNewVarName] = useState('');
  const [newVarType, setNewVarType] = useState<'string' | 'int' | 'boolean' | 'date'>('string');
  const [newVarDefault, setNewVarDefault] = useState('');

  const handleNameChange = useCallback(
    (name: string) => {
      setTemplateName(name);
      onTemplateMetaChange(name, templateDescription);
    },
    [templateDescription, onTemplateMetaChange],
  );

  const handleDescChange = useCallback(
    (desc: string) => {
      setTemplateDescription(desc);
      onTemplateMetaChange(templateName, desc);
    },
    [templateName, onTemplateMetaChange],
  );

  const addVariable = () => {
    if (!newVarName.trim()) return;
    const newVar: ProcessVariable = {
      id: '', // empty id signals new variable to save hook
      process_template_id: null,
      workflow_instance_id: null,
      name: newVarName.trim(),
      variable_type: newVarType,
      string_value: newVarType === 'string' ? newVarDefault : null,
      int_value: newVarType === 'int' ? parseInt(newVarDefault, 10) || null : null,
      bool_value: newVarType === 'boolean' ? newVarDefault === 'true' : null,
      date_value: newVarType === 'date' ? newVarDefault || null : null,
      created_at: '',
      updated_at: '',
      is_deleted: false,
    };
    onVariablesChange([...variables, newVar]);
    setNewVarName('');
    setNewVarType('string');
    setNewVarDefault('');
    setShowAddForm(false);
  };

  const deleteVariable = (id: string) => {
    onVariablesChange(variables.filter((v) => v.id !== id));
  };

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex border-b">
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'template'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setActiveTab('template')}
        >
          Template
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'variables'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setActiveTab('variables')}
        >
          Variables
        </button>
      </div>

      {activeTab === 'template' && (
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium" htmlFor="template-name">
              Name
            </label>
            <input
              id="template-name"
              type="text"
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
              value={templateName}
              onChange={(e) => handleNameChange(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="template-desc">
              Description
            </label>
            <textarea
              id="template-desc"
              className="mt-1 w-full rounded border px-3 py-2 text-sm min-h-[60px]"
              value={templateDescription}
              onChange={(e) => handleDescChange(e.target.value)}
            />
          </div>
        </div>
      )}

      {activeTab === 'variables' && (
        <div className="space-y-3">
          {variables.map((v) => (
            <div
              key={v.id}
              className="flex items-center justify-between rounded border px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{v.name}</span>
                <span className="inline-block px-1.5 py-0.5 text-xs rounded bg-muted text-muted-foreground">
                  {v.variable_type}
                </span>
              </div>
              <button
                onClick={() => deleteVariable(v.id)}
                className="text-red-500 hover:text-red-700"
                aria-label={`Delete variable ${v.name}`}
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          ))}

          {showAddForm && (
            <div className="space-y-2 rounded border p-3">
              <input
                type="text"
                className="w-full rounded border px-3 py-2 text-sm"
                placeholder="Variable name"
                value={newVarName}
                onChange={(e) => setNewVarName(e.target.value)}
              />
              <select
                className="w-full rounded border px-3 py-2 text-sm"
                value={newVarType}
                onChange={(e) =>
                  setNewVarType(
                    e.target.value as 'string' | 'int' | 'boolean' | 'date',
                  )
                }
              >
                <option value="string">string</option>
                <option value="int">int</option>
                <option value="boolean">boolean</option>
                <option value="date">date</option>
              </select>
              <input
                type="text"
                className="w-full rounded border px-3 py-2 text-sm"
                placeholder="Default value"
                value={newVarDefault}
                onChange={(e) => setNewVarDefault(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={addVariable}
                  className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground"
                >
                  Add
                </button>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="rounded border px-3 py-1.5 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {!showAddForm && (
            <button
              onClick={() => setShowAddForm(true)}
              className="w-full rounded border border-dashed px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:border-foreground transition-colors"
            >
              + Add Variable
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---- Main PropertiesPanel ----
interface PropertiesPanelProps {
  variables: ProcessVariable[];
  onVariablesChange: (vars: ProcessVariable[]) => void;
  templateName: string;
  templateDescription: string;
  onTemplateMetaChange: (name: string, description: string) => void;
}

export function PropertiesPanel({
  variables,
  onVariablesChange,
  templateName,
  templateDescription,
  onTemplateMetaChange,
}: PropertiesPanelProps) {
  const selectedNodeId = useDesignerStore((s) => s.selectedNodeId);
  const selectedEdgeId = useDesignerStore((s) => s.selectedEdgeId);
  const nodes = useDesignerStore((s) => s.nodes);
  const edges = useDesignerStore((s) => s.edges);

  const selectedNode = selectedNodeId
    ? nodes.find((n) => n.id === selectedNodeId)
    : null;
  const selectedEdge = selectedEdgeId
    ? edges.find((e) => e.id === selectedEdgeId)
    : null;

  // Count incoming/outgoing edges for the selected node
  const incomingEdgeCount = selectedNodeId
    ? edges.filter((e) => e.target === selectedNodeId).length
    : 0;
  const outgoingEdgeCount = selectedNodeId
    ? edges.filter((e) => e.source === selectedNodeId).length
    : 0;

  // Get source node routing type for edge properties
  const sourceRoutingType = selectedEdge
    ? (nodes.find((n) => n.id === selectedEdge.source)?.data as ActivityNodeData | undefined)
        ?.routingType
    : null;

  return (
    <aside className="w-[320px] border-l bg-background p-4 overflow-y-auto shrink-0">
      {selectedNode ? (
        <NodeProperties
          nodeId={selectedNode.id}
          data={selectedNode.data as ActivityNodeData}
          incomingEdgeCount={incomingEdgeCount}
          outgoingEdgeCount={outgoingEdgeCount}
        />
      ) : selectedEdge ? (
        <EdgeProperties
          edgeId={selectedEdge.id}
          data={(selectedEdge.data ?? { flowType: 'normal' }) as FlowEdgeData}
          sourceRoutingType={sourceRoutingType}
        />
      ) : (
        <TemplatePanel
          variables={variables}
          onVariablesChange={onVariablesChange}
          templateName={templateName}
          templateDescription={templateDescription}
          onTemplateMetaChange={onTemplateMetaChange}
        />
      )}
    </aside>
  );
}
