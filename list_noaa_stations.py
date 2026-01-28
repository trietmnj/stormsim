import json
import noaapy
import os

def main():
    # Configure to fetch all stations (selection_type=0)
    config = noaapy.station_list.StationListBuildConfig(
        selection_type=0,
        include_historical=True
    )
    
    print("Fetching station list from NOAA...")
    stations = noaapy.station_list.build(config)
    
    print(f"Total stations found: {len(stations)}")
    
    # Print header
    print(f"{ 'ID':<10} | {'Lat':<10} | {'Lng':<10} | {'Name'}")
    print("-" * 60)
    
    # Print first 20 stations as a sample and save all to a file
    for s in stations[:20]:
        print(f"{s['id']:<10} | {s['lat']:<10.4f} | {s['lng']:<10.4f} | {s['name']}")
    
    if len(stations) > 20:
        print(f"... and {len(stations) - 20} more.")

    # Save to intermediate data directory
    output_path = "data/intermediate/noaa-requests/all_stations_coords.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        # Extract only relevant fields for the final list
        simplified_list = [
            {"id": s["id"], "name": s["name"], "lat": s["lat"], "lng": s["lng"], "state": s.get("state")}
            for s in stations
        ]
        json.dump(simplified_list, f, indent=2)
    
    print(f"\nFull list saved to: {output_path}")

if __name__ == "__main__":
    main()
