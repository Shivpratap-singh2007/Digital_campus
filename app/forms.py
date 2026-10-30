import uuid
from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    SelectField,
    RadioField,
    IntegerField,
    HiddenField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError


def validate_college_domain(form, field):
    """
    Validates email domain using exact parsed-domain matching.
    Prevents substring bypasses (e.g. evilcampus.edu or fake@campus.edu.attacker.com).
    """
    email_val = (field.data or "").strip().lower()
    if "@" not in email_val:
        raise ValidationError("Invalid email address format.")
    
    parts = email_val.split("@")
    if len(parts) != 2:
        raise ValidationError("Invalid email address format.")
    
    domain = parts[1]
    allowed_domains = current_app.config.get("COLLEGE_EMAIL_DOMAINS", [])
    
    # Exact case-insensitive match of the domain part
    if domain not in [d.lower() for d in allowed_domains]:
        allowed_list = ", ".join(f"@{d}" for d in allowed_domains)
        raise ValidationError(
            f"Registration is restricted to college domains only ({allowed_list})."
        )


class RegistrationForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField(
        "College Email Address",
        validators=[DataRequired(), Email(), validate_college_domain],
        description="Must be your official college email (e.g., student@campus.edu).",
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    email = StringField("College Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class ResendVerificationForm(FlaskForm):
    email = StringField("College Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Resend Verification Email")


class ComplaintForm(FlaskForm):
    submission_type = SelectField(
        "Submission Type",
        choices=[("complaint", "Complaint (Issue or Malfunction)"), ("suggestion", "Suggestion (Campus Improvement)")],
        default="complaint",
        validators=[DataRequired()],
    )
    title = StringField(
        "Title",
        validators=[
            DataRequired(),
            Length(min=5, max=200, message="Title must be between 5 and 200 characters."),
        ],
    )
    description = TextAreaField(
        "Description",
        validators=[
            DataRequired(),
            Length(min=10, max=4000, message="Description must be between 10 and 4000 characters."),
        ],
        description="Please describe what happened, where, and any relevant details.",
    )
    user_category = SelectField(
        "Category",
        choices=[
            ("Infrastructure", "Infrastructure"),
            ("Sanitation", "Sanitation"),
            ("Academics", "Academics"),
            ("Student services", "Student services"),
            ("IT/connectivity", "IT/connectivity"),
            ("Other", "Other"),
            ("Not sure", "Not sure"),
        ],
        default="Not sure",
        validators=[DataRequired()],
    )
    building = SelectField(
        "Campus Location / Building",
        validators=[DataRequired()],
    )
    room = StringField("Room / Area (Optional)", validators=[Length(max=100)])
    image = FileField(
        "Attach Photo (Optional - JPEG or PNG, max 5 MB)",
        validators=[FileAllowed(["jpg", "jpeg", "png"], "Only JPEG and PNG images are allowed.")],
    )
    idempotency_token = HiddenField("Idempotency Token", validators=[DataRequired()])
    submit = SubmitField("Submit Report")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate building choices dynamically from config
        locations = current_app.config.get("CAMPUS_LOCATIONS", [])
        self.building.choices = [(loc, loc) for loc in locations]
        if not self.idempotency_token.data:
            self.idempotency_token.data = uuid.uuid4().hex


class StatusUpdateForm(FlaskForm):
    new_status = SelectField(
        "New Operational Status",
        choices=[
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved"),
        ],
        validators=[DataRequired()],
    )
    note = TextAreaField(
        "Operational Note / Reason",
        validators=[
            DataRequired(),
            Length(min=5, max=2000, message="Note must be between 5 and 2000 characters."),
        ],
        description="Required explanation for this status update. If resolving, describe the fix.",
    )
    submit = SubmitField("Update Status")


class CreateIssueForm(FlaskForm):
    title = StringField("Issue Title", validators=[DataRequired(), Length(min=5, max=200)])
    description = TextAreaField(
        "Synthesized Issue Description",
        validators=[DataRequired(), Length(min=10, max=4000)],
        description="Public/operational summary. Avoid copying personal identifiers.",
    )
    category = SelectField(
        "Category",
        choices=[
            ("Infrastructure", "Infrastructure"),
            ("Sanitation", "Sanitation"),
            ("Academics", "Academics"),
            ("Student services", "Student services"),
            ("IT/connectivity", "IT/connectivity"),
            ("Other", "Other"),
        ],
        validators=[DataRequired()],
    )
    building = SelectField("Building / Location", validators=[DataRequired()])
    room = StringField("Room / Area (Optional)", validators=[Length(max=100)])
    priority = SelectField(
        "Priority",
        choices=[
            ("Urgent review", "Urgent review"),
            ("High", "High"),
            ("Normal", "Normal"),
            ("Low", "Low"),
        ],
        default="Normal",
        validators=[DataRequired()],
    )
    submit = SubmitField("Create Issue")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locations = current_app.config.get("CAMPUS_LOCATIONS", [])
        self.building.choices = [(loc, loc) for loc in locations]


class LinkComplaintForm(FlaskForm):
    complaint_id = IntegerField("Complaint ID", validators=[DataRequired()])
    relationship_type = SelectField(
        "Relationship Type",
        choices=[
            ("same_incident", "Same Incident (Direct duplicate or report of this problem)"),
            ("related_only", "Related Only (Connected issue in same area)"),
        ],
        default="same_incident",
        validators=[DataRequired()],
    )
    submit = SubmitField("Link to Issue")


class ResolutionFeedbackForm(FlaskForm):
    response = RadioField(
        "Has the issue been resolved to your satisfaction?",
        choices=[
            ("fixed", "Fixed — The issue has been completely resolved."),
            ("partially_fixed", "Partially fixed — Some work was done, but problems remain."),
            ("not_fixed", "Not fixed — The reported problem still persists."),
        ],
        validators=[DataRequired(message="Please select your resolution rating.")],
    )
    comments = TextAreaField(
        "Optional Submitter Comments",
        validators=[Length(max=1000)],
        description="Provide details, especially if partially fixed or not fixed.",
    )
    submit = SubmitField("Submit Verified Feedback")


class IdentityRevealForm(FlaskForm):
    justification = TextAreaField(
        "Required Operational Justification",
        validators=[
            DataRequired(),
            Length(
                min=10,
                max=1000,
                message="A detailed reason (min 10 characters) is required to access submitter identity.",
            ),
        ],
        description="Explain why disclosing the submitter's identity is strictly necessary for resolving this issue.",
    )
    submit = SubmitField("Confirm Identity Reveal & Record Audit Log")
