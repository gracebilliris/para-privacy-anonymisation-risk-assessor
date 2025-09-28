"""
MCP Tool: Tabular Dataset Discovery

Provides a function to discover all tabular datasets (CSV, XLS, XLSX) in the repository.
"""

import glob
import os
from typing import List

def discover_tabular_datasets(search_globs=None, repo_root: str = None) -> List[str]:
    """
    Discover all tabular datasets (CSV, XLS, XLSX files) in the repository.
    Args:
        search_globs: List of glob patterns for dataset files (default ['**/*.csv', '**/*.xls', '**/*.xlsx']).
        repo_root: Root directory to search from. If None, uses three levels up from this file.
    Returns:
        List of absolute file paths to discovered datasets.
    """
    if search_globs is None:
        search_globs = ['**/*.csv', '**/*.xls', '**/*.xlsx']
    if repo_root is None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    dataset_paths = []
    for pattern in search_globs:
        full_pattern = os.path.join(repo_root, pattern)
        dataset_paths.extend(glob.glob(full_pattern, recursive=True))
    dataset_paths = [p for p in dataset_paths if os.path.isfile(p)]
    return sorted(set(dataset_paths))
