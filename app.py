import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
from pymongo import MongoClient
import requests
from config import api_access_token, mongodb_connection_string
from datetime import datetime
import json

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


@app.get("/calculate-route")
async def root(start_date: str, country: str):
    client = MongoClient(mongodb_connection_string)

    date_format = "%d.%m.%Y"
    date_object = datetime.strptime(start_date, date_format)

# Convert the datetime object to a Unix timestamp in milliseconds
    unix_timestamp = int(date_object.timestamp()) * 1000
    print(unix_timestamp)
    hack_db = client["hack"]
    "1675209600000"

    trips_collection = hack_db.trips

    cursor = trips_collection.find({"date": int(1675209600000), "country": country}).limit(
        500
    )

    result = list(cursor)
    if len(result) == 0:
        raise HTTPException(status_code=400, detail="No deliveries found")

    locations = []
    shipments = []
    id_value = 0
    for x in result:
        ''' print(x["plant_name"]) '''
        if x["plant_name"] is not None:
            ''' print(x["plant_name"]) '''
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
        id_value += 1

    vehicles = []
    value_id = 0
    for i in range(100):
        vehicles.append(
            {
                "name": str(value_id),
                "capacities": {"boxes": 100},
                "earliest_start": "2023-09-15T08:00:00Z",
                "latest_end": "2023-09-17T12:00:00Z",
            }
        )
        value_id +=1
    print(len(vehicles))
    json_data = {
        "version": 1,
        "locations": locations,
        "vehicles": vehicles,
        "shipments": shipments,
    }

    ''' # Serializing json
    json_object = json.dumps(json_data, indent=4)

    # Writing to sample.json
    with open("sample.json", "w") as outfile:
        outfile.write(json_object) '''

    json_test = {
        "version": 1,
        "locations": [
            {
                "name": "Hat Club",
                "coordinates": [-73.99566831245832, 40.72724507379965],
            },
            {
                "name": "109th Street",
                "coordinates": [-73.83597003588466, 40.68956385162866],
            },
        ],
        "vehicles": [
            {
                "name": "0",
                "capacities": {"boxes": 100},
                "earliest_start": "2023-09-15T08:00:00Z",
                "latest_end": "2023-09-15T12:00:00Z",
            }
        ],
        "shipments": [
            {
                "name": "0",
                "from": "Hat Club",
                "to": "109th Street",
                "size": {"boxes": 10},
                "pickup_duration": 10,
                "dropoff_duration": 10,
            },
            {
                "name": "1",
                "from": "Hat Club",
                "to": "109th Street",
                "size": {"boxes": 10},
                "pickup_duration": 10,
                "dropoff_duration": 10,
            },
        ],
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
    print(json_data)
    print(response.json())
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

    return api_route_response
