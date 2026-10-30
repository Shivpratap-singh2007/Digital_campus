import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
      <div className="container">
        <Link className="navbar-brand text-light fw-bold" to="/">
          <i className="bi bi-megaphone-fill text-warning me-2"></i>CampusVoice
        </Link>
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navContent"
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        <div className="collapse navbar-collapse" id="navContent">
          <ul className="navbar-nav me-auto mb-2 mb-lg-0">
            <li className="nav-item">
              <Link className="nav-link" to="/public-issues">
                <i className="bi bi-kanban me-1"></i>Public Issues
              </Link>
            </li>

            {user && (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/my-complaints">
                    <i className="bi bi-card-checklist me-1"></i>My Submissions
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link btn btn-outline-warning text-warning btn-sm ms-lg-2 px-3 my-1 my-lg-0" to="/new-complaint">
                    <i className="bi bi-plus-circle me-1"></i>Submit Report
                  </Link>
                </li>

                {user.is_handler && (
                  <li className="nav-item dropdown ms-lg-3">
                    <a
                      className="nav-link dropdown-toggle text-info"
                      href="#"
                      id="handlerDropdown"
                      role="button"
                      data-bs-toggle="dropdown"
                    >
                      <i className="bi bi-gear-fill me-1"></i>Operations ({user.is_admin ? 'Admin' : 'Handler'})
                    </a>
                    <ul className="dropdown-menu dropdown-menu-dark">
                      <li>
                        <Link className="dropdown-item" to="/admin/queue">
                          <i className="bi bi-list-task me-2"></i>Complaint Queue
                        </Link>
                      </li>
                      <li>
                        <Link className="dropdown-item" to="/admin/create-issue">
                          <i className="bi bi-folder-plus me-2"></i>Create Master Issue
                        </Link>
                      </li>
                      <li>
                        <Link className="dropdown-item" to="/admin/dashboard">
                          <i className="bi bi-graph-up me-2"></i>Metrics Dashboard
                        </Link>
                      </li>
                      {user.is_admin && (
                        <>
                          <li><hr className="dropdown-divider" /></li>
                          <li>
                            <Link className="dropdown-item" to="/admin/audit-log">
                              <i className="bi bi-journal-text me-2"></i>Restricted Audit Log
                            </Link>
                          </li>
                        </>
                      )}
                    </ul>
                  </li>
                )}
              </>
            )}
          </ul>

          <ul className="navbar-nav ms-auto">
            {user ? (
              <li className="nav-item dropdown">
                <a
                  className="nav-link dropdown-toggle d-flex align-items-center gap-1"
                  href="#"
                  id="userDropdown"
                  role="button"
                  data-bs-toggle="dropdown"
                >
                  <i className="bi bi-person-circle"></i>
                  <span>{user.full_name}</span>
                  {user.is_verified ? (
                    <span className="badge bg-success ms-1 small">Verified</span>
                  ) : (
                    <span className="badge bg-warning text-dark ms-1 small">Unverified</span>
                  )}
                </a>
                <ul className="dropdown-menu dropdown-menu-end">
                  <li className="dropdown-header text-muted small">
                    {user.email} ({user.role})
                  </li>
                  {!user.is_verified && (
                    <li>
                      <Link className="dropdown-item text-warning" to="/verify-email">
                        <i className="bi bi-envelope-exclamation me-2"></i>Verify College Email
                      </Link>
                    </li>
                  )}
                  <li>
                    <Link className="dropdown-item" to="/my-complaints">
                      <i className="bi bi-collection me-2"></i>My Complaints
                    </Link>
                  </li>
                  <li><hr className="dropdown-divider" /></li>
                  <li>
                    <button className="dropdown-item text-danger" onClick={handleLogout}>
                      <i className="bi bi-box-arrow-right me-2"></i>Log Out
                    </button>
                  </li>
                </ul>
              </li>
            ) : (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/login">
                    <i className="bi bi-box-arrow-in-right me-1"></i>Log In
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link btn btn-primary text-white btn-sm ms-2 px-3" to="/register">
                    Register
                  </Link>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  );
};

