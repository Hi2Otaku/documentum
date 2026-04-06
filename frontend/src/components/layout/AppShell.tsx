import { useEffect } from "react";
import { Outlet } from "react-router";
import { useAuthStore } from "../../stores/authStore";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const loadProfile = useAuthStore((s) => s.loadProfile);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  return (
    <Sidebar>
      <Outlet />
    </Sidebar>
  );
}
