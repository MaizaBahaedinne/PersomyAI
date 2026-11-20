import { CrmView } from "@/components/CrmView";
import { RequirePermission } from "@/components/RequirePermission";

export default function CrmPage() {
  return (
    <RequirePermission permission="crm:read">
      <CrmView />
    </RequirePermission>
  );
}
