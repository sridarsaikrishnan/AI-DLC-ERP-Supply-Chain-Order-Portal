import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";

const RESELLER_NAV = [{ to: "/notifications", label: "Notifications" }];
const OPERATOR_NAV = [
  { to: "/admin/orders", label: "Orders" },
  { to: "/admin/subsidiaries", label: "Subsidiaries" },
  { to: "/admin/connections", label: "ERP connections" },
  { to: "/admin/tenants", label: "Resellers" },
  { to: "/admin/failed-messages", label: "Failed messages" },
];

function crumbFor(pathname: string): string {
  if (/^\/orders\/[^/]+\/events$/.test(pathname)) return "Notifications / Order events";
  if (/^\/orders\/[^/]+$/.test(pathname)) return "Notifications / Order";
  if (pathname.startsWith("/notifications")) return "Notifications";
  if (pathname.startsWith("/admin/orders")) return "Operator / Orders";
  if (pathname.startsWith("/admin/subsidiaries")) return "Operator / Subsidiaries";
  if (pathname.startsWith("/admin/connections")) return "Operator / ERP connections";
  if (pathname.startsWith("/admin/tenants")) return "Operator / Resellers";
  if (pathname.startsWith("/admin/failed-messages")) return "Operator / Failed messages";
  return "";
}

export function AppShell() {
  const { tenantId, roles, signOut } = useAuth();
  const location = useLocation();
  const isOperator = roles.includes("OPERATOR");
  const isReseller = roles.includes("RESELLER") || !isOperator;
  const navItems = [...(isReseller ? RESELLER_NAV : []), ...(isOperator ? OPERATOR_NAV : [])];

  return (
    <div className="app">
      <aside className="side">
        <div>
          <div className="brandmark">ERP Platform</div>
          <div className="role">{isOperator ? "Operator admin" : "Reseller portal"}</div>
        </div>
        <nav className="nav" aria-label="Main">
          {navItems.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => `nav-item ${isActive ? "is-active" : ""}`}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="side-note">{tenantId ? `Signed in to tenant ${tenantId}` : "Signed in"}</div>
      </aside>
      <div className="main">
        <header className="top">
          <div className="crumb">{crumbFor(location.pathname)}</div>
          <div className="user">
            <span>{roles.join(", ") || "User"}</span>
            <button className="erp-btn erp-btn--ghost erp-btn--sm" type="button" onClick={signOut}>
              Sign out
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
