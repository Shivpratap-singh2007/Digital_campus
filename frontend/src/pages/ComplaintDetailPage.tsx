import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { ResolutionVerificationCard } from '../components/ResolutionVerificationCard';

export const ComplaintDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [complaint, setComplaint] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = async () => {
    try {
      const data = await api.get(`/api/complaints/${id}`);
      setComplaint(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load complaint details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  if (loading) {
    return (
      <div className="cv-card p-5 text-center text-muted">
        <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
        Loading submission details...
      </div>
    );
  }

  if (error || !complaint) {
    return (
      <div className="cv-card p-4 text-center my-4">
        <div className="text-danger mb-2">
          <i className="bi bi-exclamation-triangle" style={{ fontSize: '2rem' }}></i>
        </div>
        <h5 className="fw-semibold text-dark">{error || 'Submission Not Found'}</h5>
        <div className="mt-3">
          <Link to="/my-complaints" className="btn btn-outline-secondary btn-sm">
            Back to Submissions
          </Link>
        </div>
      </div>
    );
  }

  const linkedIssue = complaint.linked_issue;
  const isResolved =
    complaint.status === 'resolved' ||
    Boolean(linkedIssue && (linkedIssue.status === 'resolved' || linkedIssue.current_round));

  return (
    <div>
      {/* Top Back Navigation */}
      <div className="mb-3">
        <Link to="/my-complaints" className="text-decoration-none text-muted small d-inline-flex align-items-center gap-1">
          <i className="bi bi-arrow-left"></i> Back to Submissions
        </Link>
      </div>

      <div className="row g-4">
        {/* Left Column: Details, Attachments, Resolution Feedback */}
        <div className="col-lg-8">
          <div className="cv-card mb-4">
            <div className="cv-card-header d-flex justify-content-between align-items-center">
              <div className="d-flex align-items-center gap-2">
                <span className="cv-badge cv-badge-low text-capitalize">
                  {complaint.submission_type}
                </span>
                <span className="text-muted small font-monospace">#{complaint.id}</span>
              </div>
              <div>
                <StatusBadge type="status" value={complaint.status} />
              </div>
            </div>

            <div className="cv-card-body p-4">
              <h3 className="fw-bold text-dark mb-3">{complaint.title}</h3>

              {/* Scope & Priority Chips */}
              <div className="d-flex flex-wrap align-items-center gap-2 mb-4">
                <span className="cv-badge cv-badge-low">
                  <i className="bi bi-geo-alt me-1"></i>
                  {complaint.building} {complaint.room && `· ${complaint.room}`}
                </span>
                <span className="cv-badge cv-badge-low">
                  <i className="bi bi-tag me-1"></i>
                  {complaint.display_category}
                </span>
                <StatusBadge type="priority" value={complaint.display_priority} />
                <span className="text-muted small ms-auto">
                  Submitted {new Date(complaint.created_at).toLocaleString()}
                </span>
              </div>

              {/* Description Block */}
              <div className="p-3 rounded mb-4" style={{ backgroundColor: 'var(--bg-subtle)' }}>
                <div className="text-uppercase fw-bold text-muted mb-2" style={{ fontSize: '0.72rem', letterSpacing: '0.05em' }}>
                  Original Submission Description
                </div>
                <p className="mb-0 text-dark" style={{ whiteSpace: 'pre-wrap', fontSize: '0.92rem', lineHeight: '1.6' }}>
                  {complaint.description}
                </p>
              </div>

              {/* Secure Verified Attachments */}
              {complaint.attachments && complaint.attachments.length > 0 && (
                <div className="mb-4">
                  <div className="text-uppercase fw-bold text-muted mb-2" style={{ fontSize: '0.72rem', letterSpacing: '0.05em' }}>
                    Verified Attachment
                  </div>
                  {complaint.attachments.map((att: any, idx: number) => (
                    <div key={idx} className="border rounded p-2 d-inline-block bg-white text-center">
                      <a href={att.url} target="_blank" rel="noreferrer">
                        <img
                          src={att.url}
                          alt="Submission photo"
                          className="img-fluid rounded"
                          style={{ maxHeight: '260px', objectFit: 'contain' }}
                        />
                      </a>
                      <div className="small text-muted mt-1">
                        {att.original_filename} ({(att.file_size / 1024).toFixed(1)} KB)
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Verified Resolution Feedback Section */}
              {isResolved && (
                <div id="feedback" className="mt-4">
                  <ResolutionVerificationCard
                    complaintId={complaint.id}
                    issueId={linkedIssue?.id}
                    initialOption={linkedIssue?.user_feedback?.response || 'fixed'}
                    initialObservations={linkedIssue?.user_feedback?.comments}
                    onSuccess={async (res) => {
                      setComplaint((prev: any) => ({
                        ...prev,
                        status: res.ticketStatus,
                      }));
                      await loadData();
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Status Progression Timeline */}
          <div className="cv-card mb-4">
            <div className="cv-card-header">
              <h5 className="mb-0 fw-semibold text-dark">Status Progression & Timeline</h5>
            </div>
            <div className="cv-card-body p-3">
              {complaint.status_events && complaint.status_events.length > 0 ? (
                <div className="d-flex flex-column gap-3">
                  {complaint.status_events.map((ev: any) => (
                    <div key={ev.id} className="d-flex justify-content-between align-items-center py-2 border-bottom last-border-none">
                      <div className="d-flex align-items-center gap-2">
                        <span className="cv-badge cv-badge-low text-capitalize">{ev.new_status}</span>
                        <span className="text-dark small">{ev.note}</span>
                      </div>
                      <span className="text-muted small">
                        {new Date(ev.created_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted small mb-0">No operational progression events recorded yet.</p>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: AI Diagnostics & Master Issue Link */}
        <div className="col-lg-4">
          {/* AI & Rule Diagnostics Card */}
          <div className="cv-card mb-4">
            <div className="cv-card-header">
              <h6 className="mb-0 fw-bold text-dark">Rule & Semantic Diagnostics</h6>
            </div>
            <div className="cv-card-body p-3">
              {complaint.analysis ? (
                <div className="d-flex flex-column gap-3">
                  {/* Category Evaluation */}
                  <div>
                    <div className="text-uppercase fw-bold text-muted mb-1" style={{ fontSize: '0.7rem' }}>
                      Category Evaluation
                    </div>
                    <div className="small">
                      <div className="text-muted">User Selected: <strong className="text-dark">{complaint.user_category}</strong></div>
                      <div className="text-muted mt-1">
                        AI Suggested:{' '}
                        {complaint.analysis.suggested_category ? (
                          <span className="fw-semibold text-primary">
                            {complaint.analysis.suggested_category}
                            {complaint.analysis.category_similarity && (
                              <span className="text-muted ms-1 font-monospace">
                                ({complaint.analysis.category_similarity})
                              </span>
                            )}
                          </span>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </div>
                      <div className="text-muted mt-1">
                        Assigned Category: <strong className="text-dark">{complaint.display_category}</strong>
                      </div>
                    </div>
                    {complaint.analysis.category_reason && (
                      <div className="text-muted small fst-italic mt-1" style={{ fontSize: '0.78rem' }}>
                        {complaint.analysis.category_reason}
                      </div>
                    )}
                  </div>

                  <hr className="my-1 border-subtle" />

                  {/* Priority Rule Evaluation */}
                  <div>
                    <div className="text-uppercase fw-bold text-muted mb-1" style={{ fontSize: '0.7rem' }}>
                      Priority Rule Evaluation
                    </div>
                    <div className="small">
                      <div className="d-flex align-items-center gap-2 mb-1">
                        <span className="text-muted">Suggested:</span>
                        <StatusBadge type="priority" value={complaint.analysis.suggested_priority} />
                      </div>
                      {complaint.analysis.matched_phrase && (
                        <div className="text-muted mt-1">
                          Matched Trigger: <code className="text-dark">{complaint.analysis.matched_phrase}</code>
                        </div>
                      )}
                      <div className="text-muted small mt-1" style={{ fontSize: '0.78rem' }}>
                        {complaint.analysis.priority_reason}
                      </div>
                    </div>
                  </div>

                  <hr className="my-1 border-subtle" />

                  {/* Model Engine Metadata */}
                  <div className="small text-muted" style={{ fontSize: '0.76rem' }}>
                    <div>Engine: <code>{complaint.analysis.model_identifier}</code></div>
                    <div>Version: v{complaint.analysis.analysis_version}</div>
                    <div className="mt-1 d-flex align-items-center gap-1">
                      <span>Analysis State:</span>
                      <span className="cv-badge cv-badge-low text-capitalize">{complaint.analysis_state}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-muted small mb-0">Analysis is pending or was not executed.</p>
              )}
            </div>
          </div>

          {/* Linked Master Issue Card */}
          {linkedIssue && (
            <div className="cv-card mb-4 border-primary">
              <div className="cv-card-header bg-white border-bottom border-primary-subtle">
                <div className="d-flex align-items-center gap-2">
                  <i className="bi bi-diagram-3 text-primary"></i>
                  <h6 className="mb-0 fw-bold text-dark">Linked Master Issue</h6>
                </div>
              </div>
              <div className="cv-card-body p-3">
                <h6 className="fw-semibold text-dark mb-2">
                  {user?.is_handler ? (
                    <Link to={`/admin/issues/${linkedIssue.id}`} className="text-decoration-none">
                      Issue #{linkedIssue.id}: {linkedIssue.title}
                    </Link>
                  ) : (
                    <span>Issue #{linkedIssue.id}: {linkedIssue.title}</span>
                  )}
                </h6>
                <div className="small d-flex flex-column gap-1">
                  <div className="d-flex align-items-center gap-2">
                    <span className="text-muted">Status:</span>
                    <StatusBadge type="status" value={linkedIssue.status} />
                  </div>
                  <div className="text-muted">
                    Relationship: <code className="text-dark">{linkedIssue.relationship_type}</code>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
