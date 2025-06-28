import os
import importlib.util
import traceback
from typing import Optional
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)


def autoload_routers(base_path: str) -> APIRouter:
    """
    Recursively load all routers from the given base path.

    Args:
        base_path: The base directory path to start looking for routers

    Returns:
        APIRouter: The main router with all sub-routers mounted

    Raises:
        FileNotFoundError: If no router.py file is found in the base path
    """
    # Check if the base router exists
    base_router_path = os.path.join(base_path, "router.py")
    if not os.path.isfile(base_router_path):
        raise FileNotFoundError(f"No router.py found at {base_path}")

    # Import the base router
    main_router = _import_router_from_path(base_router_path)
    if not main_router:
        raise ValueError(
            f"router.py at {base_path} does not contain a valid router variable"
        )

    # Recursively include all sub-routers
    visited_paths = set()
    _include_sub_routers(base_path, main_router, visited_paths=visited_paths)

    return main_router


def _import_router_from_path(router_path: str) -> Optional[APIRouter]:
    """
    Import a router from a specific file path.

    Args:
        router_path: Path to the router.py file

    Returns:
        APIRouter or None: The router if found and valid, None otherwise
    """
    try:
        # Get the module name from the file path
        module_name = os.path.basename(router_path).replace(".py", "")

        # Load the module spec
        spec = importlib.util.spec_from_file_location(module_name, router_path)
        if not spec or not spec.loader:
            logger.warning(f"Could not load spec for {router_path}")
            return None
        # Import the module
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Check if it has a router variable of type APIRouter
        if hasattr(module, "router") and isinstance(module.router, APIRouter):
            return module.router
        else:
            logger.warning(f"No valid router found in {router_path}")
            return None
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error importing router from {router_path}: {str(e)}")
        return None


def _include_sub_routers(
    directory: str, parent_router: APIRouter, visited_paths: set
) -> None:
    """
    Recursively find and include all sub-routers.

    Args:
        directory: The directory to search for sub-routers
        parent_router: The parent router to include sub-routers in
        visited_paths: Set of paths already visited to avoid infinite recursion
    """
    # Add current directory to visited paths
    visited_paths.add(os.path.abspath(directory))

    # Get all subdirectories
    subdirs = [
        d
        for d in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, d)) and not d.startswith("_")
    ]

    # Check each subdirectory for router.py
    for subdir in subdirs:
        subdir_path = os.path.join(directory, subdir)
        router_file = os.path.join(subdir_path, "router.py")

        # Skip if this path was already visited
        if os.path.abspath(subdir_path) in visited_paths:
            continue

        # If router.py exists, import it and include in parent router
        if os.path.isfile(router_file):
            sub_router = _import_router_from_path(router_file)
            if sub_router:
                _include_sub_routers(subdir_path, sub_router, visited_paths)
                parent_router.include_router(sub_router)
