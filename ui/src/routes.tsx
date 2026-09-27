import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppShell } from "./App";
import { useAuth } from "./auth/AuthContext";
import { LoginPage } from "./features/auth/LoginPage";
import { OrdersListPage } from "./features/orders/OrdersListPage";
import { OrderDetailPage } from "./features/orders/OrderDetailPage";
import { NewOrderPage } from "./features/orders/NewOrderPage";
import { ConnectionsPage } from "./features/admin/ConnectionsPage";
import { TenantsPage } from "./features/admin/TenantsPage";
import { ItemsPage } from "./features/admin/ItemsPage";
import { OrdersPage as OperatorOrdersPage } from "./features/admin/OrdersPage";
import { OrderDetailPage as OperatorOrderDetailPage } from "./features/admin/OrderDetailPage";
import { FailedMessagesPage } from "./features/admin/FailedMessagesPage";
import { OrderEventsPage } from "./features/events/OrderEventsPage";
import { WebhookEndpointsPage } from "./features/webhooks/WebhookEndpointsPage";
import { DeliveryLogPage } from "./features/webhooks/DeliveryLogPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function HomeRedirect() {
  const { roles } = useAuth();
  return <Navigate to={roles.includes("RESELLER") || !roles.includes("OPERATOR") ? "/orders" : "/admin/orders"} replace />;
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
      { path: "orders", element: <OrdersListPage /> },
      { path: "orders/new", element: <NewOrderPage /> },
      { path: "orders/:orderId", element: <OrderDetailPage /> },
      { path: "orders/:orderId/events", element: <OrderEventsPage /> },
      { path: "delivery-log", element: <DeliveryLogPage /> },
      { path: "webhook-endpoints", element: <WebhookEndpointsPage /> },
      { path: "admin/orders", element: <OperatorOrdersPage /> },
      { path: "admin/orders/:orderId", element: <OperatorOrderDetailPage /> },
      { path: "admin/connections", element: <ConnectionsPage /> },
      { path: "admin/tenants", element: <TenantsPage /> },
      { path: "admin/items", element: <ItemsPage /> },
      { path: "admin/failed-messages", element: <FailedMessagesPage /> },
    ],
  },
]);
