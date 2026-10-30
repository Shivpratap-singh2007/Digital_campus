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
        {/* Navigation Breadcrumb */}
        <div className="mb-3">
          <Link to="/my-complaints" className="text-decoration-none text-muted small d-inline-flex align-items-center gap-1">
            <i className="bi bi-arrow-left"></i> Back to Submissions
          </Link>
        </div>

        <div className="cv-card">
          <div className="cv-card-header">
            <h4 className="mb-1 fw-bold text-dark">Submit Campus Report</h4>
            <p className="text-muted small mb-0">
              Your submission is evaluated with deterministic safety rules. Submitter identities are concealed in operational queues and require audited justification to disclose.
            </p>
          </div>

          <div className="cv-card-body p-4">
            {/* Compact Contextual Notice */}
            <div className="p-3 mb-4 rounded border text-secondary small d-flex align-items-start gap-2" style={{ backgroundColor: 'var(--bg-subtle)', borderColor: 'var(--border-subtle)', fontSize: '0.82rem' }}>
              <i className="bi bi-info-circle text-primary mt-0"></i>
              <div>
                <strong>Notice:</strong> This portal handles campus maintenance and facility issues. It is not an emergency-response service; for active physical safety or medical emergencies, contact campus emergency services directly.
              </div>
            </div>

            {error && (
              <div className="alert alert-danger py-2 small mb-4" role="alert">
                <i className="bi bi-exclamation-triangle-fill me-1"></i>
                {error}
              </div>
            )}

            {analyzingStatus && (
              <div className="alert alert-info py-2 small d-flex align-items-center gap-2 mb-4">
                <div className="spinner-border spinner-border-sm" role="status"></div>
                <span>{analyzingStatus}</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {/* Type and Category Row */}
              <div className="row g-3 mb-3">
                <div className="col-md-6">
                  <label className="form-label">
                    Report Type <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={submissionType}
                    onChange={(e) => setSubmissionType(e.target.value)}
                    required
                  >
                    <option value="complaint">Complaint (Fault or Issue)</option>
                    <option value="suggestion">Suggestion (Campus Improvement)</option>
                  </select>
                </div>

                <div className="col-md-6">
                  <label className="form-label">
                    Initial Category Estimate <span className="text-danger">*</span>
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
                  <div className="form-text">Choose your best estimate or select "Not sure" for automatic suggestion.</div>
                </div>
              </div>

              {/* Title */}
              <div className="mb-3">
                <label className="form-label">
                  Subject / Summary <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Broken water tap in 2nd floor restroom"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  minLength={5}
                  maxLength={200}
                  required
                />
              </div>

              {/* Location Row */}
              <div className="row g-3 mb-3">
                <div className="col-md-6">
                  <label className="form-label">
                    Campus Facility / Building <span className="text-danger">*</span>
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
                  <label className="form-label">Room or Specific Area</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Lab 204, East Stairwell, 1st Floor"
                    value={room}
                    onChange={(e) => setRoom(e.target.value)}
                    maxLength={100}
                  />
                </div>
              </div>

              {/* Description */}
              <div className="mb-3">
                <label className="form-label">
                  Detailed Description <span className="text-danger">*</span>
                </label>
                <textarea
                  className="form-control"
                  rows={5}
                  placeholder="Describe the issue factually: what is malfunctioning, observable hazards, or maintenance needed..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  minLength={10}
                  maxLength={4000}
                  required
                />
                <div className="form-text">
                  Minimum 10 characters. Plain factual descriptions ensure faster triage. For active emergencies, contact campus emergency services directly.
                </div>
              </div>

              {/* Photo Attachment */}
              <div className="mb-4">
                <label className="form-label">Supporting Photo (Optional)</label>
                <input
                  type="file"
                  className="form-control"
                  accept="image/jpeg,image/png"
                  onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                />
                <div className="form-text">
                  Max size: 5 MB (JPEG/PNG). EXIF metadata and GPS coordinates are automatically removed prior to storage.
                </div>
              </div>

              {/* Form Action Buttons */}
              <div className="d-flex justify-content-between align-items-center pt-3 border-top">
                <Link to="/my-complaints" className="btn btn-outline-secondary">
                  Cancel
                </Link>
                <button type="submit" className="btn btn-primary px-4" disabled={loading}>
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                      Saving & Submitting...
                    </>
                  ) : (
                    'Submit Report'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
