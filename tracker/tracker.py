import requests
import json
import pandas as pd
import os

from geopy import distance

import utils

def query_telem(call, minute, tx_freq, d_start, d_end, freq_tolerance=20, band=14, num=10):
    '''
    Query telem callsigns matching the specified pattern
    '''
    
    call_regex = f"'^{call[0]}.{call[1]}.*'"
    time_regex = rf"':(?:\d){minute}:'"

    query = f"SELECT * FROM wspr.rx WHERE time > '{d_start}' AND time <= '{d_end}' AND band == {band} AND match(tx_sign, {call_regex}) == 1 AND match(toString(time), {time_regex}) == 1 AND ABS(frequency - {tx_freq}) < {freq_tolerance} ORDER BY id DESC LIMIT {num} FORMAT JSON;"

    r = requests.get(f"http://db1.wspr.live/?query={query}")
    
    return json.loads(r.text)
    
def query_standard_msg(call, d_start, d_end, band=14, num=10):
    '''
    Query standard WSPR callsigns matching the specified pattern
    '''
    
    query = f"SELECT * FROM wspr.rx WHERE time > '{d_start}' AND time <= '{d_end}' AND band == {band} AND tx_sign == '{call}' ORDER BY id DESC LIMIT {num} FORMAT JSON;"
    
    r = requests.get(f"http://db1.wspr.live/?query={query}")
    
    return json.loads(r.text)
    
def query_wspr_dataframe(call, d_start, d_end, band=14, num=10):
    wspr_df = pd.DataFrame()
    wspr_data = query_standard_msg(call, d_start, d_end, band=band, num=num)['data']

    for contact in wspr_data:
        wspr_df = pd.concat([wspr_df, pd.DataFrame([contact])], ignore_index=True)
        
    return wspr_df
    
def GS2LL_tx(row):
    gs = str(row['grid'] + row['subsquare'])
    return utils.GS2LL(gs)
    
def GS2LL_rx(row):
    gs = row['rx_loc']
    return utils.GS2LL(gs)
    
def get_rx_distance(row):
    return distance.geodesic(row['coords'], row['rx_coords']).km

def get_full_telem(call, tlm_call, minute, tx_freq, d_start, d_end, freq_tolerance=20, band=14, num=10):
    '''
    Return a dataframe containing full telemetry.
    This combines special telem messages with generic WSPR callsigns to
    get full precision location data
    '''
    telem_df = pd.DataFrame()
    wspr_tlm_data = query_telem(tlm_call, minute, tx_freq, d_start, d_end,
                                num=num, freq_tolerance=freq_tolerance)['data']

    for contact in wspr_tlm_data:
        tlm = utils.decode_u4b_telem(contact['tx_sign'], contact['tx_loc'], contact['power'])
        tlm['time'] = contact['time']
        tlm['frequency'] = contact['frequency']
        tlm['id'] = contact['id']
        tlm['rx_loc'] = contact['rx_loc']
        
        tlm['tx_sign'] = contact['tx_sign']
        tlm['tx_loc'] = contact['tx_loc']
        tlm['power'] = contact['power']
        
        telem_df = pd.concat([telem_df, pd.DataFrame([tlm])], ignore_index=True)

    #print(telem_df[telem_df.duplicated(subset='time', keep=False)])
    telem_df.drop_duplicates(subset='time', keep='first', inplace=True)

    wspr_df = pd.DataFrame()
    wspr_data = query_standard_msg(call, d_start, d_end, num=num)['data']

    for contact in wspr_data:
        wspr_df = pd.concat([wspr_df, pd.DataFrame([contact])], ignore_index=True)
        
    wspr_df.drop_duplicates(subset='time', keep='first', inplace=True)

    # Combine to full grid square
    nearest_grid = []
    nearest_call = []
    for index, row in telem_df.iterrows():
        nearest = wspr_df.loc[(wspr_df['id']-row['id']).abs().idxmin()]
        
        nearest_grid.append(nearest['tx_loc'])
        nearest_call.append(nearest['tx_sign'])

    telem_df['grid'] = nearest_grid
    telem_df['call'] = nearest_call

    telem_df['coords'] = telem_df.apply(GS2LL_tx, axis=1)
    telem_df['rx_coords'] = telem_df.apply(GS2LL_rx, axis=1)
    telem_df['rx_dist'] = telem_df.apply(get_rx_distance, axis=1)
    
    #print(list(telem_df.columns))

    return telem_df
    
def filter_telem_outliers(telem_df, max_distance=4e3):
    telem_df = telem_df[(telem_df['rx_dist'] < max_distance) | (telem_df['grid'] == 'JJ00')]
    
    return telem_df
    
def print_telem(telem_df):
    print(telem_df.drop(columns=["channel", "id", "rx_loc", "rx_coords", "call"]))

def main():
    '''
    telem_database = "telem.csv"
    
    # Checks specifically for a file
    if os.path.isfile(telem_database):
        print("The file exists.")
    else:
        print("The file does not exist")
        
    '''
    
    #Note that the last day specified in your query should be one day AFTER the last day you're trying to query

    #print(query_standard_msg("W6NXP", "2026-06-18", "2026-06-22")['data'])

    raw_df = get_full_telem("W6NXP", "Q2", 8, 14097140, "2026-07-18", "2026-07-21", num=1000, freq_tolerance=30)
    filtered_df = filter_telem_outliers(raw_df, max_distance=3.0e3)

    #print_telem(raw_df)
    print_telem(filtered_df)
    #print(filtered_df)
        
if __name__ == "__main__":
    main()
