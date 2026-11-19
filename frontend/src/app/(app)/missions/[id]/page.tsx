import { MissionDetailView } from "@/components/MissionDetailView";
import { RequirePermission } from "@/components/RequirePermission";

export default async function MissionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequirePermission permission="orchestration:read">
      <MissionDetailView id={id} />
    </RequirePermission>
  );
}
