#!/usr/bin/env python3
"""
Setup script for creating an isolated virtual environment for stock-analysis skill.
This creates a standalone Python environment with all required dependencies.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


def create_venv(venv_path):
    """Create virtual environment"""
    print(f"Creating virtual environment at: {venv_path}")
    venv.create(venv_path, with_pip=True)
    print("Virtual environment created successfully.")


def get_python_executable(venv_path):
    """Get the Python executable path in the virtual environment"""
    if sys.platform == "win32":
        return str(venv_path / "Scripts" / "python.exe")
    return str(venv_path / "bin" / "python")


def get_pip_executable(venv_path):
    """Get the pip executable path in the virtual environment"""
    if sys.platform == "win32":
        return str(venv_path / "Scripts" / "pip.exe")
    return str(venv_path / "bin" / "pip")


def install_requirements(venv_path, requirements_path):
    """Install required packages in the virtual environment"""
    pip_exe = get_pip_executable(venv_path)
    print(f"Installing requirements from: {requirements_path}")

    # First, upgrade pip
    subprocess.run([pip_exe, "install", "--upgrade", "pip"], check=True)

    # Install requirements
    subprocess.run([pip_exe, "install", "-r", requirements_path], check=True)
    print("Requirements installed successfully.")


def main():
    """Main setup function"""
    # Get the skill root directory
    skill_root = Path(__file__).parent.parent
    venv_path = skill_root / "venv"
    requirements_path = skill_root / "requirements.txt"

    # Check if requirements.txt exists
    if not requirements_path.exists():
        print(f"Error: requirements.txt not found at {requirements_path}")
        sys.exit(1)

    # Create virtual environment
    create_venv(venv_path)

    # Install requirements
    install_requirements(venv_path, requirements_path)

    # Print success message with next steps
    python_exe = get_python_executable(venv_path)
    print("\n" + "=" * 60)
    print("Setup completed successfully!")
    print("=" * 60)
    print(f"Virtual environment: {venv_path}")
    print(f"Python executable: {python_exe}")
    print("\nTo run the analysis script:")
    print(f"  {python_exe} scripts/analyze_stock.py 000001")
    print("=" * 60)


if __name__ == "__main__":
    main()
