import { FinanceView } from "@/components/FinanceView";
import { RequirePermission } from "@/components/RequirePermission";

export default function FinancePage() {
  return (
    <RequirePermission permission="finance:read">
      <FinanceView />
    </RequirePermission>
  );
}
