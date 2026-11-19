import { RequirePermission } from "@/components/RequirePermission";
import { SettingsView } from "@/components/SettingsView";

export default function SettingsPage() {
  return (
    <RequirePermission permission="settings:read">
      <SettingsView />
    </RequirePermission>
  );
}
