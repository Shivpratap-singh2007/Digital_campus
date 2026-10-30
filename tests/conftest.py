import pytest
import os
import shutil
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, Complaint, Issue, IssueComplaintLink, ResolutionRound


@pytest.fixture
def app():
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()

    # Clean up test uploads
    if os.path.exists(TestingConfig.UPLOAD_FOLDER):
        shutil.rmtree(TestingConfig.UPLOAD_FOLDER, ignore_errors=True)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def verified_user(app):
    user = User(
        email="student.test@campus.edu",
        full_name="Test Student",
        role="user",
        is_verified=True,
    )
    user.set_password("StudentPass123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def unverified_user(app):
    user = User(
        email="unverified@campus.edu",
        full_name="Unverified Student",
        role="user",
        is_verified=False,
    )
    user.set_password("StudentPass123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def handler_user(app):
    user = User(
        email="handler.ops@campus.edu",
        full_name="Facilities Handler",
        role="handler",
        is_verified=True,
    )
    user.set_password("HandlerPass123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(app):
    user = User(
        email="admin.security@campus.edu",
        full_name="Security Administrator",
        role="admin",
        is_verified=True,
    )
    user.set_password("AdminPass123!")
    db.session.add(user)
    db.session.commit()
    return user

