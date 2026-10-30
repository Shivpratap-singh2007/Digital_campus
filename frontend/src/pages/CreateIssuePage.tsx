import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { api } from '../api/client';

const CAMPUS_LOCATIONS = [
  'Academic Block A',
  'Academic Block B',
  'Central Library',
  'Computer Center / IT Labs',
  'Boys Hostel 1',
  'Boys Hostel 2',
  'Girls Hostel 1',
  'Girls Hostel 2',
  'Main Cafeteria & Food Court',
  'Sports Complex & Gymnasium',
  'Administrative Block',
  'Health Center',
  'Campus Grounds & Walkways',
  'Other / Outdoor',
];

const CATEGORIES = [
  'Infrastructure',
  'Sanitation',
  'Academics',
  'Student services',
  'IT/connectivity',
  'Other',
];

export const CreateIssuePage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const seedId = queryParams.get('seed_id');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [building, setBuilding] = useState(CAMPUS_LOCATIONS[0]);
  const [room, setRoom] = useState('');
  const [priority, setPriority] = useState('Normal');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // If seedId is present, fetch complaint to pre-fill
  useEffect(() => {
    if (seedId) {
      api.get(`/api/complaints/${seedId}`).then((c) => {
        setTitle(`Issue: ${c.title}`);
        setDescription(c.description);
        if (CATEGORIES.includes(c.display_category)) {
          setCategory(c.display_category);
        }
        setBuilding(c.building);
        setRoom(c.room || '');
        setPriority(c.display_priority);
      }).catch((err) => {
        console.warn('Could not load seed complaint:', err);
      });
    }
  }, [seedId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await api.post('/api/issues', {
        title,
        description,
        category,
        building,
        room,
        priority,
        seed_complaint_id: seedId ? parseInt(seedId, 10) : undefined,
      });
      navigate(`/admin/issues/${res.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create issue.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <div className="card card-shadow">
          <div className="card-header bg-white py-3 border-bottom">
            <h4 className="mb-0 text-primary">
              <i className="bi bi-folder-plus me-2"></i>Synthesize Operational Issue
            </h4>
            <p className="text-muted small mb-0 mt-1">
              Consolidate related complaints into an addressable campus task without modifying original submissions.
            </p>
          </div>
          <div className="card-body p-4">
            {seedId && (
              <div className="alert alert-info py-2 small mb-4">
                <i className="bi bi-info-circle me-1"></i>
                Pre-filled from seed Complaint #{seedId}. Submitting will link this complaint automatically.
              </div>
            )}
            {error && <div className="alert alert-danger py-2 small">{error}</div>}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label fw-semibold">
                  Issue Title <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Synthesized title (e.g., Computer Lab 102 Electrical Hazard)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  minLength={5}
                  maxLength={200}
                  required
                />
              </div>

              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label fw-semibold">
                    Category <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    required
                  >
                    {CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className="form-label fw-semibold">
                    Priority <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    required
                  >
                    <option value="Urgent review">Urgent review</option>
                    <option value="High">High</option>
                    <option value="Normal">Normal</option>
                    <option value="Low">Low</option>
                  </select>
                </div>
              </div>

              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label fw-semibold">
                    Building / Location <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={building}
                    onChange={(e) => setBuilding(e.target.value)}
                    required
                  >
                    {CAMPUS_LOCATIONS.map((loc) => (
                      <option key={loc} value={loc}>{loc}</option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className="form-label fw-semibold">Room / Area (Optional)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g., Lab 102"
                    value={room}
                    onChange={(e) => setRoom(e.target.value)}
                    maxLength={100}
                  />
                </div>
              </div>

              <div className="mb-4">
                <label className="form-label fw-semibold">
                  Synthesized Description <span className="text-danger">*</span>
                </label>
                <textarea
                  className="form-control"
                  rows={4}
                  placeholder="Public/operational summary of the underlying problem..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  minLength={10}
                  maxLength={4000}
                  required
                />
                <div className="form-text small text-muted">
                  Avoid copying submitter personal identifying info into the synthesized description.
                </div>
              </div>

              <div className="d-flex justify-content-between align-items-center pt-2 border-top">
                <Link to="/admin/queue" className="btn btn-outline-secondary">
                  Cancel
                </Link>
                <button type="submit" className="btn btn-primary px-4" disabled={loading}>
                  {loading ? 'Creating...' : 'Create Master Issue'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

