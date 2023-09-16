import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
from pydantic import BaseModel, Field
from pymongo import MongoClient
import requests
from config import api_access_token, mongodb_connection_string
from datetime import datetime
import json
import uuid


class InputRouteModel(BaseModel):
    delivery_date: str = Field(
        ...,
        description="The date of deliveries that should be fetched from the database",
    )
    country: str = Field(
        "MEX", description="The wanted country of deliveries (Either 'MEX' or 'ARG')"
    )
    prioritization: str = Field(
        "min-total-travel-duration",
        description="The wanted priorizization (Either 'min-total-travel-duration' or 'min-schedule-completion-time')",
    )
    start_driving: datetime = Field(...)
    end_driving: datetime = Field(...)


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

client = MongoClient(mongodb_connection_string)
hack_db = client["hack"]
trips_collection = hack_db.trips
routes_collection = hack_db.routes

@app.get("/dashboard")
async def dashboard():
    cursor = routes_collection.find({}).limit(500)

    result = list(cursor)
    if len(result) == 0:
        raise HTTPException(status_code=400, detail="No routes found")
    
    # Calculate the total distance of each route
    avg_stops = {}
    avg_empty_km = {}
    avg_wait_time = {}
    for item in result:
        # Check if routes property exists
        if "routes" not in item:
            continue

        stops_count = []
        empty_km = []
        wait_time = []
        for route in item["routes"]:
            stops_count.append(len(route["stops"]))
            prevStop = None
            for stop in route["stops"]:
                wait_time.append(stop["wait"])
                if stop["type"] == "dropoff":
                    empty_km.append((stop["odometer"] - prevStop["odometer"]) / 1000)
                    continue
                prevStop = stop
        if len(stops_count) != 0:
            avg_stops[str(item["_id"])] = (sum(stops_count) / len(stops_count))
        if len(empty_km) != 0:
            avg_empty_km[str(item["_id"])] = (sum(empty_km) / len(empty_km))
        if len(wait_time) != 0:
            avg_wait_time[str(item["_id"])] = (sum(wait_time) / len(wait_time))

    return {
        "avg_stops": avg_stops,
        "avg_empty_km": avg_empty_km,
        "avg_wait_time": avg_wait_time
    }




@app.post("/calculate-route")
async def root(input: InputRouteModel):
    print(input.start_driving.strftime('%Y-%m-%dT%H:%M:%S.%f%z'))
    date_format = "%d.%m.%Y"
    date_object = datetime.strptime(input.delivery_date, date_format)

    unix_timestamp = int(date_object.timestamp()) * 1000

    cursor = trips_collection.find(
        {"date": int(unix_timestamp) + 3600000, "country": input.country}
    ).limit(100000)

    result = list(cursor)
    if len(result) == 0:
        raise HTTPException(status_code=400, detail="No deliveries found")

    locations = []
    shipments = []
    id_value = 0
    for x in result:
        if (
            x["plant_name"] is not None
            and x["plant_code"] is not None
            and x["plant_longitude"] is not None
            and x["plant_latitude"] is not None
            and x["client_code"] is not None
            and x["client_longitude"] is not None
            and x["client_latitude"] is not None
        ):
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
                    "name": str(uuid.uuid4()),
                    "from": x["plant_code"],
                    "to": x["client_code"],
                    "size": {"boxes": 100},
                    "pickup_duration": 10,
                    "dropoff_duration": 10,
                    "pickup_times": [
                        {
                            "earliest": input.start_driving.strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                            "latest": "2023-02-03T09:15:00Z",
                            "type": "strict",
                        }
                    ],
                }
            )
        id_value += 1
        """ "pickup_times": [
                        {
                            "earliest": "2022-05-31T09:15:00Z",
                            "latest": "2022-05-31T09:30:00Z",
                            "type": "strict",
                        }
                    ],
                    "dropoff_times": [
                        {
                            "earliest": "2022-05-31T10:15:00Z",
                            "latest": "2022-05-31T10:30:00Z",
                            "type": "soft_end",
                        }
                    ], """

    vehicles = []
    value_id = 0
    for i in range(200):
        vehicles.append(
            {
                "name": str(uuid.uuid1()),
                "capacities": {"boxes": 100},
                "earliest_start": "2023-02-01T09:15:00Z",
                "latest_end": "2023-02-03T09:15:00Z",
            }
        )
        value_id += 1

    json_data = {
        "version": 1,
        "locations": locations,
        "vehicles": vehicles,
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
    copy = api_route_response.copy()
    copy["accepted"] = False
    response = routes_collection.insert_one(copy)
    api_route_response["route_id"] = str(response.inserted_id)
    return api_route_response
