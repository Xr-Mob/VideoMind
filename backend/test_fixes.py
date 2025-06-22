#!/usr/bin/env python3
"""
Test script to verify timestamp validation fixes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_time_validation():
    """Test the time validation functions"""
    print("Testing timestamp validation fixes...")
    
    # Import the functions
    try:
        from main import time_to_seconds, validate_timestamps, Timestamp
        print("✓ Successfully imported validation functions")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return
    
    # Test valid timestamps
    valid_cases = [
        ("0:00", 0),
        ("1:30", 90),
        ("5:45", 345),
        ("1:00:00", 3600),
    ]
    
    print("\nTesting valid time formats:")
    for time_str, expected in valid_cases:
        result = time_to_seconds(time_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {time_str} -> {result}s (expected: {expected}s)")
    
    # Test invalid timestamps
    invalid_cases = [
        "1:60",  # Invalid seconds
        "60:00",  # Invalid minutes
        "1:30:60",  # Invalid seconds in HH:MM:SS
        "abc",  # Invalid format
    ]
    
    print("\nTesting invalid time formats:")
    for time_str in invalid_cases:
        result = time_to_seconds(time_str)
        print(f"  {time_str} -> {result}s (should be 0 for invalid)")
    
    # Test timestamp validation
    test_timestamps = [
        Timestamp(time="0:00", description="Start", seconds=0),
        Timestamp(time="1:30", description="Valid", seconds=90),
        Timestamp(time="1:60", description="Invalid", seconds=120),  # Invalid format
        Timestamp(time="1:30", description="Negative", seconds=-90),  # Negative seconds
        Timestamp(time="3:00:00", description="Too long", seconds=10800),  # Beyond 2 hours
    ]
    
    print("\nTesting timestamp validation:")
    try:
        valid_timestamps = validate_timestamps(test_timestamps)
        print(f"  Input: {len(test_timestamps)} timestamps")
        print(f"  Valid: {len(valid_timestamps)} timestamps")
        
        for ts in valid_timestamps:
            print(f"    ✓ {ts.time} ({ts.seconds}s): {ts.description}")
            
    except Exception as e:
        print(f"  ✗ Validation error: {e}")
    
    print("\n✓ Timestamp validation test completed!")

if __name__ == "__main__":
    test_time_validation() 