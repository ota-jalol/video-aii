"""File and path utilities for the video dubbing system."""

import os
import shutil
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid


def ensure_dir(path: str) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def generate_job_id() -> str:
    """
    Generate a unique job ID.
    
    Returns:
        UUID string
    """
    return str(uuid.uuid4())


def create_temp_dir(base_dir: str, job_id: str) -> Path:
    """
    Create temporary directory for a job.
    
    Args:
        base_dir: Base temporary directory
        job_id: Job identifier
        
    Returns:
        Path to created directory
    """
    temp_path = Path(base_dir) / job_id
    temp_path.mkdir(parents=True, exist_ok=True)
    return temp_path


def cleanup_temp_dir(temp_dir: str, keep_artifacts: bool = False) -> None:
    """
    Clean up temporary directory.
    
    Args:
        temp_dir: Path to temporary directory
        keep_artifacts: If True, keep JSON artifacts
    """
    temp_path = Path(temp_dir)
    
    if not temp_path.exists():
        return
    
    if keep_artifacts:
        # Remove everything except .json files
        for item in temp_path.iterdir():
            if item.is_file() and item.suffix != '.json':
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    else:
        # Remove entire directory
        shutil.rmtree(temp_path)


def save_json(data: Dict[str, Any], filepath: str) -> None:
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        filepath: Path to JSON file
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load data from JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Loaded data
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_file_size_mb(filepath: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        filepath: Path to file
        
    Returns:
        File size in MB
    """
    return os.path.getsize(filepath) / (1024 * 1024)


def list_files(directory: str, extension: Optional[str] = None) -> List[str]:
    """
    List files in directory.
    
    Args:
        directory: Directory path
        extension: Filter by extension (e.g., '.mp4')
        
    Returns:
        List of file paths
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return []
    
    if extension:
        if not extension.startswith('.'):
            extension = f'.{extension}'
        files = [str(f) for f in dir_path.glob(f'*{extension}')]
    else:
        files = [str(f) for f in dir_path.iterdir() if f.is_file()]
    
    return sorted(files)


def get_output_path(
    base_dir: str,
    filename: str,
    suffix: str = "",
    extension: str = None
) -> str:
    """
    Generate output file path.
    
    Args:
        base_dir: Base output directory
        filename: Original filename
        suffix: Suffix to add (e.g., '_dubbed')
        extension: New extension (if changing)
        
    Returns:
        Output file path
    """
    ensure_dir(base_dir)
    
    path = Path(filename)
    stem = path.stem
    ext = extension if extension else path.suffix
    
    if not ext.startswith('.'):
        ext = f'.{ext}'
    
    output_filename = f"{stem}{suffix}{ext}"
    return str(Path(base_dir) / output_filename)
