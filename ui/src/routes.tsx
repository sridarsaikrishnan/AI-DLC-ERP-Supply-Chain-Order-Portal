import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppShell } from "./App";
import { useAuth } from "./auth/AuthContext";
import { LoginPage } from "./features/auth/LoginPage";
import { OrderDetailPage } from "./features/orders/OrderDetailPage";
import { NotificationsPage } from "./features/notifications/NotificationsPage";
import { ConnectionsPage } from "./features/admin/ConnectionsPage";
import { TenantsPage } from "./features/admin/TenantsPage";
import { SubsidiariesPage } from "./features/admin/SubsidiariesPage";
import { OrdersPage as OperatorOrdersPage } from "./features/admin/OrdersPage";
import { OrderDetailPage as OperatorOrderDetailPage } from "./features/admin/OrderDetailPage";
import { FailedMessagesPage } from "./features/admin/FailedMessagesPage";
import { OrderEventsPage } from "./features/events/OrderEventsPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function HomeRedirect() {
  const { roles } = useAuth();
  return <Navigate to={roles.includes("RESELLER") || !roles.includes("OPERATOR") ? "/notifications" : "/admin/orders"} replace />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <HomeRedirect /> },
      { path: "notifications", element: <NotificationsPage /> },
      { path: "orders/:orderId", element: <OrderDetailPage /> },
      { path: "orders/:orderId/events", element: <OrderEventsPage /> },
      { path: "admin/orders", element: <OperatorOrdersPage /> },
      { path: "admin/orders/:orderId", element: <OperatorOrderDetailPage /> },
      { path: "admin/subsidiaries", element: <SubsidiariesPage /> },
      { path: "admin/connections", element: <ConnectionsPage /> },
      { path: "admin/tenants", element: <TenantsPage /> },
      { path: "admin/failed-messages", element: <FailedMessagesPage /> },
    ],
  },
]);
