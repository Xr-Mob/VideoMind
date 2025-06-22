#!/usr/bin/env python3
"""
Test script to validate timestamp functions and identify out-of-range issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import time_to_seconds, validate_timestamps, Timestamp

def test_time_conversion():
    """Test time string to seconds conversion"""
    test_cases = [
        ("0:00", 0),
        ("1:30", 90),
        ("5:45", 345),
        ("10:00", 600),
        ("1:00:00", 3600),
        ("1:30:45", 5445),
        ("2:00:00", 7200),
    ]
    
    print("Testing time conversion:")
    for time_str, expected in test_cases:
        result = time_to_seconds(time_str)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {time_str} -> {result}s (expected: {expected}s)")
    
    # Test invalid cases
    invalid_cases = [
        "1:60",  # Invalid seconds
        "60:00",  # Invalid minutes
        "1:30:60",  # Invalid seconds in HH:MM:SS
        "abc",  # Invalid format
        "1:30:45:00",  # Too many parts
    ]
    
    print("\nTesting invalid time formats:")
    for time_str in invalid_cases:
        result = time_to_seconds(time_str)
        print(f"  {time_str} -> {result}s")

def test_timestamp_validation():
    """Test timestamp validation"""
    test_timestamps = [
        Timestamp(time="0:00", description="Start", seconds=0),
        Timestamp(time="1:30", description="Valid", seconds=90),
        Timestamp(time="5:45", description="Valid", seconds=345),
        Timestamp(time="1:00:00", description="Valid", seconds=3600),
        Timestamp(time="2:00:00", description="Valid", seconds=7200),
        Timestamp(time="3:00:00", description="Too long", seconds=10800),  # Beyond 2 hours
        Timestamp(time="1:30", description="Negative", seconds=-90),  # Negative seconds
        Timestamp(time="invalid", description="Invalid format", seconds=0),  # Invalid format
    ]
    
    print("\nTesting timestamp validation:")
    valid_timestamps = validate_timestamps(test_timestamps)
    
    print(f"Input timestamps: {len(test_timestamps)}")
    print(f"Valid timestamps: {len(valid_timestamps)}")
    
    for ts in valid_timestamps:
        print(f"  ✓ {ts.time} ({ts.seconds}s): {ts.description}")

def test_gemini_response_parsing():
    """Test parsing of potential Gemini responses"""
    sample_responses = [
        # Valid JSON response
        '''[
            {"time": "00:00", "description": "Introduction", "seconds": 0},
            {"time": "01:30", "description": "Main topic", "seconds": 90},
            {"time": "05:45", "description": "Conclusion", "seconds": 345}
        ]''',
        
        # Response with seconds mismatch
        '''[
            {"time": "01:30", "description": "Main topic", "seconds": 95}
        ]''',
        
        # Response with invalid time
        '''[
            {"time": "1:60", "description": "Invalid time", "seconds": 120}
        ]''',
        
        # Response with out-of-range seconds
        '''[
            {"time": "3:00:00", "description": "Too long", "seconds": 10800}
        ]'''
    ]
    
    print("\nTesting Gemini response parsing:")
    for i, response in enumerate(sample_responses, 1):
        print(f"\nResponse {i}:")
        print(f"  Raw: {response.strip()}")
        
        # Simulate the parsing logic
        import json
        import re
        
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                timestamps_data = json.loads(json_str)
                
                timestamps = []
                for item in timestamps_data:
                    if isinstance(item, dict) and 'time' in item and 'description' in item and 'seconds' in item:
                        # Validate the seconds value matches the time format
                        expected_seconds = time_to_seconds(item['time'])
                        if expected_seconds != item['seconds']:
                            print(f"    Warning: Seconds mismatch for {item['time']}. Expected: {expected_seconds}, Got: {item['seconds']}")
                            item['seconds'] = expected_seconds
                        
                        timestamps.append(Timestamp(
                            time=item['time'],
                            description=item['description'],
                            seconds=item['seconds']
                        ))
                
                valid_timestamps = validate_timestamps(timestamps)
                print(f"    Valid timestamps: {len(valid_timestamps)}/{len(timestamps)}")
                
        except Exception as e:
            print(f"    Error parsing: {e}")

if __name__ == "__main__":
    print("Timestamp Validation Test Suite")
    print("=" * 40)
    
    test_time_conversion()
    test_timestamp_validation()
    test_gemini_response_parsing()
    
    print("\n" + "=" * 40)
    print("Test completed!") 