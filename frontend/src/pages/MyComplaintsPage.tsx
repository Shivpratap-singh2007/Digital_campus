import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';

export const MyComplaintsPage: React.FC = () => {
  const { user } = useAuth();
  const [complaints, setComplaints] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadComplaints() {
      try {
        const data = await api.get('/api/complaints');
        setComplaints(data.complaints || []);
      } catch (err) {
        console.error('Failed to load user complaints:', err);
      } finally {
        setLoading(false);
      }
    }
    loadComplaints();
  }, []);

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h3 className="mb-1 text-dark">
            <i className="bi bi-collection me-2"></i>My Submissions
          </h3>
          <p className="text-muted small mb-0">
            Track status progression and provide verified resolution feedback once issues are marked resolved.
          </p>
        </div>
        <Link to="/new-complaint" className="btn btn-primary">
          <i className="bi bi-plus-circle me-1"></i>New Report
        </Link>
      </div>

      {!user?.is_verified && (
        <div className="alert alert-warning d-flex justify-content-between align-items-center mb-4">
          <div>
            <i className="bi bi-exclamation-triangle-fill me-2"></i>
            <strong>Email Unverified:</strong> You must verify your college email address before new submissions can be submitted.
          </div>
          <Link to="/verify-email" className="btn btn-sm btn-outline-dark">
            Verify Now
          </Link>
        </div>
      )}

      {loading ? (
        <div className="card card-shadow p-5 text-center text-muted">
          Loading your submissions...
        </div>
      ) : complaints.length > 0 ? (
        <div className="card card-shadow">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th style={{ width: '80px' }}>Ref ID</th>
                  <th>Type & Title</th>
                  <th>Category</th>
                  <th>Building / Room</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Feedback State</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((c) => (
                  <tr key={c.id}>
                    <td><strong>#{c.id}</strong></td>
                    <td>
                      <div>
                        <span className="badge bg-secondary text-capitalize me-1">{c.submission_type}</span>
                        <Link to={`/complaints/${c.id}`} className="fw-semibold text-decoration-none">
                          {c.title}
                        </Link>
                      </div>
                      <small className="text-muted">
                        {new Date(c.created_at).toLocaleString()}
                      </small>
                    </td>
                    <td><span className="badge bg-light text-dark border">{c.display_category}</span></td>
                    <td>
                      <div>{c.building}</div>
                      {c.room && <small className="text-muted">{c.room}</small>}
                    </td>
                    <td><StatusBadge type="priority" value={c.priority} /></td>
                    <td><StatusBadge type="status" value={c.status} /></td>
                    <td>
                      {c.linked_issue_status === 'resolved' ? (
                        <Link to={`/complaints/${c.id}#feedback`} className="btn btn-sm btn-outline-success">
                          <i className="bi bi-hand-thumbs-up me-1"></i>Give Feedback
                        </Link>
                      ) : (
                        <span className="text-muted small">—</span>
                      )}
                    </td>
                    <td className="text-end">
                      <Link to={`/complaints/${c.id}`} className="btn btn-sm btn-outline-primary">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card card-shadow text-center p-5">
          <i className="bi bi-inbox text-muted" style={{ fontSize: '3rem' }}></i>
          <h5 className="mt-3">No Submissions Found</h5>
          <p className="text-muted small">You haven't submitted any campus complaints or suggestions yet.</p>
          <div>
            <Link to="/new-complaint" className="btn btn-primary">
              Submit Your First Report
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};

