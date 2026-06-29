import json
import re
import os
from config import Config


def analyze_code(code: str, language: str) -> dict:
    """
    Analyze submitted code using an AI provider and return structured results.
    Returns a dict with: errors, severity, suggestions, fixed_code, quality_score.
    """
    provider = Config.AI_PROVIDER

    prompt = _build_prompt(code, language)

    if provider == "anthropic":
        return _analyze_with_anthropic(prompt, code, language)
    elif provider == "openai":
        return _analyze_with_openai(prompt, code, language)
    else:
        return _fallback_analysis(code, language)


def _build_prompt(code: str, language: str) -> str:
    return f"""You are an expert code reviewer. Analyze the following {language} code and provide a detailed review.

Return your response as valid JSON with exactly this structure:
{{
    "errors": [
        {{
            "line": <line_number>,
            "type": "<error_type>",
            "severity": "<Critical|High|Medium|Low>",
            "description": "<description of the issue>",
            "suggestion": "<how to fix it>"
        }}
    ],
    "quality_score": <integer from 0 to 100>,
    "summary": "<brief overall assessment>",
    "fixed_code": "<corrected version of the code>"
}}

If the code is perfect, return an empty errors array and a high quality score.

Code to review:
```{language}
{code}
```"""


def _analyze_with_anthropic(prompt: str, code: str, language: str) -> dict:
    try:
        import anthropic

        api_key = Config.ANTHROPIC_API_KEY
        if not api_key:
            return _fallback_analysis(code, language)

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        return _parse_ai_response(response_text)

    except Exception as e:
        print(f"Anthropic API error: {e}")
        return _fallback_analysis(code, language)


def _analyze_with_openai(prompt: str, code: str, language: str) -> dict:
    try:
        from openai import OpenAI

        api_key = Config.OPENAI_API_KEY
        if not api_key:
            return _fallback_analysis(code, language)

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )

        response_text = response.choices[0].message.content
        return _parse_ai_response(response_text)

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return _fallback_analysis(code, language)


def _parse_ai_response(response_text: str) -> dict:
    """Extract JSON from the AI response text."""
    try:
        # Try direct JSON parse
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in the response
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Return a basic structure if parsing fails
    return {
        "errors": [],
        "quality_score": 50,
        "summary": "Analysis completed but response parsing failed. Raw response available.",
        "fixed_code": "",
        "raw_response": response_text,
    }


def _fallback_analysis(code: str, language: str) -> dict:
    """
    Basic static analysis when no AI API is available.
    Checks for common issues based on language patterns.
    """
    errors = []
    lines = code.split("\n")
    score = 85

    for i, line in enumerate(lines, 1):
        # Check for very long lines
        if len(line) > 120:
            errors.append({
                "line": i,
                "type": "Style",
                "severity": "Low",
                "description": f"Line exceeds 120 characters ({len(line)} chars)",
                "suggestion": "Break this line into multiple shorter lines for readability.",
            })
            score -= 2

        # Check for trailing whitespace
        if line != line.rstrip():
            errors.append({
                "line": i,
                "type": "Style",
                "severity": "Low",
                "description": "Trailing whitespace detected",
                "suggestion": "Remove trailing whitespace.",
            })
            score -= 1

    # Language-specific checks
    if language == "Python":
        errors.extend(_check_python(lines, code))
    elif language in ("JavaScript", "TypeScript"):
        errors.extend(_check_javascript(lines, code))

    # Deduct for errors found
    critical_count = sum(1 for e in errors if e["severity"] == "Critical")
    high_count = sum(1 for e in errors if e["severity"] == "High")
    score -= critical_count * 15 + high_count * 8
    score = max(0, min(100, score))

    return {
        "errors": errors,
        "quality_score": score,
        "summary": f"Static analysis found {len(errors)} issue(s). "
                   f"AI-powered analysis unavailable (no API key configured).",
        "fixed_code": "",
    }


def _check_python(lines: list, code: str) -> list:
    errors = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check for bare except
        if re.match(r"^\s*except\s*:", line):
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "Medium",
                "description": "Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt",
                "suggestion": "Use 'except Exception:' to catch only standard exceptions.",
            })

        # Check for eval usage
        if "eval(" in line:
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "Critical",
                "description": "Use of eval() is a security risk",
                "suggestion": "Avoid eval(). Use ast.literal_eval() for safe evaluation of literals.",
            })

        # Check for hardcoded passwords
        if re.search(r"password\s*=\s*['\"]", line, re.IGNORECASE):
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "High",
                "description": "Possible hardcoded password detected",
                "suggestion": "Use environment variables or a secrets manager for sensitive data.",
            })

    return errors


def _check_javascript(lines: list, code: str) -> list:
    errors = []
    for i, line in enumerate(lines, 1):
        # Check for var usage
        if re.match(r"^\s*var\s+", line):
            errors.append({
                "line": i,
                "type": "Best Practice",
                "severity": "Medium",
                "description": "'var' is function-scoped and can lead to bugs",
                "suggestion": "Use 'let' or 'const' instead of 'var'.",
            })

        # Check for == instead of ===
        if re.search(r"[^!=]==[^=]", line):
            errors.append({
                "line": i,
                "type": "Best Practice",
                "severity": "Medium",
                "description": "Use of loose equality (==) can cause type coercion bugs",
                "suggestion": "Use strict equality (===) instead.",
            })

    return errors
