#!/usr/bin/env python3

import json
import argparse
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import boto3
from dotenv import load_dotenv
import os
import requests
load_dotenv()


def fetch_json_from_url(url: str) -> Dict[str, Any]:
    """Fetch JSON data from a URL endpoint."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch from URL {url}: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from {url}: {e}")


def parse_json_input(input_source: str) -> Dict[str, Any]:
    """Parse JSON from file path, URL, or stdin."""
    try:
        if input_source == '-':
            # Read from stdin
            content = sys.stdin.read()
            return json.loads(content)
        elif input_source.startswith(('http://', 'https://')):
            # Fetch from URL
            return fetch_json_from_url(input_source)
        else:
            # Read from file
            with open(input_source, 'r', encoding='utf-8') as f:
                content = f.read()
            return json.loads(content)
    except FileNotFoundError:
        raise ValueError(f"File not found: {input_source}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ValueError(f"Error reading input: {e}")


def extract_maritime_data(data: Any) -> Dict[str, Any]:
    """Extract location-specific maritime data with weather and wave conditions."""
    locations = []

    # Keywords to identify relevant fields
    WAYPOINT_KEYWORDS = ['waypoint', 'buoy', 'destination', 'port', 'harbor', 'location', 'place', 'name', 'point']
    WEATHER_KEYWORDS = ['weather', 'wind', 'temperature', 'temp', 'pressure', 'humidity', 'visibility', 'condition', 'forecast']
    WAVE_KEYWORDS = ['wave', 'swell', 'height', 'period', 'direction', 'sea', 'surf', 'tide', 'current']

    def extract_location_data(obj, parent_key=""):
        """Extract data and try to group by location."""
        if isinstance(obj, dict):
            # Check if this is a location object with conditions
            location_name = None
            weather_data = []
            wave_data = []

            for key, value in obj.items():
                key_lower = key.lower()

                if isinstance(value, str) and value.strip():
                    # Check if this is a location name
                    if any(keyword in key_lower for keyword in WAYPOINT_KEYWORDS):
                        location_name = value.strip()
                    # Check if this is weather data
                    elif any(keyword in key_lower for keyword in WEATHER_KEYWORDS):
                        weather_data.append(f"{key}: {value.strip()}")
                    # Check if this is wave data
                    elif any(keyword in key_lower for keyword in WAVE_KEYWORDS):
                        wave_data.append(f"{key}: {value.strip()}")
                elif isinstance(value, dict):
                    # Check if this is a nested weather or wave object
                    if any(keyword in key_lower for keyword in WEATHER_KEYWORDS):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, str) and sub_value.strip():
                                weather_data.append(f"{sub_key}: {sub_value.strip()}")
                    elif any(keyword in key_lower for keyword in WAVE_KEYWORDS):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, str) and sub_value.strip():
                                wave_data.append(f"{sub_key}: {sub_value.strip()}")
                    else:
                        # Recursively process nested objects
                        nested_result = extract_location_data(value, f"{parent_key}.{key}" if parent_key else key)
                        if nested_result:
                            locations.extend(nested_result)
                elif isinstance(value, list):
                    # Process array items
                    for i, item in enumerate(value):
                        nested_result = extract_location_data(item, f"{parent_key}.{key}[{i}]" if parent_key else f"{key}[{i}]")
                        if nested_result:
                            locations.extend(nested_result)

            # If we found a location with conditions, add it
            if location_name and (weather_data or wave_data):
                locations.append({
                    "name": location_name,
                    "weather": weather_data,
                    "waves": wave_data
                })
                return []  # Return empty to avoid duplicate processing

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                nested_result = extract_location_data(item, f"{parent_key}[{i}]" if parent_key else f"[{i}]")
                if nested_result:
                    locations.extend(nested_result)

        return locations

    # Extract all location data
    extract_location_data(data)

    # If no structured locations found, fall back to old behavior
    if not locations:
        waypoints = []
        weather = []
        waves = []

        def fallback_extract(obj, parent_key=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value.strip():
                        full_key = f"{parent_key}.{key}" if parent_key else key
                        key_lower = full_key.lower()

                        if any(keyword in key_lower for keyword in WAYPOINT_KEYWORDS):
                            waypoints.append(value.strip())
                        elif any(keyword in key_lower for keyword in WEATHER_KEYWORDS):
                            weather.append(f"{key}: {value.strip()}")
                        elif any(keyword in key_lower for keyword in WAVE_KEYWORDS):
                            waves.append(f"{key}: {value.strip()}")
                    else:
                        fallback_extract(value, f"{parent_key}.{key}" if parent_key else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    fallback_extract(item, f"{parent_key}[{i}]" if parent_key else f"[{i}]")

        fallback_extract(data)

        # Create single location from waypoints
        for waypoint in waypoints:
            locations.append({
                "name": waypoint,
                "weather": weather,
                "waves": waves
            })

    return {"locations": locations}


def format_maritime_prompt(maritime_data: Dict[str, Any], prefix: str = "") -> str:
    """Format maritime data into a structured prompt for location-specific narratives."""
    sections = []

    if prefix:
        sections.append(prefix)

    locations = maritime_data.get("locations", [])

    for location in locations:
        location_section = f"LOCATION: {location['name']}"

        if location['weather']:
            location_section += f" WEATHER: {' '.join(location['weather'])}"

        if location['waves']:
            location_section += f" WAVES: {' '.join(location['waves'])}"

        sections.append(location_section)

    return " ".join(sections)


def parse_location_narratives(claude_response: str, locations: list) -> list:
    """Parse Claude's response into location-specific narratives."""
    narratives = []

    def clean_narrative_line(line: str, location_name: str) -> str:
        """Clean a narrative line by removing location headers and formatting."""
        # Remove bold formatting
        line = line.replace('**', '')

        # Remove location name from beginning if it starts with it
        if line.lower().startswith(location_name.lower()):
            # Remove the location name and any following punctuation/whitespace
            line = line[len(location_name):].lstrip(':').lstrip('-').lstrip().lstrip(':').lstrip()

        return line.strip()

    # Try to split the response by location names
    response_lines = claude_response.strip().split('\n')
    current_location = None
    current_narrative = []

    for line in response_lines:
        line = line.strip()
        if not line:
            continue

        # Check if this line contains a location name
        found_location = None
        for location in locations:
            if location['name'].lower() in line.lower():
                found_location = location['name']
                break

        if found_location:
            # Save previous narrative if exists
            if current_location and current_narrative:
                clean_narrative = ' '.join(current_narrative)
                narratives.append({
                    "location": current_location,
                    "narrative": clean_narrative
                })

            # Start new location - clean the line
            current_location = found_location
            cleaned_line = clean_narrative_line(line, found_location)
            if cleaned_line:  # Only add if there's content after cleaning
                current_narrative = [cleaned_line]
            else:
                current_narrative = []
        else:
            # Add to current narrative
            if current_location:
                current_narrative.append(line)

    # Add the last narrative
    if current_location and current_narrative:
        clean_narrative = ' '.join(current_narrative)
        narratives.append({
            "location": current_location,
            "narrative": clean_narrative
        })

    # If parsing failed, fall back to simple approach
    if not narratives and locations:
        # Split response roughly by number of locations
        sentences = claude_response.split('.')
        sentences_per_location = max(1, len(sentences) // len(locations))

        for i, location in enumerate(locations):
            start_idx = i * sentences_per_location
            end_idx = start_idx + sentences_per_location
            narrative_sentences = sentences[start_idx:end_idx]
            narrative = '.'.join(narrative_sentences).strip()
            if narrative:
                # Clean the narrative for fallback approach too
                narrative = narrative.replace('**', '')
                for loc in locations:
                    if narrative.lower().startswith(loc['name'].lower()):
                        narrative = narrative[len(loc['name']):].lstrip(':').lstrip('-').lstrip().lstrip(':').lstrip()
                        break

                narratives.append({
                    "location": location['name'],
                    "narrative": narrative + '.' if not narrative.endswith('.') else narrative
                })

    return narratives


def call_claude_api(
    prompt: str,
    model: str = "us.anthropic.claude-sonnet-4-20250514-v1:0",
    max_tokens: int = 4096,
    aws_region: str = "us-west-2"
) -> str:
    """Call Claude API via AWS Bedrock using boto3."""
    try:
        # Create Bedrock runtime client
        bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN")  # optional, for temporary creds
        )

        # Prepare the request body for Claude
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "anthropic_version": "bedrock-2023-05-31"
        }

        # Make the API call
        response = bedrock.invoke_model(
            modelId=model,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        # Parse the response
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']

    except Exception as e:
        raise RuntimeError(f"Claude API call failed: {e}")


def create_response_json(
    narratives: list,
    model: str,
    input_data: Dict[str, Any],
    maritime_data: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error: Optional[str] = None
) -> Dict[str, Any]:
    """Create structured JSON response with location-specific narratives."""
    # Enhance narratives with weather and wave data
    if maritime_data and narratives:
        locations = maritime_data.get("locations", [])

        for narrative in narratives:
            # Find matching location data
            for location in locations:
                if location["name"] == narrative["location"]:
                    if location.get("weather"):
                        narrative["weather"] = location["weather"]
                    if location.get("waves"):
                        narrative["waves"] = location["waves"]
                    break

    result = {
        "narratives": narratives,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "locations_count": len(narratives),
        "status": status
    }

    if error:
        result["error"] = error

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Parse JSON and send to Claude AWS API, returning JSON response"
    )
    parser.add_argument(
        'input',
        help='JSON file path, URL (http/https), or "-" for stdin'
    )
    parser.add_argument(
        '--model', '-m',
        default='us.anthropic.claude-sonnet-4-20250514-v1:0',
        help='Claude model to use (default: claude-sonnet-4)'
    )
    parser.add_argument(
        '--max-tokens', '-t',
        type=int,
        default=4096,
        help='Maximum tokens in response (default: 4096)'
    )
    parser.add_argument(
        '--region', '-r',
        default='us-west-2',
        help='AWS region (default: us-west-2)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '--prompt-prefix',
        default='For each location, write exactly 3 compelling sentences in present tense and active voice as if we are currently at that specific location, focusing on its unique characteristics and features while enjoying the maritime conditions and surroundings: ',
        help='Prefix to add before the extracted maritime data'
    )

    args = parser.parse_args()

    try:
        # Parse input JSON
        input_data = parse_json_input(args.input)

        # Extract maritime data into locations
        maritime_data = extract_maritime_data(input_data)
        full_prompt = format_maritime_prompt(maritime_data, args.prompt_prefix)

        # Call Claude API
        claude_response = call_claude_api(
            prompt=full_prompt,
            model=args.model,
            max_tokens=args.max_tokens,
            aws_region=args.region
        )

        # Parse response into location-specific narratives
        locations = maritime_data.get("locations", [])
        narratives = parse_location_narratives(claude_response, locations)

        # Create JSON response
        result = create_response_json(narratives, args.model, input_data, maritime_data)

    except Exception as e:
        # Create error response
        result = create_response_json(
            narratives=[],
            model=args.model,
            input_data={},
            status="error",
            error=str(e)
        )

    # Output result
    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
    else:
        print(output_json)


if __name__ == "__main__":
    main()