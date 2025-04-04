#!/usr/bin/env python3
"""
Test script to verify the environment setup for the DFM analysis system
"""

import sys
import os
import subprocess
import importlib

def check_module(module_name, package_name=None):
    """Check if a Python module is available"""
    if package_name is None:
        package_name = module_name

    try:
        importlib.import_module(module_name)
        print(f"✅ {package_name} is installed")
        return True
    except ImportError:
        print(f"❌ {package_name} is NOT installed")
        return False

def check_executable(name, command):
    """Check if an executable is available"""
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print(f"✅ {name} is installed and working")
            return True
        else:
            print(f"❌ {name} is installed but returned an error")
            return False
    except FileNotFoundError:
        print(f"❌ {name} is NOT installed or not in PATH")
        return False

def main():
    """Run all environment checks"""
    print("=== Python Environment Check ===")
    print(f"Python version: {sys.version}")
    print("")

    print("=== Required Python Packages ===")
    required_modules = [
        ("numpy", "NumPy"),
        ("trimesh", "Trimesh"),
        ("pymeshlab", "PyMeshLab"),
        ("fastapi", "FastAPI"),
        ("stripe", "Stripe"),
        ("slack_sdk", "Slack SDK"),
        ("dotenv", "python-dotenv"),
        ("aiofiles", "aiofiles"),
    ]

    for module, name in required_modules:
        check_module(module, name)

    print("")
    print("=== Optional Python Packages ===")
    optional_modules = [
        ("OCC.Core", "pythonocc-core (OpenCascade)"),
        ("open3d", "Open3D"),
    ]

    for module, name in optional_modules:
        check_module(module, name)

    print("")
    print("=== External Dependencies ===")

    # Check PrusaSlicer
    prusa_commands = [
        ["prusa-slicer", "--help"],
        ["/Applications/PrusaSlicer.app/Contents/MacOS/prusa-slicer", "--help"],
        ["C:\\Program Files\\PrusaSlicer\\prusa-slicer.exe", "--help"]
    ]

    prusa_found = False
    for cmd in prusa_commands:
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                print(f"✅ PrusaSlicer is installed at: {cmd[0]}")
                prusa_found = True
                break
        except FileNotFoundError:
            continue

    if not prusa_found:
        print("❌ PrusaSlicer is NOT installed or not found in common locations")

    print("")
    print("\n=== Environment Variables ===")
    env_vars = [
        "STRIPE_PUBLIC_KEY",
        "STRIPE_SECRET_KEY",
        "SLACK_BOT_TOKEN",
        "SLACK_WEBHOOK_URL",
        "SLACK_CHANNEL_ID",
    ]

    # Check if .env file exists
    if os.path.exists(".env"):
        print("✅ .env file exists")

        # Try to load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ Successfully loaded .env file")
        except ImportError:
            print("❌ python-dotenv not installed, can't load .env file")
    else:
        print("❌ .env file not found (required for Stripe and Slack integration)")

    # Check for environment variables
    for var in env_vars:
        if os.environ.get(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is not set")

    print("\n=== Environment Check Complete ===")

if __name__ == "__main__":
    main()
