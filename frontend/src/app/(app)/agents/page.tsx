import { AgentsView } from "@/components/AgentsView";
import { RequirePermission } from "@/components/RequirePermission";

export default function AgentsPage() {
  return (
    <RequirePermission permission="agents:read">
      <AgentsView />
    </RequirePermission>
  );
}
