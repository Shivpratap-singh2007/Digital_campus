import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await register(fullName, email, password);
      navigate('/verify-email', { state: { email } });
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="row justify-content-center">
      <div className="col-md-6">
        <div className="card card-shadow mt-4">
          <div className="card-body p-4">
            <div className="text-center mb-4">
              <i className="bi bi-mortarboard text-success" style={{ fontSize: '2.5rem' }}></i>
              <h3 className="card-title mt-2">Campus Registration</h3>
              <p className="text-muted small">Restricted to authorized college email domains</p>
            </div>

            <div className="alert alert-info py-2 small mb-3">
              <i className="bi bi-shield-check me-1"></i>
              <strong>Domain Verification:</strong> Accounts can only be created with approved campus domains (e.g., <code>@campus.edu</code>, <code>@university.ac.in</code>). A single-use verification link will be dispatched via SMTP.
            </div>

            {error && (
              <div className="alert alert-danger py-2 small" role="alert">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label fw-semibold">Full Legal Name</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g., Jane Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>

              <div className="mb-3">
                <label className="form-label fw-semibold">College Email Address</label>
                <input
                  type="email"
                  className="form-control"
                  placeholder="yourname@campus.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <div className="form-text small text-muted">
                  Must be your verified college email domain.
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label fw-semibold">Password</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="Minimum 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  required
                />
              </div>

              <div className="mb-3">
                <label className="form-label fw-semibold">Confirm Password</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="Repeat password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  minLength={8}
                  required
                />
              </div>

              <div className="form-text small text-muted mb-4">
                <em>Note: Administrative and operations handler roles cannot be requested during registration and must be provisioned via trusted CLI system command.</em>
              </div>

              <div className="d-grid">
                <button type="submit" className="btn btn-success btn-lg" disabled={loading}>
                  {loading ? 'Registering...' : 'Create Account'}
                </button>
              </div>
            </form>

            <hr className="my-4" />
            <div className="text-center">
              <p className="mb-0 text-muted small">
                Already have an account? <Link to="/login">Log in</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

