import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

export const VerifyEmailPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();

  const queryParams = new URLSearchParams(location.search);
  const tokenFromUrl = queryParams.get('token');
  const initialEmail = (location.state as any)?.email || user?.email || '';

  const [email, setEmail] = useState(initialEmail);
  const [resendStatus, setResendStatus] = useState<string | null>(null);
  const [resendError, setResendError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<{ success: boolean; message: string } | null>(null);

  // If token is in URL, auto verify
  useEffect(() => {
    if (tokenFromUrl) {
      setVerifying(true);
      api
        .get(`/api/auth/verify/${tokenFromUrl}`)
        .then(async (res) => {
          setVerificationResult({ success: true, message: res.message });
          await refreshUser();
        })
        .catch((err) => {
          setVerificationResult({ success: false, message: err.message || 'Verification failed.' });
        })
        .finally(() => {
          setVerifying(false);
        });
    }
  }, [tokenFromUrl]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    setResendStatus(null);
    setResendError(null);

    try {
      const res = await api.post('/api/auth/resend-verification', { email });
      setResendStatus(res.message);
    } catch (err: any) {
      setResendError(err.message || 'Failed to resend verification.');
    }
  };

  return (
    <div className="row justify-content-center">
      <div className="col-md-7">
        <div className="card card-shadow mt-4">
          <div className="card-body p-4 text-center">
            <i className="bi bi-envelope-check text-primary" style={{ fontSize: '3rem' }}></i>
            <h3 className="card-title mt-3">College Email Verification</h3>

            {verifying ? (
              <div className="my-4">
                <div className="spinner-border text-primary" role="status"></div>
                <p className="mt-2 text-muted">Verifying single-use token...</p>
              </div>
            ) : verificationResult ? (
              <div className="my-4">
                <div
                  className={`alert ${verificationResult.success ? 'alert-success' : 'alert-danger'} text-start`}
                >
                  <h6 className="fw-bold">
                    <i className={`bi ${verificationResult.success ? 'bi-check-circle' : 'bi-x-circle'} me-2`}></i>
                    {verificationResult.success ? 'Verification Successful' : 'Verification Error'}
                  </h6>
                  <p className="mb-0 small">{verificationResult.message}</p>
                </div>

                {verificationResult.success ? (
                  <Link to="/my-complaints" className="btn btn-primary px-4 mt-2">
                    Go to My Submissions
                  </Link>
                ) : (
                  <p className="small text-muted mt-2">
                    Please request a new link using the resend form below.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-muted">
                {email ? (
                  <>Verification dispatched to <strong>{email}</strong></>
                ) : (
                  'Please verify your college email address to unlock report submissions.'
                )}
              </p>
            )}

            {/* Mailpit local prototype info banner */}
            <div className="alert alert-warning text-start my-4">
              <h6 className="alert-heading fw-bold">
                <i className="bi bi-gear-wide-connected me-1"></i> Demo / Hackathon SMTP Environment:
              </h6>
              <p className="small mb-2">
                In this demonstration environment, emails are routed through a local Mailpit SMTP server (configured on <code>localhost:1025</code>).
              </p>
              <p className="small mb-0">
                To view intercepted emails and click the single-use verification link, open the Mailpit web interface:
                <br />
                <a href="http://localhost:8025" target="_blank" rel="noreferrer" className="fw-bold text-decoration-underline">
                  http://localhost:8025
                </a>
              </p>
            </div>

            {/* Security Notes */}
            <div className="card bg-light border-0 text-start p-3 mb-4">
              <h6 className="fw-bold small text-secondary mb-2">Security & Verification Policies:</h6>
              <ul className="small text-secondary mb-0">
                <li>Complaint submissions are strictly locked until email ownership is proven.</li>
                <li>Tokens expire in 24 hours and are permanently consumed once used.</li>
                <li>Raw tokens are never exposed in browser logs or console outputs; only cryptographic hashes are stored.</li>
              </ul>
            </div>

            {/* Resend Verification Form */}
            <form onSubmit={handleResend} className="text-start border-top pt-3">
              <h6 className="fw-semibold text-dark mb-2">Need a new verification link?</h6>
              {resendStatus && <div className="alert alert-success py-2 small">{resendStatus}</div>}
              {resendError && <div className="alert alert-danger py-2 small">{resendError}</div>}

              <div className="input-group mb-3">
                <input
                  type="email"
                  className="form-control"
                  placeholder="yourname@campus.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <button type="submit" className="btn btn-outline-secondary">
                  Resend Link
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

