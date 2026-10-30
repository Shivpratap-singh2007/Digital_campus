import React from 'react';

export const EmergencyBanner: React.FC = () => {
  return (
    <>
      <div className="banner-emergency">
        <i className="bi bi-shield-exclamation me-1"></i>
        <strong>Emergency Notice:</strong> This portal is not an emergency-response service. For active physical safety or medical emergencies, contact campus emergency services directly.
      </div>
      <div className="banner-privacy">
        <i className="bi bi-shield-lock me-1"></i>
        <strong>Privacy Architecture:</strong> Submitter identities are concealed on ordinary operational dashboards and require audited justification to disclose.
      </div>
    </>
  );
};
