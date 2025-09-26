#!/usr/bin/env python3

import json
from json_to_claude import parse_json_input, format_json_as_text

def test_parsing():
    try:
        # Test with the sample file
        data = parse_json_input('sample_input.json')
        print("✓ JSON parsing successful")
        print(f"Parsed {len(data)} top-level keys: {list(data.keys())}")

        # Test text formatting
        text = format_json_as_text(data)
        print(f"✓ Text formatting successful ({len(text)} characters)")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    test_parsing()