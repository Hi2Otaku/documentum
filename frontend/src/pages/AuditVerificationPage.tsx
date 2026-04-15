import { useState } from "react";
import { ShieldCheck, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { useAuthStore } from "../stores/authStore";

interface AuditBreak {
  chain_sequence: number;
  record_id: string;
  type: "content_tampered" | "chain_broken" | "sequence_gap";
  details: string;
}

interface VerifyResult {
  status: "pass" | "fail";
  total_records: number;
  chained_records: number;
  pending_records: number;
  breaks: AuditBreak[];
  verified_at: string;
}

export function AuditVerificationPage() {
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = useAuthStore((s) => s.token);

  async function handleVerify() {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/v1/audit/verify", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `Verification failed (${res.status})`);
      }
      const data: VerifyResult = await res.json();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification request failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Audit Trail Integrity</h1>
        </div>
        <Button onClick={handleVerify} disabled={isLoading}>
          {isLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          Verify Integrity
        </Button>
      </div>

      {/* Error */}
      {error && (
        <Card className="mb-6 border-destructive">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Status Badge */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                {result.status === "pass" ? (
                  <>
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                    <Badge variant="default" className="bg-green-600 text-white text-base px-4 py-1">
                      PASS
                    </Badge>
                  </>
                ) : (
                  <>
                    <XCircle className="h-8 w-8 text-red-600" />
                    <Badge variant="destructive" className="text-base px-4 py-1">
                      FAIL
                    </Badge>
                  </>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Records</p>
                  <p className="text-2xl font-bold">{result.total_records}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Chained Records</p>
                  <p className="text-2xl font-bold">{result.chained_records}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Pending Records</p>
                  <p className="text-2xl font-bold">{result.pending_records}</p>
                  <p className="text-xs text-muted-foreground">Not yet hashed by background worker</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-4">
                Verified at: {new Date(result.verified_at).toLocaleString()}
              </p>
            </CardContent>
          </Card>

          {/* Breaks Table */}
          {result.breaks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-destructive">
                  Chain Breaks ({result.breaks.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Sequence</TableHead>
                      <TableHead>Record ID</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.breaks.map((b, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-mono">{b.chain_sequence}</TableCell>
                        <TableCell className="font-mono text-xs">{b.record_id}</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              b.type === "content_tampered"
                                ? "destructive"
                                : b.type === "chain_broken"
                                  ? "destructive"
                                  : "secondary"
                            }
                          >
                            {b.type.replace("_", " ")}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground max-w-md truncate">
                          {b.details}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Initial state */}
      {!result && !isLoading && !error && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              Click "Verify Integrity" to check the audit trail hash chain for tampering or gaps.
              The verification process recomputes all cryptographic hashes and compares them against
              stored values.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
