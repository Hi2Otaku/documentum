import { Badge } from "../ui/badge";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

interface RenditionStatusBadgeProps {
  status: "pending" | "ready" | "failed";
  type: "pdf" | "thumbnail";
}

export function RenditionStatusBadge({ status, type }: RenditionStatusBadgeProps) {
  switch (status) {
    case "pending":
      return (
        <Badge variant="secondary">
          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          Generating...
        </Badge>
      );
    case "ready":
      return (
        <Badge variant="default">
          <CheckCircle className="h-3 w-3 mr-1" />
          {type === "pdf" ? "PDF Ready" : "Thumbnail Ready"}
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="destructive">
          <XCircle className="h-3 w-3 mr-1" />
          Failed
        </Badge>
      );
  }
}
