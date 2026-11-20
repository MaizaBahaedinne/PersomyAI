import { AutomationsView } from "@/components/AutomationsView";
import { RequirePermission } from "@/components/RequirePermission";

export default function AutomationsPage() {
  return (
    <RequirePermission permission="automations:read">
      <AutomationsView />
    </RequirePermission>
  );
}
