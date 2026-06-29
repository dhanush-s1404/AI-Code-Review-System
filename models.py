from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="User")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    code_analyses = db.relationship("CodeAnalysis", back_populates="user", lazy=True)
    reviews = db.relationship("ReviewHistory", back_populates="user", lazy=True)

    def __repr__(self):
        return f"<User {self.name}>"


class CodeAnalysis(db.Model):
    __tablename__ = "code_analysis"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), default="untitled")
    language = db.Column(db.String(50), nullable=False)
    original_code = db.Column(db.Text, nullable=False)
    fixed_code = db.Column(db.Text)
    analysis_result = db.Column(db.Text)
    quality_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="code_analyses")
    reviews = db.relationship("ReviewHistory", back_populates="code", lazy=True)

    def __repr__(self):
        return f"<CodeAnalysis {self.id} - {self.language}>"


class ReviewHistory(db.Model):
    __tablename__ = "review_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code_id = db.Column(db.Integer, db.ForeignKey("code_analysis.id"), nullable=False)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="Completed")

    user = db.relationship("User", back_populates="reviews")
    code = db.relationship("CodeAnalysis", back_populates="reviews")

    def __repr__(self):
        return f"<ReviewHistory {self.id} - {self.status}>"


class Admin(db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Admin {self.name}>"
