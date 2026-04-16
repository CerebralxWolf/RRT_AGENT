#!/usr/bin/env python3
"""
Test script for CFAO Process Monitor Agent

This script helps test individual components of the agent.
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

# Try to import agent components (may fail if dependencies not installed)
try:
    from Agent import CFAOProcessMonitor
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    print("Warning: Full agent not available (missing dependencies). Some tests will be skipped.")


def test_config():
    """Test configuration loading"""
    print("Testing configuration...")
    try:
        config = Config()
        config.validate()
        print("✓ Configuration loaded successfully")
        print(f"  SMTP Host: {config.SMTP_HOST}")
        print(f"  Check Interval: {config.CHECK_INTERVAL_MINUTES} minutes")
        print(f"  Stuck Threshold: {config.STUCK_PROCESS_THRESHOLD_MINUTES} minutes")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False
    return True


def test_time_parsing():
    """Test time parsing functionality"""
    if not AGENT_AVAILABLE:
        print("⏭️ Skipping time parsing test (agent not available)")
        return True

    print("\nTesting time parsing...")
    agent = CFAOProcessMonitor()

    test_cases = [
        ("00:15:30", 15),  # 15 minutes 30 seconds -> 15 minutes
        ("01:30:00", 90),  # 1 hour 30 minutes -> 90 minutes
        ("02:45:30", 165), # 2 hours 45 minutes 30 seconds -> 165 minutes
        ("00:05:00", 5),   # 5 minutes -> 5 minutes
        ("00:00:30", 0),   # 30 seconds -> 0 minutes
        ("", None),        # Empty string
        ("invalid", None), # Invalid format
    ]

    for time_str, expected in test_cases:
        result = agent.parse_time_to_minutes(time_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{time_str}' -> {result} minutes (expected {expected})")
        if result != expected:
            return False

    return True


def test_state_persistence():
    """Test state loading and saving"""
    if not AGENT_AVAILABLE:
        print("⏭️ Skipping state persistence test (agent not available)")
        return True

    print("\nTesting state persistence...")

    # Create test state file
    test_state = {
        'last_all_clear_timestamp': datetime.now().isoformat()
    }

    test_file = 'test_state.json'
    try:
        with open(test_file, 'w') as f:
            json.dump(test_state, f)

        # Test loading
        agent = CFAOProcessMonitor()
        agent.config.STATE_FILE = test_file
        loaded_state = agent.load_state()

        if loaded_state.get('last_all_clear_timestamp') == test_state['last_all_clear_timestamp']:
            print("✓ State persistence works")
            result = True
        else:
            print("✗ State loading failed")
            result = False

    except Exception as e:
        print(f"✗ State persistence error: {e}")
        result = False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

    return result


def test_all_clear_logic():
    """Test all-clear notification logic"""
    if not AGENT_AVAILABLE:
        print("⏭️ Skipping all-clear logic test (agent not available)")
        return True

    print("\nTesting all-clear notification logic...")
    agent = CFAOProcessMonitor()

    # Test 1: No previous timestamp
    agent.state = {}
    if agent.should_send_all_clear():
        print("✓ Sends notification when no previous timestamp")
    else:
        print("✗ Should send notification when no previous timestamp")
        return False

    # Test 2: Recent timestamp (less than 1 hour ago)
    recent_time = datetime.now() - timedelta(minutes=30)
    agent.state = {'last_all_clear_timestamp': recent_time.isoformat()}
    if not agent.should_send_all_clear():
        print("✓ Does not send notification when recent (< 1 hour)")
    else:
        print("✗ Should not send notification when recent")
        return False

    # Test 3: Old timestamp (more than 1 hour ago)
    old_time = datetime.now() - timedelta(hours=2)
    agent.state = {'last_all_clear_timestamp': old_time.isoformat()}
    if agent.should_send_all_clear():
        print("✓ Sends notification when old (> 1 hour)")
    else:
        print("✗ Should send notification when old")
        return False

    return True


def test_stuck_process_detection():
    """Test stuck process detection"""
    if not AGENT_AVAILABLE:
        print("⏭️ Skipping stuck process detection test (agent not available)")
        return True

    print("\nTesting stuck process detection...")
    agent = CFAOProcessMonitor()

    # Mock process data
    processes = [
        {'process_id': 'P001', 'time': '00:15:00', 'description': 'Normal process'},  # 15 min - OK
        {'process_id': 'P002', 'time': '00:25:00', 'description': 'Stuck process'},   # 25 min - STUCK
        {'process_id': 'P003', 'time': '01:30:00', 'description': 'Very stuck process'}, # 90 min - STUCK
        {'process_id': 'P004', 'time': 'invalid', 'description': 'Invalid time'},     # Invalid - skipped
    ]

    stuck = agent.check_for_stuck_processes(processes)

    expected_stuck_ids = ['P002', 'P003']
    actual_stuck_ids = [p['process_id'] for p in stuck]

    if set(actual_stuck_ids) == set(expected_stuck_ids):
        print("✓ Stuck process detection works correctly")
        print(f"  Found {len(stuck)} stuck processes: {actual_stuck_ids}")
        return True
    else:
        print(f"✗ Stuck process detection failed. Expected {expected_stuck_ids}, got {actual_stuck_ids}")
        return False


def run_all_tests():
    """Run all tests"""
    print("Running CFAO Process Monitor Agent Tests")
    print("=" * 50)

    tests = [
        test_config,
        test_time_parsing,
        test_state_persistence,
        test_all_clear_logic,
        test_stuck_process_detection,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed. Please review the output above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)


def test_config():
    """Test configuration loading"""
    print("Testing configuration...")
    try:
        config = Config()
        config.validate()
        print("✓ Configuration loaded successfully")
        print(f"  SMTP Host: {config.SMTP_HOST}")
        print(f"  Check Interval: {config.CHECK_INTERVAL_MINUTES} minutes")
        print(f"  Stuck Threshold: {config.STUCK_PROCESS_THRESHOLD_MINUTES} minutes")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False
    return True


def test_time_parsing():
    """Test time parsing functionality"""
    print("\nTesting time parsing...")
    agent = CFAOProcessMonitor()

    test_cases = [
        ("00:15:30", 15),  # 15 minutes 30 seconds -> 15 minutes
        ("01:30:00", 90),  # 1 hour 30 minutes -> 90 minutes
        ("02:45:30", 165), # 2 hours 45 minutes 30 seconds -> 165 minutes
        ("00:05:00", 5),   # 5 minutes -> 5 minutes
        ("00:00:30", 0),   # 30 seconds -> 0 minutes
        ("", None),        # Empty string
        ("invalid", None), # Invalid format
    ]

    for time_str, expected in test_cases:
        result = agent.parse_time_to_minutes(time_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{time_str}' -> {result} minutes (expected {expected})")
        if result != expected:
            return False

    return True


def test_state_persistence():
    """Test state loading and saving"""
    print("\nTesting state persistence...")

    # Create test state file
    test_state = {
        'last_all_clear_timestamp': datetime.now().isoformat()
    }

    test_file = 'test_state.json'
    try:
        with open(test_file, 'w') as f:
            json.dump(test_state, f)

        # Test loading
        agent = CFAOProcessMonitor()
        agent.config.STATE_FILE = test_file
        loaded_state = agent.load_state()

        if loaded_state.get('last_all_clear_timestamp') == test_state['last_all_clear_timestamp']:
            print("✓ State persistence works")
            result = True
        else:
            print("✗ State loading failed")
            result = False

    except Exception as e:
        print(f"✗ State persistence error: {e}")
        result = False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

    return result


def test_all_clear_logic():
    """Test all-clear notification logic"""
    print("\nTesting all-clear notification logic...")
    agent = CFAOProcessMonitor()

    # Test 1: No previous timestamp
    agent.state = {}
    if agent.should_send_all_clear():
        print("✓ Sends notification when no previous timestamp")
    else:
        print("✗ Should send notification when no previous timestamp")
        return False

    # Test 2: Recent timestamp (less than 1 hour ago)
    recent_time = datetime.now() - timedelta(minutes=30)
    agent.state = {'last_all_clear_timestamp': recent_time.isoformat()}
    if not agent.should_send_all_clear():
        print("✓ Does not send notification when recent (< 1 hour)")
    else:
        print("✗ Should not send notification when recent")
        return False

    # Test 3: Old timestamp (more than 1 hour ago)
    old_time = datetime.now() - timedelta(hours=2)
    agent.state = {'last_all_clear_timestamp': old_time.isoformat()}
    if agent.should_send_all_clear():
        print("✓ Sends notification when old (> 1 hour)")
    else:
        print("✗ Should send notification when old")
        return False

    return True


def test_stuck_process_detection():
    """Test stuck process detection"""
    print("\nTesting stuck process detection...")
    agent = CFAOProcessMonitor()

    # Mock process data
    processes = [
        {'process_id': 'P001', 'time': '00:15:00', 'description': 'Normal process'},  # 15 min - OK
        {'process_id': 'P002', 'time': '00:25:00', 'description': 'Stuck process'},   # 25 min - STUCK
        {'process_id': 'P003', 'time': '01:30:00', 'description': 'Very stuck process'}, # 90 min - STUCK
        {'process_id': 'P004', 'time': 'invalid', 'description': 'Invalid time'},     # Invalid - skipped
    ]

    stuck = agent.check_for_stuck_processes(processes)

    expected_stuck_ids = ['P002', 'P003']
    actual_stuck_ids = [p['process_id'] for p in stuck]

    if set(actual_stuck_ids) == set(expected_stuck_ids):
        print("✓ Stuck process detection works correctly")
        print(f"  Found {len(stuck)} stuck processes: {actual_stuck_ids}")
        return True
    else:
        print(f"✗ Stuck process detection failed. Expected {expected_stuck_ids}, got {actual_stuck_ids}")
        return False


def run_all_tests():
    """Run all tests"""
    print("Running CFAO Process Monitor Agent Tests")
    print("=" * 50)

    tests = [
        test_config,
        test_time_parsing,
        test_state_persistence,
        test_all_clear_logic,
        test_stuck_process_detection,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed. Please review the output above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)