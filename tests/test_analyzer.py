from pathlib import Path

from video_aii.analyzer import analyze_directory


def test_analyze_directory_counts_files(tmp_path: Path) -> None:
    (tmp_path / "a.mp4").write_bytes(b"0" * 10)
    (tmp_path / "b.mov").write_bytes(b"0" * 20)
    (tmp_path / "note.txt").write_text("not a video")

    result = analyze_directory(tmp_path)

    assert result.video_count == 2
    assert result.total_size_bytes == 30
    assert result.extensions == {".mov": 1, ".mp4": 1}
    assert result.largest_files[0].path == "b.mov"


def test_extension_filtering(tmp_path: Path) -> None:
    (tmp_path / "a.mp4").write_bytes(b"0" * 10)
    (tmp_path / "b.mkv").write_bytes(b"0" * 20)

    result = analyze_directory(tmp_path, extensions={".mp4"})

    assert result.video_count == 1
    assert result.extensions == {".mp4": 1}
