import { RequirePermission } from "@/components/RequirePermission";
import { TaskDetailView } from "@/components/TaskDetailView";

export default async function TaskDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequirePermission permission="orchestration:read">
      <TaskDetailView id={id} />
    </RequirePermission>
  );
}
