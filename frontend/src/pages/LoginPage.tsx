import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(email, password);
      const from = (location.state as any)?.from?.pathname || (user.is_handler ? '/admin/queue' : '/my-complaints');
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

        {/* Prototype Demo Accounts Helper */}
        <div className="cv-card mt-3 bg-white">
          <div className="cv-card-body p-3">
            <div className="d-flex align-items-center gap-2 mb-2">
              <i className="bi bi-info-circle text-muted"></i>
              <span className="fw-semibold text-secondary small">Demo Seed Credentials</span>
            </div>
            <div className="small text-muted d-flex flex-column gap-1">
              <div>
                <strong>Admin:</strong> <code>admin@campus.edu</code> / <code>AdminPass123!</code>
              </div>
              <div>
                <strong>Handler:</strong> <code>handler@campus.edu</code> / <code>HandlerPass123!</code>
              </div>
              <div>
                <strong>Student:</strong> <code>student.aarav@campus.edu</code> / <code>StudentPass123!</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
