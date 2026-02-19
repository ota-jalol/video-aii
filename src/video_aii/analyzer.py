from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


@dataclass(slots=True)
class FileStat:
    path: str
    size_bytes: int


@dataclass(slots=True)
class AnalysisResult:
    root: str
    video_count: int
    total_size_bytes: int
    extensions: dict[str, int]
    largest_files: list[FileStat]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["largest_files"] = [asdict(item) for item in self.largest_files]
        return data


def analyze_directory(
    directory: str | Path,
    extensions: set[str] | None = None,
    top_k: int = 5,
) -> AnalysisResult:
    root = Path(directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Directory not found or invalid: {root}")

    allowed = {ext.lower() for ext in (extensions or DEFAULT_VIDEO_EXTENSIONS)}

    matches: list[Path] = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in allowed
    ]

    extensions_counter = Counter(path.suffix.lower() for path in matches)
    files = [
        FileStat(path=str(path.relative_to(root)), size_bytes=path.stat().st_size)
        for path in matches
    ]
    files_sorted = sorted(files, key=lambda item: item.size_bytes, reverse=True)

    return AnalysisResult(
        root=str(root),
        video_count=len(matches),
        total_size_bytes=sum(item.size_bytes for item in files),
        extensions=dict(sorted(extensions_counter.items())),
        largest_files=files_sorted[: max(0, top_k)],
    )
