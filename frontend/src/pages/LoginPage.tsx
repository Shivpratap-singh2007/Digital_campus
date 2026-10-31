import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { fetchCsrfToken } from '../api/client';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Proactively bootstrap CSRF session cookie in background upon viewing login page
    fetchCsrfToken();
  }, []);

  const handleQuickLogin = (demoEmail: string, demoPw: string) => {
    setEmail(demoEmail);
    setPassword(demoPw);
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return; // Prevent duplicate submissions
    setError('');
    setLoading(true);

    try {
      await fetchCsrfToken();
      const user = await login(email, password);
      const defaultDashboard = user.is_handler ? '/admin/dashboard' : '/';
      const from = (location.state as any)?.from?.pathname || defaultDashboard;
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="row justify-content-center py-4">
      <div className="col-11 col-sm-9 col-md-6 col-lg-5 col-xl-4">
        <div className="cv-card">
          <div className="cv-card-body p-4">
            <div className="text-center mb-4">
              <h4 className="fw-bold text-dark mb-1">Sign In</h4>
              <p className="text-muted small mb-0">Enter your verified campus credentials</p>
            </div>

            {error && (
              <div className="alert alert-danger py-2 small mb-3" role="alert">
                <i className="bi bi-exclamation-circle me-1"></i>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label">College Email</label>
                <input
                  type="email"
                  className="form-control"
                  placeholder="e.g. student@campus.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="mb-4">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <button type="submit" className="btn btn-primary w-100 py-2" disabled={loading}>
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                    Authenticating...
                  </>
                ) : (
                  'Sign In'
                )}
              </button>

              {/* 1-Click Quick Demo Login Section */}
              <div className="mt-3 p-3 rounded" style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <span className="small text-muted fw-semibold d-block mb-2 text-center">
                  ⚡ 1-Click Quick Demo Login:
                </span>
                <div className="d-flex flex-column gap-2">
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary d-flex align-items-center justify-content-between px-3"
                    onClick={() => handleQuickLogin('student.aarav@campus.edu', 'StudentPass123!')}
                  >
                    <span>🎓 Student (Aarav)</span>
                    <span className="badge bg-primary-subtle text-primary">Autofill</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger d-flex align-items-center justify-content-between px-3"
                    onClick={() => handleQuickLogin('admin@campus.edu', 'AdminPass123!')}
                  >
                    <span>🛡️ Administrator</span>
                    <span className="badge bg-danger-subtle text-danger">Autofill</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary d-flex align-items-center justify-content-between px-3"
                    onClick={() => handleQuickLogin('handler@campus.edu', 'HandlerPass123!')}
                  >
                    <span>🔧 Operational Handler</span>
                    <span className="badge bg-secondary-subtle text-secondary">Autofill</span>
                  </button>
                </div>
              </div>
            </form>

            <div className="text-center mt-4 pt-3 border-top">
              <p className="mb-1 text-muted small">
                Need an account?{' '}
                <Link to="/register" className="text-primary fw-medium text-decoration-none">
                  Register here
                </Link>
              </p>
              <p className="mb-0 text-muted small">
                Unverified email?{' '}
                <Link to="/verify-email" className="text-secondary text-decoration-none">
                  Verification center
                </Link>
              </p>
            </div>
          </div>
        </div>

        {/* Campus Support Notice */}
        <div className="cv-card mt-3 bg-white">
          <div className="cv-card-body p-3 text-center">
            <div className="d-flex align-items-center justify-content-center gap-2 mb-1">
              <i className="bi bi-shield-lock text-primary"></i>
              <span className="fw-semibold text-secondary small">Authorized Campus Access Only</span>
            </div>
            <p className="text-muted small mb-0">
              For account assistance or role provisioning, please contact the campus IT Operations Desk.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
