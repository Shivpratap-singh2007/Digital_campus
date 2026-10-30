import React from 'react';

interface Props {
  type: 'status' | 'priority' | 'feedback_round' | 'feedback_response';
  value: string;
}

export const StatusBadge: React.FC<Props> = ({ type, value }) => {
  if (type === 'priority') {
    switch (value) {
      case 'Urgent review':
        return <span className="badge badge-urgent"><i className="bi bi-exclamation-octagon-fill me-1"></i>Urgent</span>;
      case 'High':
        return <span className="badge badge-high">High</span>;
      case 'Low':
        return <span className="badge badge-low">Low</span>;
      default:
        return <span className="badge badge-normal">Normal</span>;
    }
  }

  if (type === 'status') {
    switch (value) {
      case 'resolved':
        return <span className="badge bg-success"><i className="bi bi-check2-circle me-1"></i>Resolved</span>;
      case 'in_progress':
        return <span className="badge bg-info text-dark">In Progress</span>;
      case 'under_review':
        return <span className="badge bg-warning text-dark">Under Review</span>;
      default:
        return <span className="badge bg-secondary">Submitted</span>;
    }
  }

  if (type === 'feedback_round') {
    switch (value) {
      case 'submitter_confirmed':
        return <span className="badge bg-success"><i className="bi bi-check-all me-1"></i>Submitter Confirmed</span>;
      case 'disputed':
        return <span className="badge bg-danger"><i className="bi bi-exclamation-triangle me-1"></i>Disputed</span>;
      case 'pending_feedback':
        return <span className="badge bg-warning text-dark"><i className="bi bi-hourglass-split me-1"></i>Pending Feedback</span>;
      default:
        return <span className="badge bg-secondary">No Response</span>;
    }
  }

  if (type === 'feedback_response') {
    switch (value) {
      case 'fixed':
        return <span className="badge bg-success"><i className="bi bi-check-circle me-1"></i>Fixed</span>;
      case 'partially_fixed':
        return <span className="badge bg-warning text-dark"><i className="bi bi-dash-circle me-1"></i>Partially Fixed</span>;
      case 'not_fixed':
        return <span className="badge bg-danger"><i className="bi bi-x-circle me-1"></i>Not Fixed</span>;
      default:
        return <span className="badge bg-secondary">{value}</span>;
    }
  }

  return <span className="badge bg-secondary">{value}</span>;
};

