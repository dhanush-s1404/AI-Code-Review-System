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
            model="claude-opus-4.8",
            max_tokens=4096,
            temperature=0.2,
            messages=[{
                "role": "user",
                "content": (
                    f"Fix this {language} code. {issue_text} "
                    "Return ONLY the corrected code, no explanations:\n\n"
                    f"```{language}\n{code}\n```"
                ),
            }],
        )

        fixed = _extract_anthropic_text(message).strip()
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
