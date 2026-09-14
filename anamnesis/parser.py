"""
Parser for EduMed HTML files.

Each EduMed module HTML embeds a `<script type="module">` block that declares
several JavaScript constants:

- ``const PATIENT = { ... };`` — single object literal with the case patient.
- ``const ALL_QS = [ ... ];`` — array literal with the seven anamnesis steps.
- ``const STEP_DX = [ ... ];`` — array literal with the diagnostic feedback per quote.
- ``const COMBOS = [ ... ];`` — array literal with the differential diagnosis combos.
- ``const QUIZ_CARDS = [ ... ];`` — array literal with the diagnostic study cards
  used for the in-page "Pruébate" flashcard exercise. Each card describes a
  candidate diagnosis (``dx``) plus a clinical vignette and assorted descriptive
  fields (``caso``/``loc``/``tipo``/``claves``/``patofisio``/...). Field names
  vary across modules; the parser returns the raw decoded list and the importer
  is responsible for synthesising multiple-choice questions from it.

These literals are JavaScript (unquoted keys, single quotes, trailing commas, JS
comments) so we can not feed them to the standard ``json`` module. We use
``demjson3.decode(..., strict=False)`` which is lenient enough to swallow them.

The regex extracts the body up to the matching closing brace/bracket followed
by ``;``. The HTML files in ``EduMed_UVa_completo/`` consistently terminate
each block with ``};`` or ``];`` on its own line, which makes the regex
straightforward.
"""

from __future__ import annotations

import re

import demjson3


_BLOCK_RE_CACHE: dict[str, re.Pattern] = {}


def _build_block_re(name: str) -> re.Pattern:
    # Match `const NAME = (literal)\n};` or `const NAME = (literal)\n];`.
    # Some EduMed files declare the same constants as `window.NAME = ...` instead
    # of `const NAME = ...`, so accept either prefix.
    # The closing `};` / `];` lives on its own line in the EduMed sources.
    return re.compile(
        rf'(?:const\s+|window\.){re.escape(name)}\s*=\s*'
        rf'(?P<body>[\[\{{][\s\S]*?)\n(?P<close>\}};|\];)',
        re.MULTILINE,
    )


def _extract_block(html: str, name: str) -> str | None:
    if name not in _BLOCK_RE_CACHE:
        _BLOCK_RE_CACHE[name] = _build_block_re(name)
    m = _BLOCK_RE_CACHE[name].search(html)
    if not m:
        return None
    body = m.group('body')
    close_char = '}' if m.group('close').startswith('}') else ']'
    return body + '\n' + close_char


def _decode(literal: str):
    return demjson3.decode(literal, strict=False)


def parse_module_html(html: str) -> dict:
    """Parse an EduMed module HTML and return its data structures.

    Returns a dict with keys ``patient``, ``steps``, ``step_dx``, ``combos``,
    ``quiz``, plus a ``warnings`` list naming any expected block that was
    absent. Missing blocks default to ``{}`` (patient) or ``[]`` (others); the
    ``warnings`` list is empty when everything parsed cleanly.
    """
    warnings: list[str] = []
    out: dict = {
        'patient': {},
        'steps': [],
        'step_dx': [],
        'combos': [],
        'quiz': [],
        'warnings': warnings,
    }

    pat = _extract_block(html, 'PATIENT')
    if pat:
        out['patient'] = _decode(pat)
    else:
        warnings.append('PATIENT block not found')

    qs = _extract_block(html, 'ALL_QS')
    if qs:
        out['steps'] = _decode(qs)
    else:
        warnings.append('ALL_QS block not found')

    dx = _extract_block(html, 'STEP_DX')
    if dx:
        out['step_dx'] = _decode(dx)
    else:
        warnings.append('STEP_DX block not found')

    # Some modules name the combos array `SYMPTOM_COMBOS` instead of `COMBOS`.
    combos = _extract_block(html, 'COMBOS') or _extract_block(html, 'SYMPTOM_COMBOS')
    if combos:
        out['combos'] = _decode(combos)
    else:
        warnings.append('COMBOS/SYMPTOM_COMBOS blocks not found')

    # The quiz block is named `QUIZ_CARDS` in every shipped module (some
    # modules use `window.QUIZ_CARDS` instead of `const QUIZ_CARDS`; the
    # extractor handles both). Field names inside each card vary across
    # modules, so the importer is in charge of normalising them.
    quiz = _extract_block(html, 'QUIZ_CARDS') or _extract_block(html, 'QUIZ')
    if quiz:
        out['quiz'] = _decode(quiz)
    else:
        warnings.append('QUIZ block not found')

    return out
