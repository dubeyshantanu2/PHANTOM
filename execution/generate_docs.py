import os
import subprocess
import sys

def generate_docs():
    """
    Generates API documentation using pdoc.
    Attempts to install pdoc if not present.
    """
    print("🚀 PHANTOM Documentation Generator")
    
    try:
        import pdoc
    except ImportError:
        print("pdoc not found. Attempting to install...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pdoc"])
    
    # Define paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "directives", "api-docs")
    modules = ["core", "data", "auth", "config", "main"]
    
    print(f"📂 Output directory: {output_dir}")
    
    # Run pdoc command
    try:
        cmd = [
            "pdoc",
            "--output-directory", output_dir,
            "--docformat", "google",
            *modules
        ]
        subprocess.check_call(cmd, cwd=project_root)
        print("✅ Documentation generated successfully!")
    except Exception as e:
        print(f"❌ Error generating documentation: {e}")

if __name__ == "__main__":
    generate_docs()
