import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, ChevronRight, GitBranch, Loader2 } from "lucide-react";
import { useWorkflows, useCreateWorkflow, useDeleteWorkflow } from "../hooks/useWorkflows";

export default function WorkflowList() {
  const navigate         = useNavigate();
  const { data: workflows, isLoading } = useWorkflows();
  const createMutation   = useCreateWorkflow();
  const deleteMutation   = useDeleteWorkflow();
  const [showModal, setShowModal] = useState(false);
  const [name, setName]           = useState("");
  const [description, setDescription] = useState("");
  const [n8nId, setN8nId]         = useState("");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ name, description, n8n_workflow_id: n8nId }, {
      onSuccess: () => { setShowModal(false); setName(""); setDescription(""); setN8nId(""); },
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Workflows</h1>
          <p className="text-gray-400 text-sm mt-1">Manage your registered automation workflows</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Workflow
        </button>
      </div>

      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-blue-400 animate-spin" /></div>
        ) : !workflows?.length ? (
          <div className="text-center py-12">
            <GitBranch className="w-10 h-10 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400">No workflows registered yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {workflows.map((wf) => (
              <div key={wf.id} onClick={() => navigate(`/workflows/${wf.id}`)}
                className="flex items-center justify-between py-4 px-2 hover:bg-gray-800/40 cursor-pointer rounded-lg transition-colors group">
                <div className="flex items-center gap-4">
                  <div className="bg-blue-600/20 p-2 rounded-lg"><GitBranch className="w-4 h-4 text-blue-400" /></div>
                  <div>
                    <p className="font-medium text-white group-hover:text-blue-300 transition-colors">{wf.name}</p>
                    {wf.description && <p className="text-xs text-gray-500 mt-0.5">{wf.description}</p>}
                    <p className="text-xs text-gray-600 mt-0.5 font-mono">n8n ID: {wf.n8n_workflow_id}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 hidden md:block">{new Date(wf.created_at).toLocaleDateString()}</span>
                  <button onClick={(e) => { e.stopPropagation(); if (confirm("Delete this workflow?")) deleteMutation.mutate(wf.id); }}
                    className="p-1.5 rounded hover:bg-red-900/40 text-gray-600 hover:text-red-400 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <ChevronRight className="w-4 h-4 text-gray-600" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-white mb-4">Register Workflow</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Support Bot" className="input" required />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Description <span className="text-gray-600">(optional)</span></label>
                <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this workflow do?" className="input" />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Workflow ID (from your platform)</label>
                <input value={n8nId} onChange={(e) => setN8nId(e.target.value)} placeholder="e.g. abc123" className="input font-mono" required />
                <p className="text-xs text-gray-600 mt-1">Found in n8n → Workflow Settings → Workflow ID</p>
              </div>
              {createMutation.isError && (
                <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-3">
                  <p className="text-red-300 text-sm">{(createMutation.error as any)?.response?.data?.detail ?? "Failed to create"}</p>
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" disabled={createMutation.isPending} className="btn-primary flex-1">
                  {createMutation.isPending ? "Saving..." : "Register"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
