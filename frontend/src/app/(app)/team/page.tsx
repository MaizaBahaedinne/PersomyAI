import { TeamView } from "@/components/TeamView";
import { RequirePermission } from "@/components/RequirePermission";

export default function TeamPage() {
  return (
    <RequirePermission permission="team:read">
      <TeamView />
    </RequirePermission>
  );
}
