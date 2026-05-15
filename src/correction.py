import re

import zhconv

_CORRECTION_MAP: dict[str, str] = {}

_SUBSCRIPT_MAP = str.maketrans("aehijklmnoprstuvx", "ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
_SUPERSCRIPT_MAP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_LATEX_RE = re.compile(r"\\.|[{}]")


def _sub_repl(m: re.Match) -> str:
    content = m.group(1)
    if content.isdigit():
        return content
    return content.translate(_SUBSCRIPT_MAP)


def _sup_repl(m: re.Match) -> str:
    content = m.group(1)
    if content.isdigit():
        return content
    return content.translate(_SUPERSCRIPT_MAP)


def set_correction_map(m: dict[str, str]):
    _CORRECTION_MAP.clear()
    _CORRECTION_MAP.update(m)


def correct_text(text: str) -> str:
    text = _clean_latex(text)
    for wrong, right in _CORRECTION_MAP.items():
        if wrong in text:
            text = text.replace(wrong, right)
    return zhconv.convert(text, "zh-cn")


def _clean_latex(text: str) -> str:
    text = re.sub(r"\\text\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"_\{([^{}]+)\}", _sub_repl, text)
    text = re.sub(r"\^\{([^{}]+)\}", _sup_repl, text)
    text = re.sub(r"_([a-zA-Z])", lambda m: m.group(1).translate(_SUBSCRIPT_MAP), text)
    text = re.sub(r"\^([0-9])", lambda m: m.group(1).translate(_SUPERSCRIPT_MAP), text)
    text = text.replace(r"\times", "×")
    text = text.replace(r"\cdot", "·")
    text = text.replace(r"\quad", " ")
    text = text.replace(r"\cup", "或")
    text = text.replace(r"\geq", "≥")
    text = text.replace(r"\leq", "≤")
    text = text.replace(r"\pm", "±")
    text = re.sub(r"\s+", " ", text).strip()
    return text
