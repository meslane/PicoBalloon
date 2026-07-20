import json
import pandas as pd
import os
from datetime import datetime, timezone

import utils
import tracker

def main():
    config_filename = "config.json"
    wspr_filename = "wspr.csv"
    telem_filename = "telem.csv"
    
    with open(config_filename, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Open normal wspr spot database
    if os.path.isfile(wspr_filename):
        wspr_df = pd.read_csv(wspr_filename)
    else:
        print("Could not locate WSPR database file, creating empty dataframe")
        wspr_df = pd.DataFrame()
        
    # Open telemetry database
    if os.path.isfile(telem_filename):
        telem_df = pd.read_csv(telem_filename)
    else:
        print("Could not locate U4B telemetry database file, creating empty dataframe")
        telem_df = pd.DataFrame()
        
    latest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Current UTC time is: {latest_date}")
        
    # Get latest nominal WSPR telemetry
    if wspr_df.empty:
        print("Cannot get latest date from an empty WSPR dataframe!")
        print("Please enter the earliest UTC date you'd like to search in YYYY-MM-DD format")
        wspr_start_date = input('>')
    else:
        wspr_start_date = wspr_df.loc[wspr_df['id'].idxmax()]['time']
        print(f"Last spot date in WSPR dateframe was {wspr_start_date}")
    
    print(f"Querying for spots from {wspr_start_date} to {latest_date}")
    wspr_query_df = tracker.query_wspr_dataframe(config['callsign'], 
                                        wspr_start_date, latest_date, num=1000)
    
    print(wspr_query_df)
    print("\nWrite new WSPR data to database? (Y/N)")
    write_wspr = input('>')
    
    if write_wspr.lower() == 'y':
        wspr_df = pd.concat([wspr_df, wspr_query_df], ignore_index=True).drop_duplicates()
        wspr_df.to_csv(wspr_filename, index=False)
        print("Wrote WSPR database")
        
    # Get latest U4B style telemetry
    if telem_df.empty:
        print("Cannot get latest date from an empty telemetry dataframe!")
    
if __name__ == "__main__":
    main()