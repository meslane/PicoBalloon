import requests
import json
import utils

def query_telem(call, minute, tx_freq, d_start, freq_tolerance=20, band=14, num=10):
    '''
    Query telem callsigns matching the specified pattern
    
    Call: 2 d
    '''
    
    call_regex = f"'^{call[0]}.{call[1]}.*'"
    time_regex = rf"':(?:\d){minute}:'"

    query = f"SELECT * FROM wspr.rx WHERE time > '{d_start}' AND band == {band} AND match(tx_sign, {call_regex}) == 1 AND match(toString(time), {time_regex}) == 1 AND ABS(frequency - {tx_freq}) < {freq_tolerance} ORDER BY id DESC LIMIT {num} FORMAT JSON;"

    r = requests.get(f"http://db1.wspr.live/?query={query}")
    
    return json.loads(r.text)
    
def query_standard_msg(call):
    pass

wspr_data = query_telem("Q2", 8, 14097140, "2026-05-10", num=50)['data']


for contact in wspr_data:
    print(contact['time'])
    tlm = utils.decode_u4b_telem(contact['tx_sign'], contact['tx_loc'], contact['power'])
    print(tlm)