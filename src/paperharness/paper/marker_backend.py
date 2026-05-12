from __future__ import annotations

from pathlib import Path


class MarkerUnavailable(RuntimeError):
    pass


_CONVERTER = None


def is_available() -> bool:
    try:
        import marker  # noqa: F401
    except ImportError:
        return False
    return True


def pdf_to_markdown(path: Path) -> str:
    global _CONVERTER
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered
    except ImportError as exc:
        raise MarkerUnavailable("marker-pdf is not installed; pip install 'paperharness[parse]'") from exc

    if _CONVERTER is None:
        _CONVERTER = PdfConverter(artifact_dict=create_model_dict())
    rendered = _CONVERTER(str(path))
    text, _, _ = text_from_rendered(rendered)
    return text
