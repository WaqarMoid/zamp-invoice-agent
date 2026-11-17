import React from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { FileText, LayoutDashboard, ShoppingCart, Sliders } from "lucide-react";

export const AppShell: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { label: "Dashboard", path: "/", icon: LayoutDashboard },
    { label: "Process invoice", path: "/runs/new", icon: FileText },
    { label: "Purchase orders", path: "/purchase-orders", icon: ShoppingCart },
    { label: "Rules", path: "/rules", icon: Sliders },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800">
      {/* Top navigation */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center space-x-6">
            <Link to="/" className="flex items-center space-x-2 font-display font-bold text-lg text-slate-900 tracking-tight">
              <span className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-sm shadow-sm">
                K
              </span>
              <span>Kestrel AP <span className="font-normal text-slate-500">· Invoice desk</span></span>
            </Link>
            <nav className="hidden md:flex space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`inline-flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-teal-50 text-teal-800 font-semibold"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    }`}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center space-x-3">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span>
              Live (v0.1)
            </span>
          </div>
        </div>
      </header>

      {/* Main content body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        Kestrel Foods Pvt. Ltd. · Automated AP Invoice Processing · Two-way PO Match
      </footer>
    </div>
  );
};
