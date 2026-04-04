import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { WorkflowQueryTab } from "../components/query/WorkflowQueryTab";
import { WorkItemQueryTab } from "../components/query/WorkItemQueryTab";
import { DocumentQueryTab } from "../components/query/DocumentQueryTab";

export function QueryPage() {
  return (
    <div className="max-w-[1200px] mx-auto p-8">
      <h1 className="text-lg font-bold mb-6">Query</h1>

      <Tabs defaultValue="workflows">
        <TabsList>
          <TabsTrigger value="workflows">Workflows</TabsTrigger>
          <TabsTrigger value="work-items">Work Items</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>

        <TabsContent value="workflows">
          <WorkflowQueryTab />
        </TabsContent>

        <TabsContent value="work-items">
          <WorkItemQueryTab />
        </TabsContent>

        <TabsContent value="documents">
          <DocumentQueryTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
