/** Toolbar -- stub for Task 1, full implementation in Task 2 */
interface ToolbarProps {
  templateName: string;
  onSave: () => void;
  onValidateInstall: () => void;
  saving: boolean;
  validating: boolean;
}

export function Toolbar({ templateName }: ToolbarProps) {
  return (
    <div className="h-12 border-b flex items-center px-4 shrink-0">
      <span className="text-lg font-semibold">{templateName}</span>
    </div>
  );
}
