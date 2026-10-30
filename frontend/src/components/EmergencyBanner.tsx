import React from 'react';

export const EmergencyBanner: React.FC = () => {
  return (
    <>
      <div className="banner-emergency">
        <i className="bi bi-exclamation-triangle-fill me-1"></i>
        <strong>Emergency Notice:</strong> This portal is <strong>not</strong> an emergency-response service. For active physical safety or medical emergencies, contact campus emergency services directly.
      </div>
      <div className="banner-privacy">
        <i className="bi bi-shield-lock-fill me-1"></i>
        <strong>Privacy Architecture:</strong> Identity-restricted reporting, not guaranteed anonymity. Submitter names/emails are concealed from ordinary operational queues and require audited justification to reveal.
      </div>
    </>
  );
};

