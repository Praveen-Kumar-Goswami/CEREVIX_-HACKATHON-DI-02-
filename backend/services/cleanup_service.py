"""
Cleanup Service
Automatic cleanup of temporary files with TTL (Time-To-Live) enforcement.

Safety features:
- Never deletes model weights or development data
- Handles process restarts via filesystem timestamps
- Configurable TTL (default 24 hours)
- Whitelist-based protection for critical assets
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# TTL Configuration
DEFAULT_TTL_HOURS = 24
CLEANUP_CHECK_INTERVAL_MINUTES = 60

# Protected assets (never delete)
PROTECTED_PATTERNS = {
    'models/',  # All model files
    'backend/',  # Source code
    'frontend/',  # Frontend assets
    'docs/',  # Documentation
    '.git/',  # Git repository
    'requirements.txt',
    'README.md',
    'data/synthetic_evaluation/'  # Development test data
}

# Cleanup targets (temporary data)
CLEANUP_DIRECTORIES = [
    'data/uploads',
    'data/predictions',
    'data/reports'
]


def is_protected(filepath: Path, workspace_root: Path) -> bool:
    """
    Check if file is protected from cleanup.
    
    Args:
        filepath: File to check
        workspace_root: Workspace root directory
        
    Returns:
        True if file should be protected
    """
    try:
        rel_path = filepath.relative_to(workspace_root)
        rel_path_str = str(rel_path).replace('\\', '/')
        
        for pattern in PROTECTED_PATTERNS:
            # Check if path starts with protected directory
            if pattern.endswith('/'):
                # Directory prefix
                if rel_path_str.startswith(pattern):
                    return True
            elif pattern == rel_path_str:
                # Exact file match
                return True
                
        return False
    except ValueError:
        # Path not relative to workspace
        return True  # Protect files outside workspace


def get_file_age_hours(filepath: Path) -> float:
    """
    Get file age in hours based on modification time.
    
    Args:
        filepath: File to check
        
    Returns:
        Age in hours
    """
    mtime = filepath.stat().st_mtime
    age_seconds = time.time() - mtime
    return age_seconds / 3600


def cleanup_expired_files(
    workspace_root: Path,
    ttl_hours: float = DEFAULT_TTL_HOURS,
    dry_run: bool = False
) -> tuple[int, int]:
    """
    Clean up files older than TTL in cleanup directories.
    
    Args:
        workspace_root: Workspace root path
        ttl_hours: Time-to-live in hours
        dry_run: If True, only report what would be deleted
        
    Returns:
        Tuple of (files_deleted, files_protected)
    """
    files_deleted = 0
    files_protected = 0
    
    logger.info(f"Starting cleanup (TTL={ttl_hours}h, dry_run={dry_run})")
    
    for cleanup_dir in CLEANUP_DIRECTORIES:
        dir_path = workspace_root / cleanup_dir
        
        if not dir_path.exists():
            logger.debug(f"Cleanup directory does not exist: {dir_path}")
            continue
            
        logger.info(f"Scanning {dir_path}")
        
        # Walk directory tree
        for root, dirs, files in os.walk(dir_path):
            root_path = Path(root)
            
            for filename in files:
                filepath = root_path / filename
                
                # Check protection
                if is_protected(filepath, workspace_root):
                    files_protected += 1
                    continue
                
                # Check age
                try:
                    age_hours = get_file_age_hours(filepath)
                    
                    if age_hours > ttl_hours:
                        if dry_run:
                            logger.info(f"Would delete (age={age_hours:.1f}h): {filepath}")
                        else:
                            filepath.unlink()
                            logger.info(f"Deleted (age={age_hours:.1f}h): {filepath}")
                        files_deleted += 1
                        
                except (OSError, PermissionError) as e:
                    logger.error(f"Error accessing {filepath}: {e}")
    
    # Clean up empty directories
    if not dry_run:
        for cleanup_dir in CLEANUP_DIRECTORIES:
            dir_path = workspace_root / cleanup_dir
            if dir_path.exists():
                for root, dirs, files in os.walk(dir_path, topdown=False):
                    for dirname in dirs:
                        dirpath = Path(root) / dirname
                        try:
                            if not any(dirpath.iterdir()):
                                dirpath.rmdir()
                                logger.info(f"Removed empty directory: {dirpath}")
                        except OSError:
                            pass
    
    logger.info(f"Cleanup complete: {files_deleted} deleted, {files_protected} protected")
    return files_deleted, files_protected


def run_cleanup_on_startup(workspace_root: Path, ttl_hours: float = DEFAULT_TTL_HOURS):
    """
    Run cleanup check on application startup.
    
    This handles the case where the process was restarted and old files exist.
    """
    logger.info("Running cleanup on startup")
    deleted, protected = cleanup_expired_files(workspace_root, ttl_hours, dry_run=False)
    logger.info(f"Startup cleanup: {deleted} files deleted, {protected} protected")



