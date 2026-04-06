import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Textarea } from "../ui/textarea";
import { Button } from "../ui/button";
import { addComment } from "../../api/inbox";

interface CommentComposeProps {
  workItemId: string;
}

export function CommentCompose({ workItemId }: CommentComposeProps) {
  const [content, setContent] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => addComment(workItemId, content),
    onSuccess: () => {
      setContent("");
      queryClient.invalidateQueries({
        queryKey: ["inbox", workItemId, "comments"],
      });
      queryClient.invalidateQueries({
        queryKey: ["inbox", workItemId],
      });
      toast.success("Comment added");
    },
    onError: (error: Error) => {
      toast.error("Action failed: " + error.message);
    },
  });

  return (
    <div className="space-y-2">
      <Textarea
        placeholder="Write a comment..."
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="min-h-[60px]"
      />
      <Button
        variant="outline"
        size="sm"
        disabled={content.trim() === "" || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "Adding..." : "Add Comment"}
      </Button>
    </div>
  );
}
