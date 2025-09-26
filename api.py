#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
from json_to_claude import extract_maritime_data, format_maritime_prompt, call_claude_api, create_response_json, parse_location_narratives
import requests

app = FastAPI(
    title="Maritime Narrative API",
    description="Generate compelling maritime narratives from location, weather, and wave data",
    version="1.0.0"
)

class JSONInput(BaseModel):
    data: Dict[str, Any]
    prompt_prefix: Optional[str] = "For each location, write exactly 3 compelling sentences in present tense and active voice as if we are currently at that specific location, focusing on its unique characteristics and features while enjoying the maritime conditions and surroundings: "
    model: Optional[str] = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    max_tokens: Optional[int] = 4096
    aws_region: Optional[str] = "us-west-2"

class URLInput(BaseModel):
    url: str
    prompt_prefix: Optional[str] = "For each location, write exactly 3 compelling sentences in present tense and active voice as if we are currently at that specific location, focusing on its unique characteristics and features while enjoying the maritime conditions and surroundings: "
    model: Optional[str] = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    max_tokens: Optional[int] = 4096
    aws_region: Optional[str] = "us-west-2"

@app.get("/")
async def root():
    """API status and information."""
    return {
        "message": "Maritime Narrative API",
        "status": "active",
        "endpoints": {
            "/generate": "POST - Generate narrative from JSON data",
            "/generate-from-url": "POST - Generate narrative from URL endpoint",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "maritime-narrative-api"}

@app.post("/generate")
async def generate_narrative(input_data: JSONInput):
    """Generate maritime narrative from JSON data."""
    try:
        # Extract maritime data into locations
        maritime_data = extract_maritime_data(input_data.data)
        full_prompt = format_maritime_prompt(maritime_data, input_data.prompt_prefix)

        # Call Claude API
        claude_response = call_claude_api(
            prompt=full_prompt,
            model=input_data.model,
            max_tokens=input_data.max_tokens,
            aws_region=input_data.aws_region
        )

        # Parse response into location-specific narratives
        locations = maritime_data.get("locations", [])
        narratives = parse_location_narratives(claude_response, locations)

        # Create JSON response
        result = create_response_json(narratives, input_data.model, input_data.data, maritime_data)
        return result

    except Exception as e:
        # Create error response
        error_result = create_response_json(
            narratives=[],
            model=input_data.model,
            input_data={},
            status="error",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=error_result)

@app.post("/generate-from-url")
async def generate_narrative_from_url(input_data: URLInput):
    """Generate maritime narrative from URL endpoint."""
    try:
        # Fetch JSON from URL
        response = requests.get(input_data.url, timeout=30)
        response.raise_for_status()
        json_data = response.json()

        # Extract maritime data into locations
        maritime_data = extract_maritime_data(json_data)
        full_prompt = format_maritime_prompt(maritime_data, input_data.prompt_prefix)

        # Call Claude API
        claude_response = call_claude_api(
            prompt=full_prompt,
            model=input_data.model,
            max_tokens=input_data.max_tokens,
            aws_region=input_data.aws_region
        )

        # Parse response into location-specific narratives
        locations = maritime_data.get("locations", [])
        narratives = parse_location_narratives(claude_response, locations)

        # Create JSON response
        result = create_response_json(narratives, input_data.model, json_data)
        return result

    except requests.exceptions.RequestException as e:
        error_result = create_response_json(
            narratives=[],
            model=input_data.model,
            input_data={},
            status="error",
            error=f"Failed to fetch from URL {input_data.url}: {e}"
        )
        raise HTTPException(status_code=400, detail=error_result)
    except Exception as e:
        error_result = create_response_json(
            narratives=[],
            model=input_data.model,
            input_data={},
            status="error",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=error_result)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)