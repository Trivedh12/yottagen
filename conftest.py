"""Root pytest configuration to ensure yottagen is always discoverable."""
import os
import sys

# Ensure repository root is on sys.path for standalone pytest executions
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
