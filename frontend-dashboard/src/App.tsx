import { BrowserRouter, Routes, Route, Outlet } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import { Menu, X } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { ToastProvider } from "@/components/Toast";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";

const HomePage = lazy(() => import("@/pages/HomePage"));
const LoginPage = lazy(() => import("@/pages/LoginPage"));
const RegisterPage = lazy(() => import("@/pages/RegisterPage"));
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const ClientsPage = lazy(() => import("@/pages/ClientsPage"));
const ClientDetailPage = lazy(() => import("@/pages/ClientDetailPage"));
const AgentsPage = lazy(() => import("@/pages/AgentsPage"));
const AgentDetailPage = lazy(() => import("@/pages/AgentDetailPage"));
const ConversationsPage = lazy(() => import("@/pages/ConversationsPage"));
const ConversationDetailPage = lazy(() => import("@/pages/ConversationDetailPage"));
const LeadsPage = lazy(() => import("@/pages/LeadsPage"));
const LeadDetailPage = lazy(() => import("@/pages/LeadDetailPage"));
const TemplatesPage = lazy(() => import("@/pages/TemplatesPage"));
const TemplateApplyPage = lazy(() => import("@/pages/TemplateApplyPage"));
const LandingPage = lazy(() => import("@/pages/LandingPage"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-black">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
    </div>
  );
}

function AppLayout() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen bg-black text-white overflow-hidden">
      <div className="hidden lg:block h-full">
        <Sidebar />
      </div>

      <div className="lg:hidden absolute top-4 left-4 z-50">
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2.5 glass-card rounded-xl shadow-lg"
        >
          {isMobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setIsMobileMenuOpen(false)} />
          <Sidebar
            className="w-[80vw] max-w-xs shadow-2xl animate-slide-left border-r border-zinc-800"
            onCloseMobile={() => setIsMobileMenuOpen(false)}
          />
        </div>
      )}

      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-5%] right-[-5%] w-[600px] h-[600px] bg-amber-500/[0.02] rounded-full blur-[120px]" />
          <div className="absolute bottom-[-10%] left-[-5%] w-[400px] h-[400px] bg-amber-500/[0.01] rounded-full blur-[100px]" />
        </div>
        <main className="flex-1 overflow-y-auto overflow-x-hidden relative z-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <AuthProvider>
            <Suspense fallback={<Loading />}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/landing/:slug" element={<LandingPage />} />
                <Route element={<ProtectedRoute />}>
                  <Route element={<AppLayout />}>
                    <Route path="/app" element={<DashboardPage />} />
                    <Route path="/app/clients" element={<ClientsPage />} />
                    <Route path="/app/clients/:id" element={<ClientDetailPage />} />
                    <Route path="/app/agents" element={<AgentsPage />} />
                    <Route path="/app/agents/:id" element={<AgentDetailPage />} />
                    <Route path="/app/conversations" element={<ConversationsPage />} />
                    <Route path="/app/conversations/:id" element={<ConversationDetailPage />} />
                    <Route path="/app/leads" element={<LeadsPage />} />
                    <Route path="/app/leads/:id" element={<LeadDetailPage />} />
                    <Route path="/app/templates" element={<TemplatesPage />} />
                    <Route path="/app/templates/:slug/apply" element={<TemplateApplyPage />} />
                    <Route path="/app/profile" element={null} />
                  </Route>
                </Route>
              </Routes>
            </Suspense>
          </AuthProvider>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}
