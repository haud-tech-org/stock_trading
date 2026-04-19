"""
This module provides utility functions for file system operations, such as
creating, deleting, and managing files and directories.
"""
import os
import glob
import logging
import sys
import json
from typing import Any, Optional
import pandas as pd


# Add the project root to the Python path to ensure consistent imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Utility to get the project root directory
def get_project_root() -> str:
    """
    Returns the absolute path to the project root directory (one level up from 'src').
    """
    # If project_root ends with '/src', return its parent
    if project_root.endswith(os.sep + "src"):
        return os.path.dirname(project_root)
    return project_root


def clear_files_in_directory(directory: str, filename_pattern: Optional[str] = None):
    """
    Deletes files within a specific directory, optionally matching a pattern.

    Args:
        directory (str): The directory to clear files from.
        filename_pattern (Optional[str]): If provided, only deletes files matching
                                           this glob pattern (e.g., "*.json").
                                           If None, deletes all files.
    """
    if not os.path.isdir(directory):
        logging.info(f"Directory does not exist, no files to clear: {directory}")
        return

    # Use the provided pattern or default to all files
    pattern = filename_pattern if filename_pattern else "*"
    glob_pattern = os.path.join(directory, pattern)
    files_to_delete = glob.glob(glob_pattern)

    if not files_to_delete:
        logging.info(f"No files matching pattern '{pattern}' found to delete in this directory.")
        return

    for f in files_to_delete:
        try:
            if os.path.isfile(f):  # Only delete files, not subdirectories
                os.remove(f)
                logging.info(f"Deleted old file: {f}")
        except OSError as e:
            logging.error(f"Error deleting file {f}: {e}")

    logging.info(f"--- Finished clearing {len(files_to_delete)} old file(s). ---")


def save_json_report(data: Any, filepath: str, logger_instance: logging.Logger):
    """
    A generic utility to save data to a JSON file. It creates the directory if it doesn't exist.

    Args:
        data (Any): The data to save (can be a list, dict, or pandas DataFrame).
        filepath (str): The full path to the file.
        logger_instance (logging.Logger): The logger to use for output.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            if isinstance(data, pd.DataFrame):
                data.to_json(f, orient='records', indent=4)
            else:
                json.dump(data, f, indent=4)
        logger_instance.info(f"Successfully saved report to {filepath}")
    except Exception as e:
        logger_instance.error(f"Failed to save report to {filepath}: {e}")
