import { MissionsView } from "@/components/MissionsView";
import { RequirePermission } from "@/components/RequirePermission";

export default function MissionsPage() {
  return (
    <RequirePermission permission="orchestration:read">
      <MissionsView />
    </RequirePermission>
  );
}
