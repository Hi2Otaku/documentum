import { useState, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Rocket } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { WizardStepIndicator } from "./WizardStepIndicator";
import { TemplatePickerStep } from "./TemplatePickerStep";
import { DocumentAttachStep } from "./DocumentAttachStep";
import { VariablesStep } from "./VariablesStep";
import { ReviewStep } from "./ReviewStep";
import { startWorkflow } from "../../api/workflows";
import { fetchDocuments } from "../../api/documents";

interface StartWorkflowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function StartWorkflowDialog({
  open,
  onOpenChange,
}: StartWorkflowDialogProps) {
  const queryClient = useQueryClient();

  const [wizardStep, setWizardStep] = useState(1);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(
    null,
  );
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [variableValues, setVariableValues] = useState<
    Record<string, unknown>
  >({});

  // Fetch templates for name lookup in review step
  const { data: templatesData } = useQuery({
    queryKey: ["templates"],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      const headers: HeadersInit = token
        ? {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          }
        : { "Content-Type": "application/json" };
      const res = await fetch("/api/v1/templates/", { headers });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();
      return json.data as { id: string; name: string }[];
    },
    enabled: open,
  });

  // Fetch documents for review step names
  const { data: documentsData } = useQuery({
    queryKey: ["documents"],
    queryFn: () => fetchDocuments({ page: 1, page_size: 100 }),
    enabled: open,
  });

  const selectedTemplate = selectedTemplateId
    ? (templatesData ?? []).find((t) => t.id === selectedTemplateId) ?? null
    : null;

  const allDocuments = (documentsData?.data ?? []).map((d) => ({
    id: d.id,
    title: d.title,
  }));

  const resetState = useCallback(() => {
    setWizardStep(1);
    setSelectedTemplateId(null);
    setSelectedDocumentIds([]);
    setVariableValues({});
  }, []);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        resetState();
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange, resetState],
  );

  const launchMutation = useMutation({
    mutationFn: () =>
      startWorkflow({
        template_id: selectedTemplateId!,
        document_ids: selectedDocumentIds,
        initial_variables: variableValues,
      }),
    onSuccess: () => {
      toast.success("Workflow started");
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      handleOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error(`Action failed: ${error.message}`);
    },
  });

  const handleLaunch = () => {
    launchMutation.mutate();
  };

  const handleVariableChange = useCallback(
    (name: string, value: unknown) => {
      setVariableValues((prev) => ({ ...prev, [name]: value }));
    },
    [],
  );

  const handleDocumentToggle = useCallback((id: string) => {
    setSelectedDocumentIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id],
    );
  }, []);

  const completedSteps: number[] = [];
  if (selectedTemplateId) completedSteps.push(1);
  if (wizardStep > 2) completedSteps.push(2);
  if (wizardStep > 3) completedSteps.push(3);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-[640px] min-h-[400px] flex flex-col">
        <DialogHeader>
          <DialogTitle>Start Workflow</DialogTitle>
        </DialogHeader>

        <WizardStepIndicator
          currentStep={wizardStep}
          completedSteps={completedSteps}
        />

        <div className="flex-1 min-h-[280px] p-6 overflow-y-auto">
          {wizardStep === 1 && (
            <TemplatePickerStep
              selectedTemplateId={selectedTemplateId}
              onSelect={setSelectedTemplateId}
            />
          )}
          {wizardStep === 2 && (
            <DocumentAttachStep
              selectedDocumentIds={selectedDocumentIds}
              onToggle={handleDocumentToggle}
            />
          )}
          {wizardStep === 3 && selectedTemplateId && (
            <VariablesStep
              templateId={selectedTemplateId}
              variableValues={variableValues}
              onChange={handleVariableChange}
            />
          )}
          {wizardStep === 4 && (
            <ReviewStep
              selectedTemplate={
                selectedTemplate
                  ? { id: selectedTemplate.id, name: selectedTemplate.name }
                  : null
              }
              selectedDocumentIds={selectedDocumentIds}
              variableValues={variableValues}
              documents={allDocuments}
            />
          )}
        </div>

        <DialogFooter className="flex justify-end gap-2 p-4 border-t">
          {wizardStep > 1 && (
            <Button
              variant="outline"
              onClick={() => setWizardStep((s) => s - 1)}
            >
              Back
            </Button>
          )}
          {wizardStep < 4 && (
            <Button
              onClick={() => setWizardStep((s) => s + 1)}
              disabled={wizardStep === 1 && selectedTemplateId === null}
            >
              Next
            </Button>
          )}
          {wizardStep === 4 && (
            <Button
              onClick={handleLaunch}
              disabled={launchMutation.isPending}
            >
              <Rocket className="w-4 h-4 mr-2" />
              Launch Workflow
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
