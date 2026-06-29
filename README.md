# AI Based Code Review System

An intelligent web-based application that automates source code analysis using Artificial Intelligence. Submit code in multiple languages, get instant feedback on errors, security vulnerabilities, code quality scores, and corrected code suggestions.

## Features

- **Automatic Error Detection** – Detects syntax errors, logical flaws, and security issues
- **Multi-Language Support** – Python, JavaScript, Java, C++, C, C#, PHP, Ruby, Go, Rust
- **Code Quality Score** – Generates a quality score (0–100) for submitted code
- **Severity Classification** – Errors categorized as Critical, High, Medium, or Low
- **AI-Powered Suggestions** – Provides fix recommendations and corrected code
- **User Authentication** – Secure login/registration system
- **History Tracking** – View all past code analyses

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite (via SQLAlchemy)
- **AI:** Anthropic Claude / OpenAI GPT (configurable)

## Setup

1. **Clone and navigate to the project:**
   ```bash
   cd AI_Project
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   copy .env.example .env
   ```
   Edit `.env` and add your API key (Anthropic or OpenAI).

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Open in browser:**
   ```
   http://127.0.0.1:5000/
   ```

## Project Structure

```
AI_Project/
├── app.py              # Main Flask application (routes)
├── models.py           # Database models (SQLAlchemy)
├── ai_analyzer.py      # AI-powered code analysis engine
├── autofix.py          # AI-powered auto-fix functionality
├── language_detector.py# Programming language detection
├── config.py           # Application configuration
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates (Jinja2)
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── analyze.html
│   ├── result.html
│   └── history.html
└── static/             # Static assets
    ├── css/style.css
    └── js/main.js
```

## Notes

- The system works with a **fallback static analyzer** if no AI API key is configured — you can test it without any API key.
- To enable full AI-powered reviews, add your Anthropic or OpenAI API key to the `.env` file.
