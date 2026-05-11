import requests
import json
import pandas as pd

import utils

def query_telem(call, minute, tx_freq, d_start, freq_tolerance=20, band=14, num=10):
    '''
    Query telem callsigns matching the specified pattern
    '''
    
    call_regex = f"'^{call[0]}.{call[1]}.*'"
    time_regex = rf"':(?:\d){minute}:'"

    query = f"SELECT * FROM wspr.rx WHERE time > '{d_start}' AND band == {band} AND match(tx_sign, {call_regex}) == 1 AND match(toString(time), {time_regex}) == 1 AND ABS(frequency - {tx_freq}) < {freq_tolerance} ORDER BY id DESC LIMIT {num} FORMAT JSON;"

    r = requests.get(f"http://db1.wspr.live/?query={query}")
    
    return json.loads(r.text)
    
def query_standard_msg(call, d_start, band=14, num=10):
    '''
    Query standard WSPR callsigns matching the specified pattern
    '''
    
    query = f"SELECT * FROM wspr.rx WHERE time > '{d_start}' AND band == {band} AND tx_sign == '{call}' ORDER BY id DESC LIMIT {num} FORMAT JSON;"
    
    r = requests.get(f"http://db1.wspr.live/?query={query}")
    
    return json.loads(r.text)

def GS2LL(row):
    gs = str(row['grid'] + row['subsquare'])
    
    lat = (ord(gs[1]) - 65) * 10 + (ord(gs[3]) - 48) + (ord(gs[5]) - 97) * (2.5/60) + (2.5/120) - 90
    lon = (ord(gs[0]) - 65) * 20 + (ord(gs[2]) - 48) * 2 + (ord(gs[4]) - 97) * (5/60) + (5/120) - 180
    
    return (lat, lon)

def get_full_telem(call, tlm_call, minute, tx_freq, d_start, freq_tolerance=20, band=14, num=10):
    '''
    Return a dataframe containing full telemetry.
    This combines special telem messages with generic WSPR callsigns to
    get full precision location data
    '''
    telem_df = pd.DataFrame()
    wspr_tlm_data = query_telem(tlm_call, minute, tx_freq, d_start, num=num)['data']

    for contact in wspr_tlm_data:
        tlm = utils.decode_u4b_telem(contact['tx_sign'], contact['tx_loc'], contact['power'])
        tlm['time'] = contact['time']
        tlm['frequency'] = contact['frequency']
        tlm['id'] = contact['id']
        
        telem_df = pd.concat([telem_df, pd.DataFrame([tlm])], ignore_index=True)

    telem_df.drop_duplicates(subset='time', keep='first', inplace=True)

    wspr_df = pd.DataFrame()
    wspr_data = query_standard_msg(call, d_start, num=num)['data']

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

    telem_df['coords'] = telem_df.apply(GS2LL, axis=1)

    return telem_df

print(get_full_telem("W6NXP", "Q2", 8, 14097140, "2025-05-10", num=30))