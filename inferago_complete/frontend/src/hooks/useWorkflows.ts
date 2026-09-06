import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWorkflows, getWorkflow, createWorkflow, updateWorkflow, deleteWorkflow } from "../api/workflows";

export const workflowKeys = {
  all:    ["workflows"] as const,
  detail: (id: string) => ["workflows", id] as const,
};

export const useWorkflows     = () => useQuery({ queryKey: workflowKeys.all, queryFn: getWorkflows });
export const useWorkflow      = (id: string) => useQuery({ queryKey: workflowKeys.detail(id), queryFn: () => getWorkflow(id), enabled: !!id });

export const useCreateWorkflow = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: createWorkflow, onSuccess: () => qc.invalidateQueries({ queryKey: workflowKeys.all }) });
};

export const useUpdateWorkflow = (id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name?: string; description?: string }) => updateWorkflow(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: workflowKeys.all }); qc.invalidateQueries({ queryKey: workflowKeys.detail(id) }); },
  });
};

export const useDeleteWorkflow = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: deleteWorkflow, onSuccess: () => qc.invalidateQueries({ queryKey: workflowKeys.all }) });
};
