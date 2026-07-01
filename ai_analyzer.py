import ast
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
            model="claude-opus-4.8",
            max_tokens=4096,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = _extract_anthropic_text(message)
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


def _extract_anthropic_text(message_obj) -> str:
    """Extract human-readable text from an Anthropic Message response."""
    if not message_obj:
        return ""

    if hasattr(message_obj, "content"):
        content = message_obj.content
        if content:
            first = content[0]
            if hasattr(first, "text"):
                return first.text
            if isinstance(first, dict):
                return first.get("text", "")

    if isinstance(message_obj, dict):
        content_list = message_obj.get("content", [])
        if isinstance(content_list, list) and content_list:
            first = content_list[0]
            if isinstance(first, dict):
                return first.get("text", "")

    return str(message_obj)


def _fallback_analysis(code: str, language: str) -> dict:
    """
    Enhanced static analysis when no AI API is available.
    Performs language-aware checks, syntax validation, formatting cleanup, and heuristic scoring.
    """
    errors = []
    lines = code.split("\n")

    errors.extend(_check_common_issues(lines))
    errors.extend(_check_language_specific(lines, code, language))

    quality_score = _calculate_quality_score(errors, lines, code)
    fixed_code = _auto_fix_basic_issues(code)

    return {
        "errors": errors,
        "quality_score": quality_score,
        "summary": (
            f"Static analysis found {len(errors)} issue(s). "
            f"AI-powered analysis unavailable or not configured."
        ),
        "fixed_code": fixed_code,
    }


def _check_common_issues(lines: list) -> list:
    errors = []
    blank_line_count = 0
    duplicates = {}

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if len(line) > 120:
            errors.append({
                "line": i,
                "type": "Style",
                "severity": "Low",
                "description": f"Line exceeds 120 characters ({len(line)} chars).",
                "suggestion": "Break this line into smaller statements or wrap long expressions.",
            })

        if line != line.rstrip():
            errors.append({
                "line": i,
                "type": "Style",
                "severity": "Low",
                "description": "Trailing whitespace detected.",
                "suggestion": "Remove trailing whitespace from this line.",
            })

        if "\t" in line:
            errors.append({
                "line": i,
                "type": "Style",
                "severity": "Low",
                "description": "Tab character detected instead of spaces.",
                "suggestion": "Use spaces for indentation to keep formatting consistent.",
            })

        if stripped.startswith("# TODO") or stripped.startswith("// TODO") or stripped.startswith("# FIXME") or stripped.startswith("// FIXME"):
            errors.append({
                "line": i,
                "type": "Maintainability",
                "severity": "Low",
                "description": "TODO/FIXME comment left in the code.",
                "suggestion": "Resolve the outstanding task or remove the placeholder comment.",
            })

        if stripped == "":
            blank_line_count += 1
        else:
            blank_line_count = 0

        if blank_line_count > 2:
            errors.append({
                "line": i,
                "type": "Style",
                "severity": "Low",
                "description": "More than two consecutive blank lines.",
                "suggestion": "Limit consecutive blank lines to improve readability.",
            })
            blank_line_count = 0

        duplicates.setdefault(stripped, []).append(i)

    for text, occurrence in duplicates.items():
        if text and len(occurrence) > 1 and len(text) < 100:
            errors.append({
                "line": occurrence[1],
                "type": "Maintainability",
                "severity": "Low",
                "description": "Duplicate code block detected.",
                "suggestion": "Consider extracting the repeated code into a reusable function or helper.",
            })
            break

    return errors


def _find_case_conflicts(lines: list) -> list:
    errors = []
    identifiers = {}
    for i, line in enumerate(lines, 1):
        for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", line):
            key = token.lower()
            if key in identifiers and token not in identifiers[key]:
                errors.append({
                    "line": i,
                    "type": "Case Sensitivity",
                    "severity": "Medium",
                    "description": f"Identifier '{token}' differs only by case from '{identifiers[key][0]}'.",
                    "suggestion": "Use a consistent identifier name to avoid confusion on case-sensitive platforms.",
                })
                identifiers[key].append(token)
            else:
                identifiers.setdefault(key, []).append(token)
    return errors


