#!/usr/bin/env python3

from fastapi import FastAPI
import json

test_app = FastAPI(title="Test Maritime Data API")

# Test data with multiple locations
test_maritime_data = {
    "mission_data": {
        "vessel_name": "Research Vessel Explorer",
        "mission_type": "Scientific Survey"
    },
    "locations": [
        {
            "name": "Cape Cod Bay",
            "coordinates": {"lat": 41.9, "lon": -70.1},
            "weather_conditions": {
                "wind_speed": "12 knots",
                "wind_direction": "southwest",
                "temperature": "72°F",
                "visibility": "8 nautical miles",
                "condition": "clear skies"
            },
            "wave_data": {
                "significant_wave_height": "2-3 feet",
                "wave_direction": "from the south",
                "wave_period": "6 seconds",
                "sea_condition": "calm to moderate"
            }
        },
        {
            "name": "Stellwagen Bank",
            "coordinates": {"lat": 42.1, "lon": -70.2},
            "weather_conditions": {
                "wind_speed": "18 knots",
                "wind_direction": "northeast",
                "temperature": "69°F",
                "visibility": "12 nautical miles",
                "condition": "partly cloudy"
            },
            "wave_data": {
                "significant_wave_height": "4-5 feet",
                "wave_direction": "from the east",
                "wave_period": "8 seconds",
                "sea_condition": "moderate seas"
            }
        },
        {
            "name": "Georges Bank",
            "coordinates": {"lat": 41.7, "lon": -68.5},
            "weather_conditions": {
                "wind_speed": "22 knots",
                "wind_direction": "northeast",
                "temperature": "65°F",
                "visibility": "15 nautical miles",
                "condition": "overcast"
            },
            "wave_data": {
                "significant_wave_height": "6-8 feet",
                "wave_direction": "from the northeast",
                "wave_period": "10 seconds",
                "sea_condition": "rough seas"
            }
        }
    ],
    "timestamp": "2025-09-26T15:30:00Z"
}

# Alternative format test data (legacy format)
legacy_maritime_data = {
    "voyage_info": {
        "vessel": "Coastal Explorer"
    },
    "waypoints": [
        {
            "name": "Monterey Bay",
            "location": "California Coast"
        },
        {
            "name": "Big Sur",
            "location": "California Coastline"
        }
    ],
    "current_weather": {
        "wind_speed": "8 knots",
        "wind_direction": "northwest",
        "temperature": "64°F",
        "visibility": "6 nautical miles",
        "weather_condition": "foggy"
    },
    "sea_conditions": {
        "wave_height": "3-4 feet",
        "wave_direction": "from the west",
        "wave_period": "7 seconds",
        "swell_height": "2 feet"
    }
}

@test_app.get("/")
async def root():
    return {"message": "Test Maritime Data API", "endpoints": ["/research-data", "/legacy-data", "/single-location"]}

@test_app.get("/research-data")
async def get_research_data():
    """Multiple locations with detailed conditions."""
    return test_maritime_data

@test_app.get("/legacy-data")
async def get_legacy_data():
    """Legacy format with shared conditions."""
    return legacy_maritime_data

@test_app.get("/single-location")
async def get_single_location():
    """Single location test case."""
    return {
        "location_data": {
            "name": "Martha's Vineyard",
            "weather": {
                "wind_speed": "14 knots",
                "wind_direction": "south",
                "temperature": "75°F",
                "condition": "sunny"
            },
            "waves": {
                "height": "1-2 feet",
                "direction": "from the southwest",
                "period": "5 seconds"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(test_app, host="0.0.0.0", port=9000)