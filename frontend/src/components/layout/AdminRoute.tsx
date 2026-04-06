import { Navigate, Outlet } from "react-router";
import { useAuthStore } from "../../stores/authStore";

export function AdminRoute() {
  const isSuperuser = useAuthStore((s) => s.isSuperuser);

  if (!isSuperuser) {
    return <Navigate to="/inbox" replace />;
  }

  return <Outlet />;
}