def _check_keyword_case(lines: list, language: str) -> list:
    errors = []
    python_keywords = [
        "If", "Else", "For", "While", "Try", "Except", "With", "Import",
        "From", "Class", "Def", "Return", "Lambda", "Pass", "Raise", "Yield"
    ]
    js_keywords = [
        "If", "Else", "For", "While", "Switch", "Case", "Default", "Try",
        "Catch", "Finally", "Function", "Return", "Const", "Let", "Var",
        "Class", "Import", "Export", "Async", "Await", "Break", "Continue",
        "Throw", "New", "This"
    ]

    keywords = python_keywords if language == "Python" else js_keywords
    for i, line in enumerate(lines, 1):
        for word in keywords:
            if re.search(rf"\b{word}\b", line) and word != word.lower():
                errors.append({
                    "line": i,
                    "type": "Keyword Case",
                    "severity": "Medium",
                    "description": f"'{word}' is used with incorrect casing.",
                    "suggestion": f"Use lowercase '{word.lower()}' for {language} keywords.",
                })
    return errors


def _check_javascript_semicolons(lines: list) -> list:
    errors = []
    statement_pattern = re.compile(r"^\s*(?:const|let|var|return|throw|break|continue|await|import|export|[A-Za-z_$][A-Za-z0-9_$]*\s*=|[A-Za-z_$][A-Za-z0-9_$]*\(|console\.|document\.|window\.)")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "/*", "*", "}", "{", "case", "default", "else", "catch", "finally", "return", "break", "continue", "throw", "export", "import")):
            continue
        if not statement_pattern.match(stripped):
            continue
        if stripped.endswith((";", "{", "}", ",", ":", ")", "]")):
            continue
        if "//" in stripped:
            stripped = stripped.split("//")[0].rstrip()
        if stripped and not stripped.endswith((";", "{", "}")):
            errors.append({
                "line": i,
                "type": "Syntax",
                "severity": "Low",
                "description": "Possible missing semicolon at the end of the statement.",
                "suggestion": "Add a semicolon to terminate the statement in JavaScript/TypeScript.",
            })
    return errors


def _check_language_specific(lines: list, code: str, language: str) -> list:
    errors = []

    if language == "Python":
        errors.extend(_check_python(lines, code))
        errors.extend(_check_python_syntax(code))
        errors.extend(_check_keyword_case(lines, language))
    elif language in ("JavaScript", "TypeScript"):
        errors.extend(_check_javascript(lines, code))
        errors.extend(_check_javascript_style(lines, code))
        errors.extend(_check_javascript_semicolons(lines))
        errors.extend(_check_keyword_case(lines, language))
    else:
        errors.extend(_check_generic_language(lines, language))

    errors.extend(_find_case_conflicts(lines))
    return errors


def _check_python_syntax(code: str) -> list:
    errors = []
    try:
        ast.parse(code)
    except SyntaxError as exc:
        errors.append({
            "line": exc.lineno or 1,
            "type": "Syntax",
            "severity": "High",
            "description": str(exc).strip(),
            "suggestion": "Fix the syntax error before rerunning analysis.",
        })
    return errors


