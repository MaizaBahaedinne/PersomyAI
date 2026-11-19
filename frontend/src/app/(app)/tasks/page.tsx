import { RequirePermission } from "@/components/RequirePermission";
import { TasksView } from "@/components/TasksView";

export default function TasksPage() {
  return (
    <RequirePermission permission="orchestration:read">
      <TasksView />
    </RequirePermission>
  );
}
