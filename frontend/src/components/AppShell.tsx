import React, { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../lib/api";

export const AppShell: React.FC = () => {
  const [serverStatus, setServerStatus] = useState<"live" | "waking" | "offline">("live");
  const [modelName, setModelName] = useState<string>("gemini-3.5-flash-lite");
  const location = useLocation();

  useEffect(() => {
    let isMounted = true;
    const checkServer = async () => {
      try {
        const healthPromise = api.getHealth();
        // Check timeout for waking
        const timer = setTimeout(() => {
          if (isMounted) setServerStatus("waking");
        }, 2000);

        await healthPromise;
        clearTimeout(timer);
        if (isMounted) setServerStatus("live");
      } catch {
        if (isMounted) setServerStatus("offline");
      }
    };

    // Load config for model name
    api
      .getConfig()
      .then((cfg) => {
        if (isMounted && cfg.model) {
          setModelName(cfg.model);
        }
      })
      .catch(() => {});

    checkServer();
    const interval = setInterval(checkServer, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navLinks = [
    { to: "/", label: "Invoices" },
    { to: "/new", label: "Process invoice" },
    { to: "/purchase-orders", label: "Purchase orders" },
    { to: "/rules", label: "Rules" },
  ];

  return (
    <div className="min-h-screen bg-[var(--paper)] text-[var(--ink)] flex flex-col font-sans">
      {/* Top Navigation Bar: 56px */}
      <header className="h-[56px] bg-[var(--surface)] border-b border-[var(--line)] sticky top-0 z-40 px-4 sm:px-6 lg:px-8">
        <div className="max-w-[1240px] mx-auto h-full flex items-center justify-between">
          <div className="flex items-center gap-8">
            {/* Wordmark */}
            <Link
              to="/"
              className="flex items-center gap-1.5 text-[16px] font-heading font-bold tracking-[-0.01em] text-[var(--ink)] hover:opacity-90 select-none no-underline"
            >
              <span>Kestrel AP</span>
              <span className="text-[var(--ink-3)] font-normal">·</span>
              <span className="text-[var(--ink-3)] font-normal text-[14px]">Invoice desk</span>
            </Link>

            {/* Nav links */}
            <nav className="hidden md:flex items-center gap-6 h-[56px]">
              {navLinks.map((link) => {
                const isActive =
                  link.to === "/"
                    ? location.pathname === "/"
                    : location.pathname.startsWith(link.to);

                return (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    className={`h-[56px] flex items-center text-[15px] font-medium transition-colors select-none relative focus-visible:outline-2 focus-visible:outline-[var(--focus)] ${
                      isActive
                        ? "text-[var(--ink)] font-semibold"
                        : "text-[var(--ink-3)] hover:text-[var(--ink)]"
                    }`}
                  >
                    <span>{link.label}</span>
                    {isActive && (
                      <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[var(--ink)]" />
                    )}
                  </NavLink>
                );
              })}
            </nav>
          </div>

          {/* Right Status */}
          <div className="flex items-center gap-3">
            {/* Server Status Dot */}
            <div className="flex items-center gap-1.5 text-[12px] font-sans font-medium text-[var(--ink-2)] select-none">
              <span
                className={`w-2 h-2 rounded-full ${
                  serverStatus === "live"
                    ? "bg-[#1B6B43]"
                    : serverStatus === "waking"
                    ? "bg-[#8A5A00] animate-pulse"
                    : "bg-[#A3182A]"
                }`}
              />
              <span className="hidden sm:inline">
                {serverStatus === "live"
                  ? "Live"
                  : serverStatus === "waking"
                  ? "Waking server"
                  : "Offline"}
              </span>
            </div>

            <span className="text-[var(--line)] hidden sm:inline">|</span>

            {/* Model Name */}
            <span className="font-mono text-[11px] text-[var(--ink-3)] hidden sm:inline bg-[var(--surface-sunken)] px-2 py-0.5 rounded-[4px] border border-[var(--line)]">
              {modelName}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-[1240px] mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
        <Outlet />
      </main>
    </div>
  );
};
