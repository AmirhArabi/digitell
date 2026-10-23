import sys
import os
import subprocess

def run_graphify_analysis(project_root: str) -> int:
    """Run Graphify analysis on the given project root.

    Args:
        project_root: Path to the Django project root.
    Returns:
        Exit code: 0 on success, non-zero on failure.
    """
    try:
        import graphifyy  # type: ignore
    except ImportError:
        print("Graphify library not installed. Please install it first.", file=sys.stderr)
        return 1
    try:
        subprocess.run([sys.executable, "-m", "graphifyy", "analyze", project_root], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Graphify analysis failed: {e}", file=sys.stderr)
        return e.returncode
    return 0

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.exit(run_graphify_analysis(project_root))
