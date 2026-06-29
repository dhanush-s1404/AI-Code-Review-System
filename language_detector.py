import re


def detect_language(code: str) -> str:
    """
    Detect the programming language of a given code snippet.
    Returns a string indicating the detected language.
    """
    code = code.strip()

    # Python
    if re.search(r"^\s*def\s+\w+\s*\(|^\s*import\s+|^\s*from\s+\w+\s+import", code, re.MULTILINE):
        return "Python"

    # Java
    if re.search(r"public\s+class\s+\w+|System\.out\.println|public\s+static\s+void\s+main", code):
        return "Java"

    # C++
    if re.search(r"#include\s*<\w+>|std::\w+|cout\s*<<|int\s+main\s*\(", code):
        return "C++"

    # C
    if re.search(r"#include\s*<stdio\.h>|printf\s*\(|scanf\s*\(", code):
        return "C"

    # JavaScript / TypeScript
    if re.search(r"function\s+\w+\s*\(|console\.log|const\s+\w+\s*=|let\s+\w+\s*=|=>\s*{", code):
        return "JavaScript"

    # C#
    if re.search(r"using\s+System;|Console\.WriteLine|namespace\s+\w+", code):
        return "C#"

    # PHP
    if code.startswith("<?php") or re.search(r"\$\w+\s*=", code):
        return "PHP"

    # Ruby
    if re.search(r"^\s*puts\s+|^\s*end\s*$|^\s*require\s+", code, re.MULTILINE):
        return "Ruby"

    # Go
    if re.search(r"package\s+main|func\s+\w+\(|fmt\.Println", code):
        return "Go"

    # Rust
    if re.search(r"fn\s+main\s*\(|let\s+mut\s+|println!\(", code):
        return "Rust"

    return "Unknown"
