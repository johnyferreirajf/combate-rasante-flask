from datetime import datetime
from app import db


class EmployeeFile(db.Model):
    __tablename__ = "employee_files"

    id = db.Column(db.Integer, primary_key=True)

    stored_filename = db.Column(db.String(255), nullable=False)  # on disk
    original_filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(180), nullable=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(60), nullable=True)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    uploader = db.relationship("Employee", backref="files")
