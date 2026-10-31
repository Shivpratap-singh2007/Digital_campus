import React, { useState } from 'react';
import { api } from '../api/client';

export type FeedbackOption = 'fixed' | 'partially_fixed' | 'not_fixed';

interface ResolutionVerificationCardProps {
  complaintId: number;
  issueId?: number;
  initialOption?: FeedbackOption;
  initialObservations?: string;
  onSuccess: (result: {
    response: FeedbackOption;
    observations: string;
    ticketStatus: string;
    message: string;
  }) => void;
}

const AI_SUGGESTIONS: Record<FeedbackOption, string> = {
  fixed: 'Verified on-site. The issue has been completely resolved and functioning properly. Thank you.',
  partially_fixed: 'Work was attempted, but incomplete. Basic functionality is restored, but minor issues/safety concerns still persist.',
  not_fixed: 'Inspected the site. The malfunction remains completely unresolved and continues to cause disruption.',
};

export const ResolutionVerificationCard: React.FC<ResolutionVerificationCardProps> = ({
  complaintId,
  issueId,
  initialOption = 'fixed',
  initialObservations,
  onSuccess,
}) => {
  const [selectedOption, setSelectedOption] = useState<FeedbackOption>(initialOption);
  const [observations, setObservations] = useState<string>(
    initialObservations || AI_SUGGESTIONS[initialOption]
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{
    message: string;
    type: 'success' | 'warning' | 'danger';
    icon: string;
  } | null>(null);

  const handleOptionChange = (option: FeedbackOption) => {
    setSelectedOption(option);
    // Dynamically auto-suggest appropriate observation text
    setObservations(AI_SUGGESTIONS[option]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const endpoint = issueId
        ? `/api/feedback/issue/${issueId}`
        : `/api/feedback/complaint/${complaintId}`;

      const res = await api.post(endpoint, {
        response: selectedOption,
        comments: observations.trim(),
      });

      const isFixed = selectedOption === 'fixed';
      const toastMessage = isFixed
        ? '✓ Resolution confirmed! Ticket permanently marked as Resolved.'
        : `⚠️ Ticket re-opened to In Progress. High-priority alert sent to maintenance desk.`;

      // Show instant toast notification
      setToast({
        message: toastMessage,
        type: isFixed ? 'success' : 'warning',
        icon: isFixed ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill',
      });

      // Notify parent to smoothly update UI state (status badge, timeline, etc.)
      onSuccess({
        response: selectedOption,
        observations: observations.trim(),
        ticketStatus: isFixed ? 'resolved' : 'in_progress',
        message: res.message || toastMessage,
      });

      setTimeout(() => {
        setToast(null);
      }, 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to submit verification confirmation.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      {/* Floating Instant Toast */}
      {toast && (
        <div className="position-fixed bottom-0 end-0 p-3" style={{ zIndex: 1150 }}>
          <div
            className={`toast show align-items-center text-white ${
              toast.type === 'success'
                ? 'bg-success'
                : toast.type === 'warning'
                ? 'bg-dark border border-warning'
                : 'bg-danger'
            } border-0 shadow-lg`}
            role="alert"
          >
            <div className="d-flex">
              <div className="toast-body d-flex align-items-center gap-2 py-3 px-3">
                <i className={`bi ${toast.icon} fs-5 ${toast.type === 'warning' ? 'text-warning' : ''}`}></i>
                <span className="small fw-medium">{toast.message}</span>
              </div>
              <button
                type="button"
                className="btn-close btn-close-white me-2 m-auto"
                onClick={() => setToast(null)}
              ></button>
            </div>
          </div>
        </div>
      )}

      {/* Strictly Minimal Resolution Verification Card */}
      <div className="cv-card mb-4 border">
        <div className="cv-card-body p-4">
          <div className="d-flex align-items-center justify-content-between mb-3">
            <h5 className="fw-bold text-dark mb-0">Resolution Verification</h5>
            <span className="badge bg-light text-secondary border font-monospace" style={{ fontSize: '0.72rem' }}>
              Student Verification
            </span>
          </div>

          {error && (
            <div className="alert alert-danger py-2 small mb-3">
              <i className="bi bi-exclamation-circle me-1"></i>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* 1. Selection Options: 'Fixed', 'Partially fixed', 'Not fixed' */}
            <div className="mb-3">
              <label className="form-label small fw-medium text-muted text-uppercase mb-2" style={{ letterSpacing: '0.04em' }}>
                Resolution Outcome
              </label>
              <div className="d-flex flex-column gap-2">
                {/* Fixed */}
                <label
                  className={`d-flex align-items-center gap-3 p-3 rounded border transition-all ${
                    selectedOption === 'fixed'
                      ? 'border-success bg-success-subtle shadow-xs'
                      : 'bg-white'
                  }`}
                  style={{ cursor: 'pointer' }}
                >
                  <input
                    type="radio"
                    name="resolution_outcome"
                    value="fixed"
                    checked={selectedOption === 'fixed'}
                    onChange={() => handleOptionChange('fixed')}
                    className="form-check-input mt-0"
                    style={{ cursor: 'pointer' }}
                  />
                  <div>
                    <span className="fw-semibold text-dark">Fixed</span>
                    <span className="text-muted small ms-2">— Issue resolved completely.</span>
                  </div>
                </label>

                {/* Partially fixed */}
                <label
                  className={`d-flex align-items-center gap-3 p-3 rounded border transition-all ${
                    selectedOption === 'partially_fixed'
                      ? 'border-warning bg-warning-subtle shadow-xs'
                      : 'bg-white'
                  }`}
                  style={{ cursor: 'pointer' }}
                >
                  <input
                    type="radio"
                    name="resolution_outcome"
                    value="partially_fixed"
                    checked={selectedOption === 'partially_fixed'}
                    onChange={() => handleOptionChange('partially_fixed')}
                    className="form-check-input mt-0"
                    style={{ cursor: 'pointer' }}
                  />
                  <div>
                    <span className="fw-semibold text-dark">Partially fixed</span>
                    <span className="text-muted small ms-2">— Incomplete or minor issues remain.</span>
                  </div>
                </label>

                {/* Not fixed */}
                <label
                  className={`d-flex align-items-center gap-3 p-3 rounded border transition-all ${
                    selectedOption === 'not_fixed'
                      ? 'border-danger bg-danger-subtle shadow-xs'
                      : 'bg-white'
                  }`}
                  style={{ cursor: 'pointer' }}
                >
                  <input
                    type="radio"
                    name="resolution_outcome"
                    value="not_fixed"
                    checked={selectedOption === 'not_fixed'}
                    onChange={() => handleOptionChange('not_fixed')}
                    className="form-check-input mt-0"
                    style={{ cursor: 'pointer' }}
                  />
                  <div>
                    <span className="fw-semibold text-dark">Not fixed</span>
                    <span className="text-muted small ms-2">— Malfunction persists unresolved.</span>
                  </div>
                </label>
              </div>
            </div>

            {/* 2. Submitter Observations Textarea */}
            <div className="mb-4">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <label htmlFor="submitterObservations" className="form-label mb-0 fw-medium small text-dark">
                  Submitter Observations
                </label>
                <span className="badge bg-secondary-subtle text-secondary font-monospace" style={{ fontSize: '0.68rem' }}>
                  ✨ AI Auto-Suggested
                </span>
              </div>
              <textarea
                id="submitterObservations"
                className="form-control"
                rows={3}
                value={observations}
                onChange={(e) => setObservations(e.target.value)}
                placeholder="Enter on-site verification observations or customize the suggested note..."
                required
              />
            </div>

            {/* 3. Submit Verified Confirmation Button */}
            <button
              type="submit"
              className="btn btn-primary w-100 py-2 fw-medium d-flex align-items-center justify-content-center gap-2"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                  <span>Submitting Confirmation...</span>
                </>
              ) : (
                <>
                  <i className="bi bi-shield-check"></i>
                  <span>Submit Verified Confirmation</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </>
  );
};

