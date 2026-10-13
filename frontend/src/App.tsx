import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { PublicLayout } from "@/components/PublicLayout";
import { StaffHome, StaffLayout } from "@/components/StaffLayout";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/lib/auth";
import NotFound from "@/pages/NotFound";
import Apply from "@/pages/public/Apply";
import Home from "@/pages/public/Home";
import ChildDetail from "@/pages/parent/ChildDetail";
import Children from "@/pages/parent/Children";
import ParentLogin from "@/pages/parent/Login";
import ParentNotices from "@/pages/parent/Notices";
import { ParentLayout } from "@/pages/parent/ParentLayout";
import Pay from "@/pages/public/Pay";
import Track from "@/pages/public/Track";
import Dashboard from "@/pages/staff/admin/Dashboard";
import Setup from "@/pages/staff/admin/Setup";
import Users from "@/pages/staff/admin/Users";
import ApplicationDetail from "@/pages/staff/ApplicationDetail";
import ChangePassword from "@/pages/staff/ChangePassword";
import Concessions from "@/pages/staff/fees/Concessions";
import FeeSetup from "@/pages/staff/fees/FeeSetup";
import InvoiceDetail from "@/pages/staff/fees/InvoiceDetail";
import Invoices from "@/pages/staff/fees/Invoices";
import FeeReports from "@/pages/staff/fees/Reports";
import UpiPayments from "@/pages/staff/fees/UpiPayments";
import Applications from "@/pages/staff/Applications";
import Login from "@/pages/staff/Login";
import Notices from "@/pages/staff/Notices";
import StudentDetail from "@/pages/staff/StudentDetail";
import Students from "@/pages/staff/Students";
import WhatsApp from "@/pages/staff/WhatsApp";
import Attendance from "@/pages/staff/teaching/Attendance";
import Marks from "@/pages/staff/teaching/Marks";
import MarksEntry from "@/pages/staff/teaching/MarksEntry";
import MyClasses from "@/pages/staff/teaching/MyClasses";

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
              <Route path="/parent/login" element={<ParentLogin />} />
            </Route>
            <Route path="/parent" element={<ParentLayout />}>
              <Route index element={<Children />} />
              <Route path="children/:id" element={<ChildDetail />} />
              <Route path="notices" element={<ParentNotices />} />
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
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="classes" element={<MyClasses />} />
              <Route path="classes/:sectionId/attendance" element={<Attendance />} />
              <Route path="classes/:sectionId/marks" element={<Marks />} />
              <Route path="assessments/:id" element={<MarksEntry />} />
              <Route path="notices" element={<Notices />} />
              <Route path="setup" element={<Setup />} />
              <Route path="users" element={<Users />} />
              <Route path="password" element={<ChangePassword />} />
              <Route path="whatsapp" element={<WhatsApp />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
