import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

export const IssueDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [issue, setIssue] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Status update form
  const [newStatus, setNewStatus] = useState('under_review');
  const [statusNote, setStatusNote] = useState('');
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [statusError, setStatusError] = useState('');

  // Manual link form
  const [manualComplaintId, setManualComplaintId] = useState('');
  const [manualRelType, setManualRelType] = useState('same_incident');

  const loadIssue = async () => {
    try {
      const data = await api.get(`/api/issues/${id}`);
      setIssue(data);
      setNewStatus(data.status);
    } catch (err: any) {
      setError(err.message || 'Failed to load issue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIssue();
  }, [id]);

  const handleStatusUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusUpdating(true);
    setStatusMessage('');
    setStatusError('');

    try {
      const res = await api.post(`/api/issues/${id}/status`, {
        new_status: newStatus,
        note: statusNote,
      });
      setStatusMessage(res.message);
      setStatusNote('');
      await loadIssue();
    } catch (err: any) {
      setStatusError(err.message || 'Failed to update status.');
    } finally {
      setStatusUpdating(false);
    }
  };

  const handleUnlink = async (complaintId: number) => {
    if (!window.confirm('Unlink this complaint? Original report will be preserved intact.')) {
      return;
    }
    try {
      await api.post(`/api/issues/${id}/unlink/${complaintId}`);
      await loadIssue();
    } catch (err: any) {
      alert(err.message || 'Unlink failed.');
    }
  };

  const handleFastLink = async (complaintId: number, relType: string) => {
    try {
      await api.post(`/api/issues/${id}/link`, {
        complaint_id: complaintId,
        relationship_type: relType,
      });
      await loadIssue();
    } catch (err: any) {
      alert(err.message || 'Link failed.');
    }
  };

  const handleManualLink = async (e: React.FormEvent) => {
    e.preventDefault();
    const cId = parseInt(manualComplaintId, 10);
    if (!cId) return;

    try {
      await api.post(`/api/issues/${id}/link`, {
        complaint_id: cId,
        relationship_type: manualRelType,
      });
      setManualComplaintId('');
      await loadIssue();
    } catch (err: any) {
      alert(err.message || 'Link failed.');
    }
  };

  if (loading) return <div className="p-5 text-center text-muted">Loading issue details...</div>;

  if (error || !issue) {
    return (
      <div className="alert alert-danger my-4">
        {error || 'Issue not found.'}
        <div className="mt-2">
          <Link to="/admin/queue" className="btn btn-sm btn-outline-danger">
            Back to Queue
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/admin/queue" className="text-decoration-none text-muted small">
          <i className="bi bi-arrow-left"></i> Back to Complaints Queue
        </Link>
      </div>

      <div className="row">
        {/* Left Column: Details & Linked Submissions */}
        <div className="col-lg-8">
          <div className="card card-shadow mb-4">
            <div className="card-header bg-white py-3 d-flex justify-content-between align-items-center">
              <div>
                <span className="badge bg-primary me-2">Master Issue #{issue.id}</span>
                <span className="text-muted small">
                  Created {new Date(issue.created_at).toLocaleString()}
                </span>
              </div>
              <div>
                <StatusBadge type="status" value={issue.status} />
              </div>
            </div>
            <div className="card-body p-4">
              <h3 className="card-title text-dark mb-3">{issue.title}</h3>

              <div className="d-flex flex-wrap gap-2 mb-3">
                <span className="badge bg-light text-dark border">
                  <i className="bi bi-geo-alt me-1"></i>
                  {issue.building} {issue.room && `• ${issue.room}`}
                </span>
                <span className="badge bg-light text-dark border">
                  <i className="bi bi-tag me-1"></i>Category: {issue.category}
                </span>
                <StatusBadge type="priority" value={issue.priority} />
              </div>

              <div className="p-3 bg-light rounded mb-4">
                <h6 className="text-secondary small fw-bold text-uppercase mb-2">
                  Synthesized Public Summary
                </h6>
                <p className="mb-0 text-dark" style={{ whiteSpace: 'pre-wrap' }}>
                  {issue.description}
                </p>
              </div>

              {/* Linked Complaints List */}
              <div className="mb-4">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h5 className="mb-0 text-dark">
                    <i className="bi bi-link-45deg me-1"></i>Linked Submissions ({issue.linked_complaints?.length || 0})
                  </h5>
                  <small className="text-muted">Original reports are preserved intact.</small>
                </div>

                {issue.linked_complaints && issue.linked_complaints.length > 0 ? (
                  <div className="list-group">
                    {issue.linked_complaints.map((c: any) => (
                      <div
                        key={c.complaint_id}
                        className="list-group-item d-flex justify-content-between align-items-center p-3"
                      >
                        <div>
                          <div className="d-flex align-items-center gap-2">
                            <strong>#{c.complaint_id}</strong>
                            <Link to={`/complaints/${c.complaint_id}`} className="fw-semibold text-decoration-none">
                              {c.title}
                            </Link>
                            <span className="badge bg-secondary text-capitalize small">
                              {c.submission_type}
                            </span>
                          </div>
                          <div className="small text-muted mt-1">
                            <span><i className="bi bi-geo-alt"></i> {c.building} {c.room && `(${c.room})`}</span> &bull;{' '}
                            <span><i className="bi bi-tag"></i> {c.category}</span> &bull;{' '}
                            <span>Relationship: <code>{c.relationship_type}</code></span>
                          </div>
                        </div>
                        <div>
                          {/* Reversible Grouping */}
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-danger"
                            title="Unlink complaint (reversible)"
                            onClick={() => handleUnlink(c.complaint_id)}
                          >
                            <i className="bi bi-x-circle me-1"></i>Unlink
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="alert alert-warning small mb-0">
                    No complaints currently linked to this issue.
                  </div>
                )}
              </div>

              {/* Suggested Related Reports (Semantic AI & Proximity) */}
              <div className="mb-4">
                <h5 className="mb-2 text-dark">
                  <i className="bi bi-magic me-1 text-primary"></i>Suggested Related Reports
                </h5>
                <p className="text-muted small mb-3">
                  Candidate complaints ranked using multilingual semantic similarity and structured location proximity.
                </p>

                {issue.suggested_matches && issue.suggested_matches.length > 0 ? (
                  <div className="list-group">
                    {issue.suggested_matches.map((m: any) => (
                      <div key={m.complaint_id} className="list-group-item p-3">
                        <div className="d-flex justify-content-between align-items-start">
                          <div>
                            <div className="d-flex align-items-center gap-2">
                              <strong>#{m.complaint_id}</strong>
                              <Link to={`/complaints/${m.complaint_id}`} target="_blank" className="fw-semibold text-decoration-none">
                                {m.title}
                              </Link>
                              {m.is_possible_recurrence && (
                                <span className="badge bg-danger-subtle text-danger border border-danger">
                                  <i className="bi bi-arrow-repeat"></i> Possible Recurrence
                                </span>
                              )}
                            </div>
                            <div className="small text-muted mt-1">
                              <i className="bi bi-geo-alt"></i> {m.building} {m.room && `(${m.room})`} &bull;{' '}
                              <span className="text-primary fw-semibold">{m.match_details}</span>
                            </div>
                          </div>
                          <div className="d-flex gap-2">
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-primary"
                              onClick={() => handleFastLink(m.complaint_id, 'same_incident')}
                            >
                              Same Incident
                            </button>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => handleFastLink(m.complaint_id, 'related_only')}
                            >
                              Related Only
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="alert alert-light border small text-muted mb-0">
                    No unlinked candidate complaints found with high similarity.
                  </div>
                )}
              </div>

              {/* Status Progression History */}
              <div className="card bg-white border">
                <div className="card-header bg-light py-2">
                  <h6 className="mb-0 text-dark fw-bold">
                    <i className="bi bi-clock-history me-1"></i>Issue Status History
                  </h6>
                </div>
                <div className="card-body p-3">
                  {issue.status_events && issue.status_events.length > 0 ? (
                    <ul className="list-group list-group-flush">
                      {issue.status_events.map((ev: any) => (
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
                    <p className="text-muted small mb-0">No status updates logged.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Status Operations & Resolution Rounds */}
        <div className="col-lg-4">
          {/* Status Update Form */}
          <div className="card card-shadow mb-4">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 text-dark">
                <i className="bi bi-sliders me-2"></i>Update Status
              </h5>
            </div>
            <div className="card-body p-3">
              {statusMessage && <div className="alert alert-success py-2 small">{statusMessage}</div>}
              {statusError && <div className="alert alert-danger py-2 small">{statusError}</div>}

              <form onSubmit={handleStatusUpdate}>
                <div className="mb-3">
                  <label className="form-label small fw-semibold">New Operational Status</label>
                  <select
                    className="form-select"
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                  >
                    <option value="submitted">Submitted</option>
                    <option value="under_review">Under Review</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label small fw-semibold">
                    Operational Note / Reason <span className="text-danger">*</span>
                  </label>
                  <textarea
                    className="form-control"
                    rows={3}
                    placeholder="Required note. If marking Resolved, describe the specific repairs completed..."
                    value={statusNote}
                    onChange={(e) => setStatusNote(e.target.value)}
                    required
                    minLength={5}
                  />
                  <div className="form-text small text-muted">
                    When marking Resolved, a new feedback round will be created for submitters.
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn btn-primary w-100"
                  disabled={statusUpdating}
                >
                  <i className="bi bi-arrow-repeat me-1"></i>
                  {statusUpdating ? 'Updating...' : 'Commit Status Update'}
                </button>
              </form>
            </div>
          </div>

          {/* Resolution Rounds & Verified Feedback */}
          <div className="card card-shadow mb-4">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 text-dark">
                <i className="bi bi-patch-check me-2"></i>Resolution Feedback Rounds
              </h5>
            </div>
            <div className="card-body p-3">
              {issue.resolution_rounds && issue.resolution_rounds.length > 0 ? (
                issue.resolution_rounds.map((round: any) => (
                  <div key={round.round_number} className="border rounded p-3 mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span className="fw-bold">Round #{round.round_number}</span>
                      <StatusBadge type="feedback_round" value={round.status} />
                    </div>

                    <p className="small text-muted mb-2">
                      <strong>Resolution Note:</strong> <em>"{round.resolution_note}"</em>
                    </p>

                    <div className="bg-light p-2 rounded small">
                      <div className="fw-semibold text-secondary mb-1">Aggregate Submitter Responses:</div>
                      <div className="d-flex justify-content-between">
                        <span className="text-success">
                          Fixed: <strong>{round.aggregate_counts.fixed}</strong>
                        </span>
                        <span className="text-warning text-dark">
                          Partial: <strong>{round.aggregate_counts.partially_fixed}</strong>
                        </span>
                        <span className="text-danger">
                          Not Fixed: <strong>{round.aggregate_counts.not_fixed}</strong>
                        </span>
                      </div>
                    </div>

                    <div className="small text-muted mt-2" style={{ fontSize: '0.78rem' }}>
                      <em>All linked submitters must confirm fixed before labeled submitter-confirmed. Missing responses never count as fixed.</em>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-muted small mb-0">
                  No resolution rounds yet. When this issue is marked Resolved, original submitters will be invited to provide verified feedback.
                </p>
              )}
            </div>
          </div>

          {/* Manual Link by ID */}
          <div className="card card-shadow mb-4">
            <div className="card-header bg-light py-2">
              <h6 className="mb-0 text-dark fw-bold">
                <i className="bi bi-plus-lg me-1"></i>Link Complaint by ID
              </h6>
            </div>
            <div className="card-body p-3">
              <form onSubmit={handleManualLink}>
                <div className="mb-2">
                  <label className="form-label small fw-semibold">Complaint Reference ID</label>
                  <input
                    type="number"
                    className="form-control form-control-sm"
                    placeholder="e.g. 5"
                    value={manualComplaintId}
                    onChange={(e) => setManualComplaintId(e.target.value)}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label small fw-semibold">Relationship Type</label>
                  <select
                    className="form-select form-select-sm"
                    value={manualRelType}
                    onChange={(e) => setManualRelType(e.target.value)}
                  >
                    <option value="same_incident">Same Incident</option>
                    <option value="related_only">Related Only</option>
                  </select>
                </div>
                <button type="submit" className="btn btn-outline-primary btn-sm w-100">
                  Link Submission
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

