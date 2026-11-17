import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/Dashboard";
import { NewRunPage } from "./pages/NewRun";
import { RunDetailPage } from "./pages/RunDetail";
import { PurchaseOrdersPage } from "./pages/PurchaseOrders";
import { RulesPage } from "./pages/Rules";
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
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="runs/new" element={<NewRunPage />} />
            <Route path="runs/:id" element={<RunDetailPage />} />
            <Route path="purchase-orders" element={<PurchaseOrdersPage />} />
            <Route path="rules" element={<RulesPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
