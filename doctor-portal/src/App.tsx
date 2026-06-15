import { lazy, Suspense, type ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useQuery } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { isAuthenticated } from './lib/auth';
import { apiFetch } from './lib/api';

// Route-split chunks
const Login = lazy(() => import('./routes/Login').then(m => ({ default: m.Login })));
const ForgotPassword = lazy(() => import('./routes/ForgotPassword').then(m => ({ default: m.ForgotPassword })));
const Dashboard = lazy(() => import('./routes/Dashboard').then(m => ({ default: m.Dashboard })));
const PatientList = lazy(() => import('./routes/patients/PatientList').then(m => ({ default: m.PatientList })));
const PatientDetail = lazy(() => import('./routes/patients/PatientDetail').then(m => ({ default: m.PatientDetail })));
const LabReportAnnotate = lazy(() => import('./routes/patients/LabReportAnnotate').then(m => ({ default: m.LabReportAnnotate })));
const ConsultationList = lazy(() => import('./routes/consultations/ConsultationList').then(m => ({ default: m.ConsultationList })));
const ConsultationDetail = lazy(() => import('./routes/consultations/ConsultationDetail').then(m => ({ default: m.ConsultationDetail })));
const Profile = lazy(() => import('./routes/Profile').then(m => ({ default: m.Profile })));
const Schedule = lazy(() => import('./routes/Schedule').then(m => ({ default: m.Schedule })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

function ProtectedShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Fetch doctor name for sidebar
  const { data } = useQuery({
    queryKey: ['doctor-me'],
    queryFn: () => apiFetch<{ name: string }>('/v1/doctor/me'),
    staleTime: 300_000,
  });

  return (
    <Layout doctorName={data?.name}>
      <Suspense fallback={
        <div className="flex items-center justify-center h-64">
          <p className="font-body text-body text-stone">Loading…</p>
        </div>
      }>
        {children}
      </Suspense>
    </Layout>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={null}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />

            <Route path="/" element={<ProtectedShell><Dashboard /></ProtectedShell>} />
            <Route path="/dashboard" element={<ProtectedShell><Dashboard /></ProtectedShell>} />

            <Route path="/patients" element={<ProtectedShell><PatientList /></ProtectedShell>} />
            <Route path="/patients/:id" element={<ProtectedShell><PatientDetail /></ProtectedShell>} />
            <Route path="/patients/:id/lab-reports/:reportId" element={<ProtectedShell><LabReportAnnotate /></ProtectedShell>} />

            <Route
              path="/consultations/today"
              element={<ProtectedShell><ConsultationList filter="today" /></ProtectedShell>}
            />
            <Route
              path="/consultations/upcoming"
              element={<ProtectedShell><ConsultationList filter="upcoming" /></ProtectedShell>}
            />
            <Route
              path="/consultations/history"
              element={<ProtectedShell><ConsultationList filter="history" /></ProtectedShell>}
            />
            <Route path="/consultations/:id" element={<ProtectedShell><ConsultationDetail /></ProtectedShell>} />

            <Route path="/schedule" element={<ProtectedShell><Schedule /></ProtectedShell>} />
            <Route path="/profile" element={<ProtectedShell><Profile /></ProtectedShell>} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
