import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

export const PublicIssuesPage: React.FC = () => {
  const [issues, setIssues] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  useEffect(() => {
    async function loadIssues() {
      try {
        const data = await api.get('/api/issues');
        setIssues(data.issues || []);
      } catch (err) {
        console.error('Failed to load public issues:', err);
      } finally {
        setLoading(false);
      }
    }
    loadIssues();
  }, []);

  const categories = useMemo(() => {
    const set = new Set<string>();
    issues.forEach((i) => {
      if (i.category) set.add(i.category);
    });
    return Array.from(set).sort();
  }, [issues]);

  const filteredIssues = useMemo(() => {
    return issues.filter((issue) => {
      if (selectedCategory && issue.category !== selectedCategory) return false;
      if (selectedStatus && issue.status !== selectedStatus) return false;
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesTitle = issue.title?.toLowerCase().includes(term);
        const matchesDesc = issue.description?.toLowerCase().includes(term);
        const matchesBuilding = issue.building?.toLowerCase().includes(term);
        const matchesRoom = issue.room?.toLowerCase().includes(term);
        if (!matchesTitle && !matchesDesc && !matchesBuilding && !matchesRoom) return false;
      }
      return true;
    });
  }, [issues, selectedCategory, selectedStatus, searchTerm]);

  return (
    <div>
      {/* Header */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <h3 className="mb-0 fw-bold">Public Issues Board</h3>
            <span className="cv-badge cv-badge-low">{issues.length} Synthesized</span>
          </div>
          <p className="text-muted small mb-0">
            Transparent campus operations tracking verified maintenance and infrastructure progress.
          </p>
        </div>
        <Link to="/new-complaint" className="btn btn-primary d-inline-flex align-items-center gap-2">
          <i className="bi bi-plus-lg"></i>
          <span>Report an Issue</span>
        </Link>
      </div>

      {/* Filter Toolbar */}
      <div className="cv-card mb-4">
        <div className="cv-card-body p-3">
          <div className="row g-2 align-items-center">
            <div className="col-md-5">
              <div className="input-group">
                <span className="input-group-text bg-white border-end-0 text-muted">
                  <i className="bi bi-search"></i>
                </span>
                <input
                  type="text"
                  className="form-control border-start-0 ps-0"
                  placeholder="Filter by title, description, or campus building..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="col-md-3">
              <select
                className="form-select"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <option value="">All Categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-2">
              <select
                className="form-select"
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="submitted">Submitted</option>
                <option value="under_review">Under Review</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
            <div className="col-md-2">
              <button
                type="button"
                className="btn btn-outline-secondary w-100"
                onClick={() => {
                  setSearchTerm('');
                  setSelectedCategory('');
                  setSelectedStatus('');
                }}
              >
                Reset Filters
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Issues Table */}
      {loading ? (
        <div className="cv-card p-5 text-center text-muted">
          <div className="spinner-border spinner-border-sm text-secondary me-2" role="status"></div>
          Loading operational issues...
        </div>
      ) : filteredIssues.length > 0 ? (
        <div className="cv-card overflow-hidden">
          <div className="table-responsive">
            <table className="cv-table">
              <thead>
                <tr>
                  <th style={{ width: '80px' }}>Issue ID</th>
                  <th>Summary & Scope</th>
                  <th>Campus Location</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Verified Feedback</th>
                </tr>
              </thead>
              <tbody>
                {filteredIssues.map((issue) => (
                  <tr key={issue.id}>
                    <td>
                      <span className="font-monospace fw-semibold text-secondary">#{issue.id}</span>
                    </td>
                    <td style={{ maxWidth: '340px' }}>
                      <div className="fw-semibold text-dark mb-0">{issue.title}</div>
                      <div className="text-muted small text-truncate" title={issue.description}>
                        {issue.description}
                      </div>
                    </td>
                    <td>
                      <div className="fw-medium text-dark">{issue.building}</div>
                      {issue.room && <div className="text-muted small">{issue.room}</div>}
                    </td>
                    <td>
                      <span className="cv-badge cv-badge-low">{issue.category}</span>
                    </td>
                    <td>
                      <StatusBadge type="priority" value={issue.priority} />
                    </td>
                    <td>
                      <StatusBadge type="status" value={issue.status} />
                    </td>
                    <td>
                      {issue.resolution_round_status ? (
                        <StatusBadge type="feedback_round" value={issue.resolution_round_status} />
                      ) : (
                        <span className="text-muted small">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="cv-card text-center p-5">
          <div className="text-muted mb-2">
            <i className="bi bi-inbox" style={{ fontSize: '2.5rem' }}></i>
          </div>
          <h5 className="fw-semibold text-dark mb-1">No Matching Issues Found</h5>
          <p className="text-muted small mb-3">
            {issues.length === 0
              ? 'No operational issues have been synthesized yet.'
              : 'Try clearing your filters or search keywords to view other records.'}
          </p>
          {(searchTerm || selectedCategory || selectedStatus) && (
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={() => {
                setSearchTerm('');
                setSelectedCategory('');
                setSelectedStatus('');
              }}
            >
              Clear Active Filters
            </button>
          )}
        </div>
      )}
    </div>
  );
};
