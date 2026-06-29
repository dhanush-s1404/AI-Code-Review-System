import re
from config import Config


def autofix_code(code: str, language: str, specific_issue: str = "") -> str:
    """
    Use AI to fix specific issues in the code.
    Returns the corrected code string.
    """
    provider = Config.AI_PROVIDER

    if provider == "anthropic":
        return _fix_with_anthropic(code, language, specific_issue)
    elif provider == "openai":
        return _fix_with_openai(code, language, specific_issue)
    else:
        return code


def _fix_with_anthropic(code: str, language: str, specific_issue: str) -> str:
    try:
        import anthropic

        api_key = Config.ANTHROPIC_API_KEY
        if not api_key:
            return code

        client = anthropic.Anthropic(api_key=api_key)
        issue_text = f"Focus specifically on: {specific_issue}" if specific_issue else "Fix all detected issues."

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    f"Fix this {language} code. {issue_text} "
                    "Return ONLY the corrected code, no explanations:\n\n"
                    f"```{language}\n{code}\n```"
                ),
            }],
        )

        fixed = message.content[0].text.strip()
        fixed = re.sub(r"^```\w*\s*", "", fixed)
        fixed = re.sub(r"\s*```$", "", fixed)
        return fixed

    except Exception as e:
        print(f"Autofix error (Anthropic): {e}")
        return code


def _fix_with_openai(code: str, language: str, specific_issue: str) -> str:
    try:
        from openai import OpenAI

        api_key = Config.OPENAI_API_KEY
        if not api_key:
            return code

        client = OpenAI(api_key=api_key)
        issue_text = f"Focus specifically on: {specific_issue}" if specific_issue else "Fix all detected issues."

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{
                "role": "user",
                "content": (
                    f"Fix this {language} code. {issue_text} "
                    "Return ONLY the corrected code, no explanations:\n\n"
                    f"```{language}\n{code}\n```"
                ),
            }],
            max_tokens=4096,
        )

        fixed = response.choices[0].message.content.strip()
        fixed = re.sub(r"^```\w*\s*", "", fixed)
        fixed = re.sub(r"\s*```$", "", fixed)
        return fixed

    except Exception as e:
        print(f"Autofix error (OpenAI): {e}")
        return code
