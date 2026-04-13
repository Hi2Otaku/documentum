import { FolderOpen } from "lucide-react";
import { Badge } from "../ui/badge";

interface AccessSourceBadgeProps {
  accessSource: string | null | undefined;
  folderName: string | null | undefined;
}

export function AccessSourceBadge({
  accessSource,
  folderName,
}: AccessSourceBadgeProps) {
  if (accessSource !== "folder_inherited" || !folderName) return null;

  return (
    <Badge
      variant="outline"
      className="text-xs border-blue-200 text-blue-700 bg-blue-50"
    >
      <FolderOpen className="h-3 w-3 mr-1" />
      Inherited from {folderName}
    </Badge>
  );
}
