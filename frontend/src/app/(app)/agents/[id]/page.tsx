import { AgentDetailView } from "@/components/AgentDetailView";
import { RequirePermission } from "@/components/RequirePermission";

export default async function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequirePermission permission="agents:read">
      <AgentDetailView id={id} />
    </RequirePermission>
  );
}
