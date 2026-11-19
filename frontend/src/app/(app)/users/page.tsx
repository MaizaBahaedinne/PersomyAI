import { RequirePermission } from "@/components/RequirePermission";
import { UsersView } from "@/components/UsersView";

export default function UsersPage() {
  return (
    <RequirePermission permission="users:read">
      <UsersView />
    </RequirePermission>
  );
}
