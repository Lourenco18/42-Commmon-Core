import sys
import os
import site


def is_virtual_environment() -> bool:
    return sys.prefix != sys.base_prefix


def get_virtual_env_name() -> str:
    return os.path.basename(sys.prefix)


def main() -> None:
    try:
        in_venv = is_virtual_environment()
        python_path = sys.executable

        if not in_venv:
            print("\nMATRIX STATUS: You're still plugged in\n")

            print(f"Current Python: {python_path}")
            print("Virtual Environment: None detected\n")

            print("WARNING: You're in the global environment!")
            print("The machines can see everything you install.\n")

            print("To enter the construct, run:")
            print("python -m venv matrix_env")
            print("source matrix_env/bin/activate  # On Unix")
            print("matrix_env\\Scripts\\activate   # On Windows")

        else:
            env_name = get_virtual_env_name()

            print("\nMATRIX STATUS: Welcome to the construct\n")

            print(f"Current Python: {python_path}")
            print(f"Virtual Environment: {env_name}")
            print(f"Environment Path: {sys.prefix}\n")

            print("SUCCESS: You're in an isolated environment!")
            print("Safe to install packages without affecting")
            print("the global system.\n")

            try:
                site_packages = site.getsitepackages()[0]
            except Exception:
                site_packages = "Unknown"

            print("Package installation path:")
            print(site_packages)

    except Exception as e:
        print("Error detecting environment:", e)


if __name__ == "__main__":
    main()
