import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "./components/Toast";
import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/Dashboard";
import { NewRunPage } from "./pages/NewRun";
import { RunDetailPage } from "./pages/RunDetail";
import { PurchaseOrdersPage } from "./pages/PurchaseOrders";
import { RulesPage } from "./pages/Rules";
import { Gallery } from "./pages/Gallery";
import { NotFoundPage } from "./pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="new" element={<NewRunPage />} />
              <Route path="runs/new" element={<Navigate to="/new" replace />} />
              <Route path="runs/:id" element={<RunDetailPage />} />
              <Route path="purchase-orders" element={<PurchaseOrdersPage />} />
              <Route path="rules" element={<RulesPage />} />
              <Route path="__gallery" element={<Gallery />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
};

export default App;