def _check_python(lines: list, code: str) -> list:
    errors = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if re.match(r"^\s*except\s*:", line):
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "Medium",
                "description": "Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt.",
                "suggestion": "Use 'except Exception:' or specific exception types instead.",
            })

        if "eval(" in line:
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "Critical",
                "description": "Use of eval() is a security risk.",
                "suggestion": "Avoid eval(); prefer ast.literal_eval() or parse input explicitly.",
            })

        if re.search(r"password\s*=\s*['\"]", line, re.IGNORECASE):
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "High",
                "description": "Possible hardcoded password detected.",
                "suggestion": "Use environment variables or secret management for credentials.",
            })

        if re.search(r"\bsubprocess\.Popen\b|\bsubprocess\.call\b|\bos\.system\b", line):
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "High",
                "description": "Subprocess execution can introduce command injection risks.",
                "suggestion": "Validate inputs carefully or avoid shell execution where possible.",
            })

        if re.match(r"^\s*def\s+\w+\(.*\):", line) and len(line) > 100:
            errors.append({
                "line": i,
                "type": "Maintainability",
                "severity": "Low",
                "description": "Function signature is long and hard to read.",
                "suggestion": "Break long parameter lists onto multiple lines.",
            })

        if stripped.startswith("assert "):
            errors.append({
                "line": i,
                "type": "Reliability",
                "severity": "Medium",
                "description": "Assertions are not a substitute for proper error handling.",
                "suggestion": "Use explicit exception handling for production code.",
            })

    return errors


def _check_javascript(lines: list, code: str) -> list:
    errors = []
    for i, line in enumerate(lines, 1):
        if re.match(r"^\s*var\s+", line):
            errors.append({
                "line": i,
                "type": "Best Practice",
                "severity": "Medium",
                "description": "'var' is function-scoped and can lead to bugs.",
                "suggestion": "Use 'let' or 'const' instead of 'var'.",
            })

        if re.search(r"[^!=]==[^=]", line):
            errors.append({
                "line": i,
                "type": "Best Practice",
                "severity": "Medium",
                "description": "Use of loose equality (==) can cause type coercion bugs.",
                "suggestion": "Use strict equality (===) instead.",
            })

        if "eval(" in line:
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "Critical",
                "description": "Use of eval() is a security risk.",
                "suggestion": "Avoid eval() and use safer parsing alternatives.",
            })

        if re.search(r"document\.write\(|innerHTML\s*=", line):
            errors.append({
                "line": i,
                "type": "Security",
                "severity": "High",
                "description": "Potential XSS risk from dynamic HTML insertion.",
                "suggestion": "Use safe DOM methods and sanitize user-controlled input.",
            })

    return errors


def _check_javascript_style(lines: list, code: str) -> list:
    errors = []
    for i, line in enumerate(lines, 1):
        if re.search(r"console\.log\(", line):
            errors.append({
                "line": i,
                "type": "Debug",
                "severity": "Low",
                "description": "console.log statement left in production code.",
                "suggestion": "Remove debugging output before deployment.",
            })

        if re.search(r"\bfunction\s*\(\)|=>\s*\{", line) and line.strip().startswith("function"):
            errors.append({
                "line": i,
                "type": "Maintainability",
                "severity": "Low",
                "description": "Consider using arrow functions for shorter function syntax.",
                "suggestion": "Use modern JavaScript syntax with arrow functions where appropriate.",
            })

    return errors


def _check_generic_language(lines: list, language: str) -> list:
    errors = []
    if language.lower() in ("html", "css"):
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("<script") and "src=" not in line:
                errors.append({
                    "line": i,
                    "type": "Security",
                    "severity": "Low",
                    "description": "Inline script detected.",
                    "suggestion": "Prefer external scripts to improve maintainability.",
                })
    return errors


def _calculate_quality_score(errors: list, lines: list, code: str) -> int:
    score = 100
    for error in errors:
        if error["severity"] == "Critical":
            score -= 18
        elif error["severity"] == "High":
            score -= 10
        elif error["severity"] == "Medium":
            score -= 5
        else:
            score -= 2

    if len(lines) > 200:
        score -= 8
    if code.count("\n\n\n") > 2:
        score -= 4

    return max(0, min(100, score))


def _auto_fix_basic_issues(code: str) -> str:
    lines = [line.rstrip().replace("\t", "    ") for line in code.split("\n")]
    cleaned = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count > 2:
                continue
        else:
            blank_count = 0
        cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"
