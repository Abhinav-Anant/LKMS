import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { PublicLayout } from "@/components/PublicLayout";
import { StaffHome, StaffLayout } from "@/components/StaffLayout";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/lib/auth";
import NotFound from "@/pages/NotFound";
import Apply from "@/pages/public/Apply";
import Home from "@/pages/public/Home";
import Pay from "@/pages/public/Pay";
import Track from "@/pages/public/Track";
import ApplicationDetail from "@/pages/staff/ApplicationDetail";
import Concessions from "@/pages/staff/fees/Concessions";
import FeeSetup from "@/pages/staff/fees/FeeSetup";
import InvoiceDetail from "@/pages/staff/fees/InvoiceDetail";
import Invoices from "@/pages/staff/fees/Invoices";
import FeeReports from "@/pages/staff/fees/Reports";
import UpiPayments from "@/pages/staff/fees/UpiPayments";
import Applications from "@/pages/staff/Applications";
import Login from "@/pages/staff/Login";
import StudentDetail from "@/pages/staff/StudentDetail";
import Students from "@/pages/staff/Students";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthProvider>
          <Toaster />
          <Routes>
            <Route element={<PublicLayout />}>
              <Route path="/" element={<Home />} />
              <Route path="/apply" element={<Apply />} />
              <Route path="/track" element={<Track />} />
              <Route path="/pay/:token" element={<Pay />} />
            </Route>
            <Route path="/staff/login" element={<Login />} />
            <Route path="/staff" element={<StaffLayout />}>
              <Route index element={<StaffHome />} />
              <Route path="applications" element={<Applications />} />
              <Route path="applications/:id" element={<ApplicationDetail />} />
              <Route path="students" element={<Students />} />
              <Route path="students/:id" element={<StudentDetail />} />
              <Route path="fees" element={<Invoices />} />
              <Route path="fees/invoices/:id" element={<InvoiceDetail />} />
              <Route path="fees/upi" element={<UpiPayments />} />
              <Route path="fees/concessions" element={<Concessions />} />
              <Route path="fees/reports" element={<FeeReports />} />
              <Route path="fees/setup" element={<FeeSetup />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
