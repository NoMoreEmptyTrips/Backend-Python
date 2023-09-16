from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
from pymongo import MongoClient
import requests
from config import api_access_token, mongodb_connection_string

app = FastAPI(
    title="API",
    description="API",
    version="{{VERSION}}",
    docs_url="/",
    redoc_url=None,
)

# Enable Cors Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/test")
async def root():
    
    client = MongoClient(
        mongodb_connection_string
    )


    hack_db = client["hack"]

    trips_collection = hack_db.trips

    cursor = trips_collection.find({})

    result = list(cursor)

    locations = []
    shipments = []
    id_value = 0
    for x in result:
        try:
            locations.index(
                {
                    "name": x["plant_code"],
                    "coordinates": [x["plant_longitude"], x["plant_latitude"]],
                }
            )
        except ValueError:
            locations.append(
                {
                    "name": x["plant_code"],
                    "coordinates": [x["plant_longitude"], x["plant_latitude"]],
                }
            )
        try:
            locations.index(
                {
                    "name": x["client_code"],
                    "coordinates": [x["client_longitude"], x["client_latitude"]],
                }
            )
        except ValueError:
            locations.append(
                {
                    "name": x["client_code"],
                    "coordinates": [x["client_longitude"], x["client_latitude"]],
                }
            )

        shipments.append(
            {
                "name": str(id_value),
                "from": x["plant_code"],
                "to": x["client_code"],
                "size": {"boxes": 100},
                "pickup_duration": 10,
                "dropoff_duration": 10,
            }
        )
        id_value +=1

    json_data = {
        "version": 1,
        "locations": locations,
        "vehicles": [
            {
                "name": "0",
                "capacities": {"boxes": 100},
                "earliest_start": "2023-09-15T08:00:00Z",
                "latest_end": "2023-09-17T12:00:00Z",
            },
            {
                "name": "1",
                "capacities": {"boxes": 100},
                "earliest_start": "2023-09-15T08:00:00Z",
                "latest_end": "2023-09-17T12:00:00Z",
            },
            {
                "name": "2",
                "capacities": {"boxes": 100},
                "earliest_start": "2023-09-15T08:00:00Z",
                "latest_end": "2023-09-17T12:00:00Z",
            },
            {
                "name": "3",
                "capacities": {"boxes": 100},
                "earliest_start": "2023-09-15T08:00:00Z",
                "latest_end": "2023-09-17T12:00:00Z",
            },
            {
                "name": "4",
                "capacities": {"boxes": 100},
                "earliest_start": "2023-09-15T08:00:00Z",
                "latest_end": "2023-09-17T12:00:00Z",
            },
            
            {
                "name": "5",
                "capacities": {"boxes": 100},
                "earliest_start": "2023-09-15T08:00:00Z",
                "latest_end": "2023-09-17T12:00:00Z",
            }
        ],
        "shipments": shipments,
    }

    response = requests.post(
        f"https://api.mapbox.com/optimized-trips/v2?access_token={api_access_token}",
        json=json_data,
        headers={
            "Accept": "/",
            "Content-Type": "application/json",
            "Origin": "https://demos.mapbox.com/",
            "Referer": "https://demos.mapbox.com/",
        },
    )
    print()
    id = response.json()["id"]
    data_ready = False
    api_route_response = {}
    while not data_ready:
        time.sleep(0.2)
        check_response = requests.get(
            f"https://api.mapbox.com/optimized-trips/v2/{id}?access_token={api_access_token}",
            headers={
                "Accept": "/",
                "Content-Type": "application/json",
                "Origin": "https://demos.mapbox.com/",
                "Referer": "https://demos.mapbox.com/",
            },
        )
        if check_response.status_code == 200:
            data_ready = True
            api_route_response = check_response.json()

    #print(api_route_response)

    #print(json_data)
    return api_route_response


