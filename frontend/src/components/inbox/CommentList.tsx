import { Avatar, AvatarFallback } from "../ui/avatar";
import type { CommentResponse } from "../../api/inbox";

interface CommentListProps {
  comments: CommentResponse[];
}

export function CommentList({ comments }: CommentListProps) {
  if (comments.length === 0) {
    return <p className="text-sm text-muted-foreground">No comments yet.</p>;
  }

  return (
    <div className="space-y-3">
      {comments.map((comment) => (
        <div key={comment.id} className="flex gap-3">
          <Avatar className="h-7 w-7 shrink-0">
            <AvatarFallback className="text-xs">
              {comment.user_id.slice(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="text-sm">{comment.content}</div>
            <div className="text-xs text-muted-foreground">
              {new Date(comment.created_at).toLocaleString()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
