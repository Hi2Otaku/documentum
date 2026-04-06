import { Check, X } from "lucide-react";
import { Progress } from "../ui/progress";

interface UploadProgressItemProps {
  name: string;
  status: "pending" | "uploading" | "done" | "error";
}

export function UploadProgressItem({ name, status }: UploadProgressItemProps) {
  return (
    <div className="flex items-center gap-2 h-9 px-4">
      <span className="text-sm truncate max-w-[200px]">{name}</span>
      <Progress
        className="flex-1 h-1"
        value={status === "done" ? 100 : status === "error" ? 0 : undefined}
      />
      {status === "done" && <Check size={16} className="text-green-600 shrink-0" />}
      {status === "error" && <X size={16} className="text-red-600 shrink-0" />}
    </div>
  );
}
