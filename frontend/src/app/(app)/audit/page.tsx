import { AuditView } from "@/components/AuditView";
import { RequirePermission } from "@/components/RequirePermission";

export default function AuditPage() {
  return (
    <RequirePermission permission="audit:read">
      <AuditView />
    </RequirePermission>
  );
}
