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
    <div className="row justify-content-center py-4">
      <div className="col-11 col-sm-9 col-md-7 col-lg-6 col-xl-5">
        <div className="cv-card">
          <div className="cv-card-body p-4 text-center">
            <div className="mb-3">
              <i className="bi bi-envelope-check text-primary" style={{ fontSize: '2.5rem' }}></i>
            </div>
            <h4 className="fw-bold text-dark mb-1">Email Verification</h4>
            <p className="text-muted small mb-4">
              Verify campus domain ownership to unlock report submissions
            </p>

            {verifying ? (
              <div className="my-4">
                <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                <p className="mt-2 text-muted small">Verifying single-use token...</p>
              </div>
            ) : verificationResult ? (
              <div className="my-4">
                <div
                  className={`alert ${verificationResult.success ? 'alert-success' : 'alert-danger'} text-start small mb-3`}
                >
                  <h6 className="fw-bold mb-1">
                    <i className={`bi ${verificationResult.success ? 'bi-check-circle' : 'bi-x-circle'} me-1`}></i>
                    {verificationResult.success ? 'Verification Successful' : 'Verification Error'}
                  </h6>
                  <p className="mb-0">{verificationResult.message}</p>
                </div>

                {verificationResult.success && (
                  <Link to="/my-complaints" className="btn btn-primary btn-sm px-4">
                    Continue to Submissions
                  </Link>
                )}
              </div>
            ) : (
              <p className="text-muted small mb-4">
                {email ? (
                  <>Verification dispatched to <strong>{email}</strong></>
                ) : (
                  'Please verify your college email address to unlock report submissions.'
                )}
              </p>
            )}

            {/* Mailpit local demo environment notice */}
            <div className="cv-card bg-white p-3 text-start mb-4 border-subtle">
              <div className="d-flex align-items-center gap-2 mb-1">
                <i className="bi bi-hdd-network text-muted"></i>
                <span className="fw-semibold text-secondary small">Demo SMTP Mailbox</span>
              </div>
              <p className="small text-muted mb-2">
                In this local hackathon environment, emails are captured by Mailpit. Open your local inbox to click verification links:
              </p>
              <a
                href="http://localhost:8025"
                target="_blank"
                rel="noreferrer"
                className="btn btn-outline-secondary btn-sm"
              >
                <i className="bi bi-box-arrow-up-right me-1"></i>Open Mailpit (localhost:8025)
              </a>
            </div>

            {/* Resend Verification Form */}
            <form onSubmit={handleResend} className="text-start border-top pt-3">
              <label className="form-label small fw-semibold">Need a new verification link?</label>
              {resendStatus && <div className="alert alert-success py-2 small mb-2">{resendStatus}</div>}
              {resendError && <div className="alert alert-danger py-2 small mb-2">{resendError}</div>}

              <div className="input-group">
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
