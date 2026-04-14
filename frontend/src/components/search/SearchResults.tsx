import { FileText } from "lucide-react";
import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
import type { SearchResult } from "../../api/search";

interface SearchResultsProps {
  results: SearchResult[];
  isLoading: boolean;
  query: string;
}

function RelevanceBar({ rank }: { rank: number }) {
  // Rank is a ts_rank score (typically 0-1 range, can exceed 1).
  // Normalize to a percentage: clamp to 0-1 range then scale.
  const pct = Math.min(Math.max(rank, 0), 1) * 100;
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${Math.max(pct, 5)}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground">{rank.toFixed(2)}</span>
    </div>
  );
}

function lifecycleVariant(
  state: string,
): "default" | "secondary" | "outline" | "destructive" {
  switch (state) {
    case "approved":
      return "default";
    case "active":
      return "secondary";
    case "draft":
      return "outline";
    case "obsolete":
    case "archived":
      return "destructive";
    default:
      return "outline";
  }
}

export function SearchResults({ results, isLoading, query }: SearchResultsProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4 space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-12 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!query) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
        <FileText className="h-12 w-12 mb-4" />
        <h3 className="text-lg font-semibold">Search documents</h3>
        <p className="text-sm mt-1">
          Enter a keyword to search across document content and metadata.
        </p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
        <FileText className="h-12 w-12 mb-4" />
        <h3 className="text-lg font-semibold">No results found</h3>
        <p className="text-sm mt-1">
          Try different keywords or adjust your filters.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {results.map((result) => (
        <Card
          key={result.id}
          className="hover:bg-accent/30 transition-colors cursor-pointer"
          onClick={() => {
            window.location.href = `/documents?id=${result.id}`;
          }}
        >
          <CardContent className="p-4">
            {/* Title and badges row */}
            <div className="flex items-start justify-between gap-2 mb-1">
              <h4 className="text-sm font-semibold leading-tight">
                {result.title}
              </h4>
              <div className="flex items-center gap-1.5 shrink-0">
                {result.document_type_name && (
                  <Badge variant="secondary">{result.document_type_name}</Badge>
                )}
                {result.lifecycle_state && (
                  <Badge variant={lifecycleVariant(result.lifecycle_state)}>
                    {result.lifecycle_state}
                  </Badge>
                )}
              </div>
            </div>

            {/* Author and filename */}
            <div className="text-xs text-muted-foreground mb-2">
              {result.author && <span>{result.author}</span>}
              {result.author && result.filename && <span> &middot; </span>}
              <span>{result.filename}</span>
            </div>

            {/* Snippet with highlighted matches */}
            {result.headline && (
              <div
                className="text-sm text-muted-foreground leading-relaxed [&_mark]:bg-yellow-200 [&_mark]:text-foreground [&_mark]:px-0.5 [&_mark]:rounded-sm"
                dangerouslySetInnerHTML={{ __html: result.headline }}
              />
            )}

            {/* Relevance indicator */}
            <div className="mt-2">
              <RelevanceBar rank={result.rank} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
