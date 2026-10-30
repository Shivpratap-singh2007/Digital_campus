import React from 'react';

interface Props {
  type: 'status' | 'priority' | 'feedback_round' | 'feedback_response';
  value: string;
}

export const StatusBadge: React.FC<Props> = ({ type, value }) => {
  if (type === 'priority') {
    switch (value) {
      case 'Urgent review':
        return (
          <span className="cv-badge cv-badge-urgent">
            <i className="bi bi-exclamation-octagon-fill"></i>
            Urgent Review
          </span>
        );
      case 'High':
        return (
          <span className="cv-badge cv-badge-high">
            <i className="bi bi-arrow-up-right"></i>
            High
          </span>
        );
      case 'Low':
        return (
          <span className="cv-badge cv-badge-low">
            <i className="bi bi-arrow-down-right"></i>
            Low
          </span>
        );
      default:
        return (
          <span className="cv-badge cv-badge-normal">
            <i className="bi bi-dash"></i>
            Normal
          </span>
        );
    }
  }

  if (type === 'status') {
    switch (value) {
      case 'resolved':
        return (
          <span className="cv-badge cv-badge-resolved">
            <i className="bi bi-check2-circle"></i>
            Resolved
          </span>
        );
      case 'in_progress':
        return (
          <span className="cv-badge cv-badge-progress">
            <i className="bi bi-play-circle"></i>
            In Progress
          </span>
        );
      case 'under_review':
        return (
          <span className="cv-badge cv-badge-review">
            <i className="bi bi-hourglass-split"></i>
            Under Review
          </span>
        );
      default:
        return (
          <span className="cv-badge cv-badge-low">
            <i className="bi bi-record-circle"></i>
            Submitted
          </span>
        );
    }
  }

  if (type === 'feedback_round') {
    switch (value) {
      case 'submitter_confirmed':
        return (
          <span className="cv-badge cv-badge-resolved">
            <i className="bi bi-check-all"></i>
            Submitter Confirmed
          </span>
        );
      case 'disputed':
        return (
          <span className="cv-badge cv-badge-urgent">
            <i className="bi bi-exclamation-triangle"></i>
            Disputed (Needs Review)
          </span>
        );
      case 'pending_feedback':
        return (
          <span className="cv-badge cv-badge-review">
            <i className="bi bi-clock"></i>
            Pending Feedback
          </span>
        );
      default:
        return (
          <span className="cv-badge cv-badge-low">
            No Response
          </span>
        );
    }
  }

  if (type === 'feedback_response') {
    switch (value) {
      case 'fixed':
        return (
          <span className="cv-badge cv-badge-resolved">
            <i className="bi bi-check-circle-fill"></i>
            Fixed
          </span>
        );
      case 'partially_fixed':
        return (
          <span className="cv-badge cv-badge-review">
            <i className="bi bi-dash-circle-fill"></i>
            Partially Fixed
          </span>
        );
      case 'not_fixed':
        return (
          <span className="cv-badge cv-badge-urgent">
            <i className="bi bi-x-circle-fill"></i>
            Not Fixed
          </span>
        );
      default:
        return <span className="cv-badge cv-badge-low">{value}</span>;
    }
  }

  return <span className="cv-badge cv-badge-low">{value}</span>;
};
