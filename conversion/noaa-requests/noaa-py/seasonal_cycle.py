import requests
import pandas as pd

def main():
    url = "https://tidesandcurrents.noaa.gov/sltrends/data/sltrends.json"
    data = requests.get(url).json()
    rows = data["uscycletable"]["data"]["rows"]
    data = pd.DataFrame(rows)

    data.to_csv("../data/intermediate/noaa-requests/seasonal_cycle.csv", index=False)

if __name__ == "__main__":
    main()
