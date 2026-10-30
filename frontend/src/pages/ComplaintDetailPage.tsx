import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';

export const ComplaintDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [complaint, setComplaint] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Feedback form state
  const [feedbackResponse, setFeedbackResponse] = useState<'fixed' | 'partially_fixed' | 'not_fixed'>('fixed');
  const [feedbackComments, setFeedbackComments] = useState('');
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [feedbackError, setFeedbackError] = useState('');

  const loadData = async () => {
    try {
      const data = await api.get(`/api/complaints/${id}`);
      setComplaint(data);
      if (data.linked_issue?.user_feedback) {
        setFeedbackResponse(data.linked_issue.user_feedback.response);
        setFeedbackComments(data.linked_issue.user_feedback.comments || '');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load complaint details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!complaint?.linked_issue?.id) return;

    setFeedbackSubmitting(true);
    setFeedbackMessage('');
    setFeedbackError('');

    try {
      const res = await api.post(`/api/feedback/issue/${complaint.linked_issue.id}`, {
        response: feedbackResponse,
        comments: feedbackComments,
      });
      setFeedbackMessage(res.message || 'Feedback recorded successfully.');
      await loadData();
    } catch (err: any) {
      setFeedbackError(err.message || 'Failed to submit feedback.');
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-5 text-center text-muted">Loading complaint details...</div>;
  }

  if (error || !complaint) {
    return (
      <div className="alert alert-danger my-4">
        {error || 'Complaint not found.'}
        <div className="mt-2">
          <Link to="/my-complaints" className="btn btn-sm btn-outline-danger">
            Back to Submissions
          </Link>
        </div>
      </div>
    );
  }

  const linkedIssue = complaint.linked_issue;
  const isResolved = linkedIssue && linkedIssue.status === 'resolved';

  return (
    <div>
      <div className="mb-3">
        <Link to="/my-complaints" className="text-decoration-none text-muted small">
          <i className="bi bi-arrow-left"></i> Back to Submissions
        </Link>
      </div>

      <div className="row">
        {/* Left Column: Details, Image, Feedback */}
        <div className="col-lg-8">
          <div className="card card-shadow mb-4">
            <div className="card-header bg-white py-3 d-flex justify-content-between align-items-center">
              <div>
                <span className="badge bg-secondary text-capitalize me-2">
                  {complaint.submission_type}
                </span>
                <span className="text-muted small">Report #{complaint.id}</span>
              </div>
              <div>
                <StatusBadge type="status" value={complaint.status} />
              </div>
            </div>
            <div className="card-body p-4">
              <h3 className="card-title text-dark mb-3">{complaint.title}</h3>

              <div className="d-flex flex-wrap gap-2 mb-3">
                <span className="badge bg-light text-dark border">
                  <i className="bi bi-geo-alt me-1"></i>
                  {complaint.building} {complaint.room && `• ${complaint.room}`}
                </span>
                <span className="badge bg-light text-dark border">
                  <i className="bi bi-tag me-1"></i>Category: {complaint.display_category}
                </span>
                <StatusBadge type="priority" value={complaint.display_priority} />
              </div>

              <div className="card bg-light border-0 p-3 mb-4">
                <h6 className="text-secondary small fw-bold text-uppercase mb-2">
                  Original Submission Description
                </h6>
                <p className="mb-0 text-dark" style={{ whiteSpace: 'pre-wrap' }}>
                  {complaint.description}
                </p>
              </div>

              {/* Secure Attachments */}
              {complaint.attachments && complaint.attachments.length > 0 && (
                <div className="mb-4">
                  <h6 className="fw-semibold text-secondary">
                    <i className="bi bi-paperclip me-1"></i>Verified Photo Attachment
                  </h6>
                  {complaint.attachments.map((att: any, idx: number) => (
                    <div key={idx} className="border rounded p-2 d-inline-block bg-white text-center">
                      <a href={att.url} target="_blank" rel="noreferrer">
                        <img
                          src={att.url}
                          alt="Complaint photo"
                          className="img-fluid rounded"
                          style={{ maxHeight: '280px', objectFit: 'contain' }}
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
                <div id="feedback" className="card border-success mt-4">
                  <div className="card-header bg-success text-white py-2">
                    <h5 className="mb-0">
                      <i className="bi bi-patch-check-fill me-2"></i>Verified Resolution Feedback
                    </h5>
                  </div>
                  <div className="card-body">
                    <p className="text-muted small">
                      Campus facilities marked this issue as resolved. As the original verified submitter, please confirm whether the physical repair or solution was successful.
                    </p>

                    {feedbackMessage && <div className="alert alert-success py-2 small">{feedbackMessage}</div>}
                    {feedbackError && <div className="alert alert-danger py-2 small">{feedbackError}</div>}

                    {linkedIssue?.user_feedback && (
                      <div className="alert alert-info py-2 mb-3">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <strong>Your Recorded Feedback:</strong>
                            <span className="ms-2">
                              <StatusBadge
                                type="feedback_response"
                                value={linkedIssue.user_feedback.response}
                              />
                            </span>
                          </div>
                          <small className="text-muted">
                            {new Date(linkedIssue.user_feedback.created_at).toLocaleString()}
                          </small>
                        </div>
                        {linkedIssue.user_feedback.comments && (
                          <p className="small text-muted mt-2 mb-0">
                            <em>"{linkedIssue.user_feedback.comments}"</em>
                          </p>
                        )}
                      </div>
                    )}

                    <form onSubmit={handleFeedbackSubmit}>
                      <div className="mb-3">
                        <label className="form-label fw-semibold">
                          Has the issue been resolved to your satisfaction?
                        </label>
                        <div className="form-check my-2">
                          <input
                            className="form-check-input"
                            type="radio"
                            name="response"
                            id="respFixed"
                            value="fixed"
                            checked={feedbackResponse === 'fixed'}
                            onChange={() => setFeedbackResponse('fixed')}
                          />
                          <label className="form-check-label" htmlFor="respFixed">
                            <strong>Fixed</strong> — The problem has been completely resolved.
                          </label>
                        </div>
                        <div className="form-check my-2">
                          <input
                            className="form-check-input"
                            type="radio"
                            name="response"
                            id="respPartially"
                            value="partially_fixed"
                            checked={feedbackResponse === 'partially_fixed'}
                            onChange={() => setFeedbackResponse('partially_fixed')}
                          />
                          <label className="form-check-label" htmlFor="respPartially">
                            <strong>Partially fixed</strong> — Some work was done, but problems remain.
                          </label>
                        </div>
                        <div className="form-check my-2">
                          <input
                            className="form-check-input"
                            type="radio"
                            name="response"
                            id="respNotFixed"
                            value="not_fixed"
                            checked={feedbackResponse === 'not_fixed'}
                            onChange={() => setFeedbackResponse('not_fixed')}
                          />
                          <label className="form-check-label" htmlFor="respNotFixed">
                            <strong>Not fixed</strong> — The reported problem still persists.
                          </label>
                        </div>
                      </div>

                      <div className="mb-3">
                        <label className="form-label fw-semibold">Submitter Comments (Optional)</label>
                        <textarea
                          className="form-control"
                          rows={2}
                          placeholder="Provide details about the current physical state..."
                          value={feedbackComments}
                          onChange={(e) => setFeedbackComments(e.target.value)}
                        />
                      </div>

                      <button
                        type="submit"
                        className="btn btn-success"
                        disabled={feedbackSubmitting}
                      >
                        <i className="bi bi-check2-circle me-1"></i>
                        {feedbackSubmitting ? 'Submitting...' : 'Submit Verified Rating'}
                      </button>
                    </form>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Status Progression Timeline */}
          <div className="card card-shadow mb-4">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 text-dark">
                <i className="bi bi-clock-history me-2"></i>Status Progression & Audit Events
              </h5>
            </div>
            <div className="card-body">
              {complaint.status_events && complaint.status_events.length > 0 ? (
                <ul className="list-group list-group-flush">
                  {complaint.status_events.map((ev: any) => (
                    <li key={ev.id} className="list-group-item px-0 py-2">
                      <div className="d-flex justify-content-between align-items-center">
                        <div>
                          <span className="badge bg-secondary text-capitalize me-2">
                            {ev.new_status}
                          </span>
                          <span className="text-dark">{ev.note}</span>
                        </div>
                        <small className="text-muted">
                          {new Date(ev.created_at).toLocaleString()}
                        </small>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted small mb-0">No status progression recorded yet.</p>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: AI & Rule Diagnostics */}
        <div className="col-lg-4">
          <div className="card card-shadow mb-4">
            <div className="card-header bg-light py-2">
              <h6 className="mb-0 text-dark fw-bold">
                <i className="bi bi-cpu me-1"></i>Semantic & Rule Diagnostics
              </h6>
            </div>
            <div className="card-body">
              {complaint.analysis ? (
                <>
                  <div className="mb-3">
                    <label className="small text-muted text-uppercase fw-bold">Category Evaluation</label>
                    <div className="small">
                      <div><strong>User Selected:</strong> {complaint.user_category}</div>
                      <div>
                        <strong>AI Suggested:</strong>{' '}
                        {complaint.analysis.suggested_category ? (
                          <span className="text-primary fw-semibold">
                            {complaint.analysis.suggested_category}
                            {complaint.analysis.category_similarity && (
                              <span className="badge bg-light text-dark border ms-1">
                                Score: {complaint.analysis.category_similarity}
                              </span>
                            )}
                          </span>
                        ) : (
                          <span className="text-muted">Unavailable</span>
                        )}
                      </div>
                      <div>
                        <strong>Final Assigned:</strong>{' '}
                        <span className="badge bg-info text-dark">{complaint.display_category}</span>
                      </div>
                    </div>
                    <div className="text-muted small mt-1">
                      <em>{complaint.analysis.category_reason}</em>
                    </div>
                  </div>

                  <hr />

                  <div className="mb-3">
                    <label className="small text-muted text-uppercase fw-bold">
                      Deterministic Priority Rule
                    </label>
                    <div className="small">
                      <div>
                        <strong>Suggested Priority:</strong>{' '}
                        <StatusBadge type="priority" value={complaint.analysis.suggested_priority} />
                      </div>
                      {complaint.analysis.matched_phrase && (
                        <div className="mt-1">
                          <strong>Matched Phrase:</strong>{' '}
                          <code>{complaint.analysis.matched_phrase}</code>
                        </div>
                      )}
                      <div className="mt-1 text-muted">
                        <strong>Rule Rationale:</strong> {complaint.analysis.priority_reason}
                      </div>
                    </div>
                  </div>

                  <hr />

                  <div className="small text-muted">
                    <div><strong>Engine:</strong> <code>{complaint.analysis.model_identifier}</code></div>
                    <div><strong>Version:</strong> v{complaint.analysis.analysis_version}</div>
                    <div className="mt-1">
                      <strong>State:</strong>{' '}
                      {complaint.analysis_state === 'completed' ? (
                        <span className="badge bg-success">Completed</span>
                      ) : complaint.analysis_state === 'needs_review' ? (
                        <span className="badge bg-warning text-dark">Needs Review</span>
                      ) : (
                        <span className="badge bg-secondary">{complaint.analysis_state}</span>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-muted small mb-0">Analysis is pending or was not executed.</p>
              )}
            </div>
          </div>

          {/* Linked Master Issue */}
          {linkedIssue && (
            <div className="card card-shadow mb-4 border-primary">
              <div className="card-header bg-primary text-white py-2">
                <h6 className="mb-0 fw-bold">
                  <i className="bi bi-diagram-3-fill me-1"></i>Linked Master Issue
                </h6>
              </div>
              <div className="card-body">
                <h6 className="card-title text-primary">
                  {user?.is_handler ? (
                    <Link to={`/admin/issues/${linkedIssue.id}`} className="text-decoration-none">
                      Issue #{linkedIssue.id}: {linkedIssue.title}
                    </Link>
                  ) : (
                    <span>Issue #{linkedIssue.id}: {linkedIssue.title}</span>
                  )}
                </h6>
                <div className="small">
                  <div>
                    <strong>Status:</strong> <StatusBadge type="status" value={linkedIssue.status} />
                  </div>
                  <div>
                    <strong>Relationship:</strong> <code>{linkedIssue.relationship_type}</code>
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

