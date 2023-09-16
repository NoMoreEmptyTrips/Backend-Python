import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
from pydantic import BaseModel, Field
from pymongo import MongoClient
import requests
from config import api_access_token, mongodb_connection_string
from datetime import datetime, timedelta
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
    number_of_buses: int = Field(
        200, description="Number of buses that should be used for the route planning"
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
    start_driving = input.start_driving.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_driving = input.end_driving.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Calculate the timedelta between the two datetime objects
    time_difference = input.end_driving - input.start_driving

    # Extract the number of hours from the timedelta
    available_hours = time_difference.total_seconds() / 3600

    # Define the duration of each driving period and each break
    driving_duration = 10
    break_duration = 8

    # Calculate the number of full cycles (driving + break) that can be completed
    full_cycles = available_hours // (driving_duration + break_duration)

    # Calculate the remaining hours after completing full cycles
    remaining_hours = available_hours % (driving_duration + break_duration)

    # Check if there are enough remaining hours for another driving period
    if remaining_hours >= driving_duration:
        full_cycles += 1

    print("Number of breaks needed:", full_cycles)

    breaks_for_drivers = []
    current_date = input.start_driving
    hours_1 = 9.5
    for i in range(int(full_cycles)):
        hours_to_add_start = timedelta(hours=hours_1)
        hours_to_add_end = timedelta(hours=9)
        start_break = current_date + hours_to_add_start
        end_break = start_break + hours_to_add_end
        start_break_formatted = start_break.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_break_formatted = end_break.strftime("%Y-%m-%dT%H:%M:%SZ")
        current_date = end_break
        breaks_for_drivers.append(
            {
                "earliest_start": start_break_formatted, # #2023-02-17T12:30:00Z
                "latest_end": end_break_formatted, # #
                "duration": 28800
            }
        )
        hours_1 = 9

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
                            "earliest": start_driving,
                            "latest": end_driving,
                            "type": "strict",
                        }
                    ],
                    "dropoff_times": [
                        {
                            "earliest": start_driving,
                            "latest": end_driving,
                            "type": "strict",
                        }
                    ],
                }
            )
        id_value += 1

    vehicles = []
    value_id = 0
    for i in range(input.number_of_buses):
        vehicles.append(
            {
                "name": str(uuid.uuid1()),
                "capacities": {"boxes": 100},
                "earliest_start": start_driving,
                "latest_end": end_driving,

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
    try:
        code = copy["code"]
        return api_route_response
    except KeyError:
        response = routes_collection.insert_one(copy)
        api_route_response["route_id"] = str(response.inserted_id)
        return api_route_response
