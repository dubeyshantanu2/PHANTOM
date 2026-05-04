import os
import inspect
import importlib
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def generate_markdown(module_name, output_dir):
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        print(f"Error importing {module_name}: {e}")
        return

    doc = f"# Module {module_name}\n\n"
    if module.__doc__:
        doc += f"{module.__doc__.strip()}\n\n"

    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue

        if inspect.isclass(obj) and obj.__module__ == module_name:
            doc += f"## Class `{name}`\n"
            if obj.__doc__:
                doc += f"{obj.__doc__.strip()}\n\n"
            
            for m_name, m_obj in inspect.getmembers(obj):
                if m_name.startswith("_") and m_name != "__init__":
                    continue
                if inspect.isroutine(m_obj):
                    doc += f"### Method `{m_name}`\n"
                    if m_obj.__doc__:
                        doc += f"{m_obj.__doc__.strip()}\n\n"

        elif inspect.isfunction(obj) and obj.__module__ == module_name:
            doc += f"## Function `{name}`\n"
            if obj.__doc__:
                doc += f"{obj.__doc__.strip()}\n\n"

    output_file = os.path.join(output_dir, f"{module_name.replace('.', '_')}.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Generated docs for {module_name} -> {output_file}")

def main():
    print("Starting API doc generation...")
    output_dir = "directives/api-docs"
    os.makedirs(output_dir, exist_ok=True)

    packages = ["core", "data", "backtest"]
    for pkg in packages:
        print(f"Scanning package: {pkg}")
        pkg_path = Path(pkg)
        if not pkg_path.exists():
            print(f"Package {pkg} not found.")
            continue
        
        for file in pkg_path.glob("*.py"):
            if file.name == "__init__.py":
                continue
            module_name = f"{pkg}.{file.stem}"
            print(f"  Generating docs for: {module_name}")
            generate_markdown(module_name, output_dir)
    print("Done.")

if __name__ == "__main__":
    main()
