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
    <div className="row justify-content-center">
      <div className="col-md-5">
        <div className="card card-shadow mt-4">
          <div className="card-body p-4">
            <div className="text-center mb-4">
              <i className="bi bi-person-badge text-primary" style={{ fontSize: '2.5rem' }}></i>
              <h3 className="card-title mt-2">Log In</h3>
              <p className="text-muted small">Sign in with your verified college credentials</p>
            </div>

            {error && (
              <div className="alert alert-danger py-2 small" role="alert">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label fw-semibold">College Email</label>
                <input
                  type="email"
                  className="form-control"
                  placeholder="e.g., student@campus.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="mb-3">
                <label className="form-label fw-semibold">Password</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <div className="d-grid mt-4">
                <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
                  {loading ? 'Logging in...' : 'Log In'}
                </button>
              </div>
            </form>

            <hr className="my-4" />

            <div className="text-center">
              <p className="mb-1 text-muted small">
                Need an account? <Link to="/register">Register here</Link>
              </p>
              <p className="mb-0 text-muted small">
                Haven't verified email? <Link to="/verify-email">Verification help</Link>
              </p>
            </div>
          </div>
        </div>

        {/* Demo Prototype Credentials Card */}
        <div className="card mt-3 bg-light border-0">
          <div className="card-body p-3">
            <h6 className="card-subtitle text-muted mb-2">
              <i className="bi bi-info-circle me-1"></i> Demo Prototype Credentials
            </h6>
            <p className="small text-secondary mb-1">For testing convenience, use the synthetic seed accounts:</p>
            <ul className="small text-secondary mb-0">
              <li><strong>Admin:</strong> <code>admin@campus.edu</code> / <code>AdminPass123!</code></li>
              <li><strong>Handler:</strong> <code>handler@campus.edu</code> / <code>HandlerPass123!</code></li>
              <li><strong>Student:</strong> <code>student.aarav@campus.edu</code> / <code>StudentPass123!</code></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

