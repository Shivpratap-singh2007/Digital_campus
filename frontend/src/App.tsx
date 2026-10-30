import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { EmergencyBanner } from './components/EmergencyBanner';
import { Navbar } from './components/Navbar';

import { HomePage } from './pages/HomePage';
import { PublicIssuesPage } from './pages/PublicIssuesPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { MyComplaintsPage } from './pages/MyComplaintsPage';
import { NewComplaintPage } from './pages/NewComplaintPage';
import { ComplaintDetailPage } from './pages/ComplaintDetailPage';
import { QueuePage } from './pages/QueuePage';
import { CreateIssuePage } from './pages/CreateIssuePage';
import { IssueDetailPage } from './pages/IssueDetailPage';
import { DashboardPage } from './pages/DashboardPage';
import { AuditLogPage } from './pages/AuditLogPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode; requireHandler?: boolean; requireAdmin?: boolean }> = ({
  children,
  requireHandler,
  requireAdmin,
}) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="p-5 text-center text-muted">Checking authentication...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && !user.is_admin) {
    return <Navigate to="/" replace />;
  }

  if (requireHandler && !user.is_handler) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <EmergencyBanner />
        <Navbar />

        <main className="main-container py-4">
          <div className="container">
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<HomePage />} />
              <Route path="/public-issues" element={<PublicIssuesPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/verify-email" element={<VerifyEmailPage />} />

              {/* Verified User Routes */}
              <Route
                path="/my-complaints"
                element={
                  <ProtectedRoute>
                    <MyComplaintsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/new-complaint"
                element={
                  <ProtectedRoute>
                    <NewComplaintPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/complaints/:id"
                element={
                  <ProtectedRoute>
                    <ComplaintDetailPage />
                  </ProtectedRoute>
                }
              />

              {/* Handler & Admin Routes */}
              <Route
                path="/admin/queue"
                element={
                  <ProtectedRoute requireHandler>
                    <QueuePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/create-issue"
                element={
                  <ProtectedRoute requireHandler>
                    <CreateIssuePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/issues/:id"
                element={
                  <ProtectedRoute requireHandler>
                    <IssueDetailPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/dashboard"
                element={
                  <ProtectedRoute requireHandler>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/audit-log"
                element={
                  <ProtectedRoute requireAdmin>
                    <AuditLogPage />
                  </ProtectedRoute>
                }
              />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>

        <footer className="footer mt-auto py-3">
          <div className="container text-center">
            <p className="mb-0 text-muted">
              <strong>CampusVoice</strong> — Campus Complaints with Verified Resolution Feedback
            </p>
          </div>
        </footer>
      </BrowserRouter>
    </AuthProvider>
  );
};

