#!/usr/bin/env python3
"""
CFAO Process Monitor Agent - Validation Script

Checks if the agent is properly configured and ready for deployment.
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✓ {description} found")
        return True
    else:
        print(f"✗ {description} missing: {filepath}")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists"""
    if os.path.exists(dirpath) and os.path.isdir(dirpath):
        print(f"✓ {description} found")
        return True
    else:
        print(f"✗ {description} missing: {dirpath}")
        return False

def check_env_file():
    """Check if .env file exists"""
    env_file = '.env'
    if not os.path.exists(env_file):
        print(f"✗ .env file missing. Copy .env.example to .env and configure.")
        return False

    print("✓ .env file exists")
    return True

def check_python_imports():
    """Check if required Python packages can be imported"""
    required_packages = [
        ('dotenv', 'python-dotenv'),
        ('apscheduler', 'APScheduler'),
        ('playwright', 'Playwright'),
    ]

    all_available = True
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"✓ {description} available")
        except ImportError:
            print(f"✗ {description} not installed. Run: pip install {package}")
            all_available = False

    return all_available

def check_docker_setup():
    """Check if Docker setup is ready"""
    docker_files = ['Dockerfile', 'docker-compose.yml']
    all_present = True

    for file in docker_files:
        if not check_file_exists(file, f"Docker {file}"):
            all_present = False

    if all_present:
        print("✓ Docker setup ready")
    return all_present

def main():
    """Main validation function"""
    print("CFAO Process Monitor Agent - Validation")
    print("=" * 50)

    checks = [
        ("Project Files", lambda: all([
            check_file_exists('Agent.py', 'Main agent script'),
            check_file_exists('config.py', 'Configuration module'),
            check_file_exists('test.py', 'Test script'),
            check_file_exists('requirements.txt', 'Python dependencies'),
            check_file_exists('README.md', 'Documentation'),
            check_file_exists('setup.bat', 'Setup script'),
        ])),
        ("Environment Configuration", check_env_file),
        ("Python Dependencies", check_python_imports),
        ("Docker Setup", check_docker_setup),
        ("Directories", lambda: all([
            check_directory_exists('data', 'Data directory (created automatically)'),
            check_directory_exists('logs', 'Logs directory (created automatically)'),
        ])),
    ]

    passed = 0
    total = len(checks)

    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            if check_func():
                passed += 1
                print(f"  Status: ✓ PASSED")
            else:
                print(f"  Status: ✗ FAILED")
        except Exception as e:
            print(f"  Status: ✗ ERROR - {e}")

    print("\n" + "=" * 50)
    print(f"Validation Results: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 Agent is ready for deployment!")
        print("\nNext steps:")
        print("1. Configure your .env file with real credentials")
        print("2. Test locally: python Agent.py --once")
        print("3. Deploy: docker-compose up -d")
        return True
    else:
        print("❌ Agent is not ready. Please fix the failed checks above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)