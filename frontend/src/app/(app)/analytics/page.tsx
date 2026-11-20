import { AnalyticsView } from "@/components/AnalyticsView";
import { RequirePermission } from "@/components/RequirePermission";

export default function AnalyticsPage() {
  return (
    <RequirePermission permission="analytics:read">
      <AnalyticsView />
    </RequirePermission>
  );
}
