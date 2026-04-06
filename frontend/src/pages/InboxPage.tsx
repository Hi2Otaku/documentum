import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export function InboxPage() {
  return (
    <div className="flex items-start justify-center pt-24">
      <Card className="w-full max-w-[400px] mx-auto">
        <CardHeader className="text-center">
          <CardTitle className="text-xl font-semibold">Coming Soon</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center">
            This page is under construction. Check back after the next update.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
