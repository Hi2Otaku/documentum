import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { listTemplates, createTemplate } from '../api/templates';
import type { ProcessTemplate } from '../types/workflow';

export function TemplateListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [newName, setNewName] = useState('');

  const { data: templates, isLoading, error } = useQuery<ProcessTemplate[]>({
    queryKey: ['templates'],
    queryFn: listTemplates,
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => createTemplate({ name }),
    onSuccess: (template) => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      navigate(`/designer/${template.id}`);
    },
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">
          Workflow Templates
        </h1>
      </header>

      <main className="max-w-4xl mx-auto p-6">
        {/* Create new template */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <h2 className="text-lg font-semibold mb-3">Create New Template</h2>
          <form
            className="flex gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (newName.trim()) {
                createMutation.mutate(newName.trim());
                setNewName('');
              }
            }}
          >
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Template name..."
              className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={!newName.trim() || createMutation.isPending}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </form>
        </div>

        {/* Template list */}
        {isLoading && (
          <div className="text-center text-gray-500 py-8">
            Loading templates...
          </div>
        )}

        {error && (
          <div className="text-center text-red-500 py-8">
            Error loading templates. Make sure the backend is running and you are
            logged in.
          </div>
        )}

        {templates && templates.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            No templates yet. Create one to get started.
          </div>
        )}

        {templates && templates.length > 0 && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    Name
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    State
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    Version
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    Updated
                  </th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {templates.map((t) => (
                  <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {t.name}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                          t.state === 'active'
                            ? 'bg-green-100 text-green-700'
                            : t.state === 'draft'
                              ? 'bg-gray-100 text-gray-700'
                              : t.state === 'validated'
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-orange-100 text-orange-700'
                        }`}
                      >
                        {t.state}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">v{t.version}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(t.updated_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => navigate(`/designer/${t.id}`)}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Open Designer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
