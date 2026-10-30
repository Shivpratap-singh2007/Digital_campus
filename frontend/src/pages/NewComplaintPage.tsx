import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

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
  'Not sure',
];

export const NewComplaintPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [submissionKey, setSubmissionKey] = useState('');
  const [submissionType, setSubmissionType] = useState('complaint');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [userCategory, setUserCategory] = useState('Not sure');
  const [building, setBuilding] = useState(CAMPUS_LOCATIONS[0]);
  const [room, setRoom] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [analyzingStatus, setAnalyzingStatus] = useState<string | null>(null);

  // Initialize a unique submission key to prevent double clicks
  useEffect(() => {
    setSubmissionKey(crypto.randomUUID());
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!user?.is_verified && user?.role === 'user') {
      setError('You must verify your college email address before submitting reports.');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('submission_key', submissionKey);
      formData.append('submission_type', submissionType);
      formData.append('title', title.trim());
      formData.append('description', description.trim());
      formData.append('user_category', userCategory);
      formData.append('building', building);
      if (room.trim()) {
        formData.append('room', room.trim());
      }
      if (imageFile) {
        formData.append('image', imageFile);
      }

      // 1. Save complaint first before analysis
      const res = await api.post('/api/complaints', formData);
      const complaintId = res.id;

      // 2. Automatically request AI analysis
      setAnalyzingStatus('Running semantic categorization and explainable safety rules...');
      try {
        await api.post(`/api/complaints/${complaintId}/analyze`);
      } catch (analysisErr) {
        console.warn('Background analysis warning:', analysisErr);
        // Analysis failure must not delete or hide the saved complaint
      }

      navigate(`/complaints/${complaintId}`);
    } catch (err: any) {
      setError(err.message || 'Submission failed. Please check required fields.');
    } finally {
      setLoading(false);
      setAnalyzingStatus(null);
    }
  };

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <div className="card card-shadow">
          <div className="card-header bg-white py-3 border-bottom">
            <h4 className="mb-0 text-primary">
              <i className="bi bi-pencil-square me-2"></i>Submit Campus Complaint or Suggestion
            </h4>
            <p className="text-muted small mb-0 mt-1">
              Your report will be processed through deterministic safety rules and semantic clustering.
            </p>
          </div>
          <div className="card-body p-4">
            {error && <div className="alert alert-danger py-2 small">{error}</div>}
            {analyzingStatus && (
              <div className="alert alert-info py-2 small d-flex align-items-center gap-2">
                <div className="spinner-border spinner-border-sm" role="status"></div>
                <span>{analyzingStatus}</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label fw-semibold">
                    Submission Type <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={submissionType}
                    onChange={(e) => setSubmissionType(e.target.value)}
                    required
                  >
                    <option value="complaint">Complaint (Issue or Malfunction)</option>
                    <option value="suggestion">Suggestion (Campus Improvement)</option>
                  </select>
                </div>

                <div className="col-md-6">
                  <label className="form-label fw-semibold">
                    Category <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={userCategory}
                    onChange={(e) => setUserCategory(e.target.value)}
                    required
                  >
                    {CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                  <div className="form-text small text-muted">
                    Select your best estimate or choose "Not sure" for AI suggestions.
                  </div>
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label fw-semibold">
                  Title <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Brief summary of the issue (e.g., Broken water pipe in hostel corridor)"
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
                    Campus Location / Building <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={building}
                    onChange={(e) => setBuilding(e.target.value)}
                    required
                  >
                    {CAMPUS_LOCATIONS.map((loc) => (
                      <option key={loc} value={loc}>
                        {loc}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-md-6">
                  <label className="form-label fw-semibold">Room / Area (Optional)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g., Lab 204, 2nd Floor Corridor, North Wing"
                    value={room}
                    onChange={(e) => setRoom(e.target.value)}
                    maxLength={100}
                  />
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label fw-semibold">
                  Description <span className="text-danger">*</span>
                </label>
                <textarea
                  className="form-control"
                  rows={5}
                  placeholder="Provide clear, factual details regarding what is malfunctioning, hazard risks, or maintenance required..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  minLength={10}
                  maxLength={4000}
                  required
                />
                <div className="form-text text-muted small">
                  Min 10 characters, max 4000 characters.
                </div>
              </div>

              <div className="mb-4">
                <label className="form-label fw-semibold">Attach Photo (Optional)</label>
                <input
                  type="file"
                  className="form-control"
                  accept="image/jpeg,image/png"
                  onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                />
                <div className="form-text text-muted small">
                  Max 5 MB. Formats: JPEG or PNG. EXIF metadata (including GPS coordinates) will be automatically stripped before secure storage outside static web folders.
                </div>
              </div>

              <div className="d-flex justify-content-between align-items-center pt-2 border-top">
                <Link to="/my-complaints" className="btn btn-outline-secondary">
                  Cancel
                </Link>
                <button type="submit" className="btn btn-primary px-4" disabled={loading}>
                  {loading ? 'Submitting & Saving...' : 'Submit Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

