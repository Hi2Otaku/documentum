import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PenTool, ShieldCheck, ShieldX } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
import { Textarea } from "../ui/textarea";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import {
  fetchSignatures,
  signDocumentVersion,
  verifySignature,
  type SignatureResponse,
  type SignatureVerifyResponse,
} from "../../api/documents";

interface SignaturePanelProps {
  documentId: string;
  versionId: string | null;
}

export function SignaturePanel({ documentId, versionId }: SignaturePanelProps) {
  const [signDialogOpen, setSignDialogOpen] = useState(false);
  const [verifyResult, setVerifyResult] = useState<{
    sigId: string;
    result: SignatureVerifyResponse;
  } | null>(null);
  const [certificatePem, setCertificatePem] = useState("");
  const [privateKeyPem, setPrivateKeyPem] = useState("");
  const [reason, setReason] = useState("");
  const queryClient = useQueryClient();

  const { data: signatures = [], isLoading } = useQuery({
    queryKey: ["signatures", documentId, versionId],
    queryFn: () => fetchSignatures(documentId, versionId!),
    enabled: !!documentId && !!versionId,
  });

  const signMutation = useMutation({
    mutationFn: () =>
      signDocumentVersion(documentId, versionId!, {
        certificate_pem: certificatePem,
        private_key_pem: privateKeyPem,
        reason: reason || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["signatures", documentId, versionId],
      });
      setSignDialogOpen(false);
      setCertificatePem("");
      setPrivateKeyPem("");
      setReason("");
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (signatureId: string) =>
      verifySignature(documentId, versionId!, signatureId),
    onSuccess: (result, signatureId) => {
      setVerifyResult({ sigId: signatureId, result });
    },
  });

  if (!versionId) {
    return (
      <div>
        <h4 className="text-sm font-medium flex items-center gap-1 mb-2">
          <PenTool className="h-4 w-4" /> Digital Signatures
        </h4>
        <p className="text-sm text-muted-foreground">
          Select a version to view signatures.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div>
        <h4 className="text-sm font-medium flex items-center gap-1 mb-2">
          <PenTool className="h-4 w-4" /> Digital Signatures
        </h4>
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium flex items-center gap-1">
          <PenTool className="h-4 w-4" /> Digital Signatures
          {signatures.length > 0 && (
            <span className="text-xs text-muted-foreground ml-1">
              ({signatures.length})
            </span>
          )}
        </h4>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSignDialogOpen(true)}
        >
          Sign Document
        </Button>
      </div>

      {signatures.length === 0 ? (
        <p className="text-sm text-muted-foreground py-2">No signatures</p>
      ) : (
        <div className="space-y-2">
          {signatures.map((sig: SignatureResponse) => (
            <div
              key={sig.id}
              className="border rounded-md p-3 space-y-1"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">{sig.signer_cn}</span>
                <Badge
                  variant={sig.is_valid ? "default" : "destructive"}
                  className={
                    sig.is_valid
                      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                      : ""
                  }
                >
                  {sig.is_valid ? "Valid" : "Invalid"}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground">
                {new Date(sig.signed_at).toLocaleString()} &middot;{" "}
                {sig.algorithm}
              </div>
              {sig.reason && (
                <div className="text-xs text-muted-foreground italic">
                  Reason: {sig.reason}
                </div>
              )}
              <div className="flex items-center gap-2 pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => verifyMutation.mutate(sig.id)}
                  disabled={verifyMutation.isPending}
                >
                  Verify
                </Button>
                {verifyResult?.sigId === sig.id && (
                  <div className="flex items-center gap-1 text-xs">
                    {verifyResult.result.is_valid ? (
                      <ShieldCheck className="h-3.5 w-3.5 text-green-600" />
                    ) : (
                      <ShieldX className="h-3.5 w-3.5 text-red-600" />
                    )}
                    <span
                      className={
                        verifyResult.result.is_valid
                          ? "text-green-700"
                          : "text-red-700"
                      }
                    >
                      {verifyResult.result.detail}
                    </span>
                    {!verifyResult.result.content_hash_match && (
                      <span className="text-red-600 ml-1">
                        (hash mismatch)
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sign Document Dialog */}
      <Dialog open={signDialogOpen} onOpenChange={setSignDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Sign Document</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="certificate_pem">
                X.509 Certificate (PEM)
              </Label>
              <Textarea
                id="certificate_pem"
                placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                value={certificatePem}
                onChange={(e) => setCertificatePem(e.target.value)}
                rows={5}
                className="font-mono text-xs"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="private_key_pem">Private Key (PEM)</Label>
              <Textarea
                id="private_key_pem"
                placeholder="-----BEGIN PRIVATE KEY-----&#10;...&#10;-----END PRIVATE KEY-----"
                value={privateKeyPem}
                onChange={(e) => setPrivateKeyPem(e.target.value)}
                rows={5}
                className="font-mono text-xs"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sign_reason">Reason (optional)</Label>
              <Input
                id="sign_reason"
                placeholder="e.g. Approved for release"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setSignDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={() => signMutation.mutate()}
                disabled={
                  signMutation.isPending ||
                  !certificatePem.trim() ||
                  !privateKeyPem.trim()
                }
              >
                {signMutation.isPending ? "Signing..." : "Sign"}
              </Button>
            </div>
            {signMutation.isError && (
              <p className="text-sm text-destructive">
                {(signMutation.error as Error).message}
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
