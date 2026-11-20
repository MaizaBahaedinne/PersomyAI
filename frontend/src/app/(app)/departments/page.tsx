import { DepartmentsView } from "@/components/DepartmentsView";
import { RequirePermission } from "@/components/RequirePermission";

export default function DepartmentsPage() {
  return (
    <RequirePermission permission="dashboard:read">
      <DepartmentsView />
    </RequirePermission>
  );
}
