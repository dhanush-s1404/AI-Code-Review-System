from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, CodeAnalysis, ReviewHistory, Admin
from ai_analyzer import analyze_code
from autofix import autofix_code
from language_detector import detect_language
from config import Config
import json

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create tables on first request
with app.app_context():
    db.create_all()


# ─── Routes ──────────────────────────────────────────────────────────────────


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    recent_analyses = (
        CodeAnalysis.query.filter_by(user_id=current_user.id)
        .order_by(CodeAnalysis.created_at.desc())
        .limit(5)
        .all()
    )
    total_analyses = CodeAnalysis.query.filter_by(user_id=current_user.id).count()
    avg_score = db.session.query(db.func.avg(CodeAnalysis.quality_score)).filter(
        CodeAnalysis.user_id == current_user.id
    ).scalar() or 0

    return render_template(
        "dashboard.html",
        recent_analyses=recent_analyses,
        total_analyses=total_analyses,
        avg_score=round(avg_score),
    )


@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        language = request.form.get("language", "").strip()
        filename = request.form.get("filename", "untitled").strip()

        if not code:
            flash("Please enter some code to analyze.", "error")
            return render_template("analyze.html")

        # Auto-detect language if not specified
        if not language or language == "auto":
            language = detect_language(code)

        # Perform AI analysis
        result = analyze_code(code, language)

        # Save to database
        analysis = CodeAnalysis(
            user_id=current_user.id,
            filename=filename,
            language=language,
            original_code=code,
            fixed_code=result.get("fixed_code", ""),
            analysis_result=json.dumps(result),
            quality_score=result.get("quality_score", 0),
        )
        db.session.add(analysis)
        db.session.commit()

        # Create review history entry
        review = ReviewHistory(
            user_id=current_user.id,
            code_id=analysis.id,
            status="Completed",
        )
        db.session.add(review)
        db.session.commit()

        return redirect(url_for("result", analysis_id=analysis.id))

    return render_template("analyze.html")


@app.route("/result/<int:analysis_id>")
@login_required
def result(analysis_id):
    analysis = CodeAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))

    result_data = json.loads(analysis.analysis_result) if analysis.analysis_result else {}

    return render_template("result.html", analysis=analysis, result=result_data)


@app.route("/history")
@login_required
def history():
    analyses = (
        CodeAnalysis.query.filter_by(user_id=current_user.id)
        .order_by(CodeAnalysis.created_at.desc())
        .all()
    )
    return render_template("history.html", analyses=analyses)


@app.route("/autofix/<int:analysis_id>", methods=["POST"])
@login_required
def autofix(analysis_id):
    analysis = CodeAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    specific_issue = request.form.get("issue", "")
    fixed_code = autofix_code(analysis.original_code, analysis.language, specific_issue)

    # Update the record
    analysis.fixed_code = fixed_code
    db.session.commit()

    return jsonify({"fixed_code": fixed_code})


@app.route("/delete/<int:analysis_id>", methods=["POST"])
@login_required
def delete_analysis(analysis_id):
    analysis = CodeAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("history"))

    ReviewHistory.query.filter_by(code_id=analysis.id).delete()
    db.session.delete(analysis)
    db.session.commit()

    flash("Analysis deleted.", "success")
    return redirect(url_for("history"))


# ─── Error Handlers ──────────────────────────────────────────────────────────


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
