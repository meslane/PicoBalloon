
def decode_u4b_telem(callsign: str, grid_square: str, power: int):
    telemetry = {}
    
    #decode callsign
    callsign_channel = callsign[0] + callsign[2] #first and third chars in callsign, for channelizing telemetry
    telemetry['channel'] = callsign_channel
    
    call_telem_int = 0
    if ord(callsign[1]) >= ord('A'):
        callsign_1_int = ord(callsign[1]) - ord('A') + 10
    else:
        callsign_1_int = ord(callsign[1]) - ord('0')
        
    call_telem_int += callsign_1_int * 17576
        
    call_telem_int += (ord(callsign[3]) - ord('A')) * 676
    call_telem_int += (ord(callsign[4]) - ord('A')) * 26
    call_telem_int += (ord(callsign[5]) - ord('A'))
    telemetry['altitude'] = (call_telem_int % 1068) * 20
    
    subsquare_1 = chr(((call_telem_int // 1068) // 24) + 97)
    subsquare_2 = chr(((call_telem_int // 1068) % 24) + 97)
    telemetry['subsquare'] = subsquare_1 + subsquare_2
    
    #decode grid square and power
    power_lut = [0,3,7,10,13,17,
                 20,23,27,30,33,37,
                 40,43,47,50,53,37,60]
                 
    power_int = power_lut.index(power)
    
    eng_telem_int = 0
    eng_telem_int += (ord(grid_square[0]) - ord('A')) * 34200
    eng_telem_int += (ord(grid_square[1]) - ord('A')) * 1900
    eng_telem_int += (ord(grid_square[2]) - ord('0')) * 190
    eng_telem_int += (ord(grid_square[3]) - ord('0')) * 19
    eng_telem_int += power_int
    
    print(eng_telem_int)
    
    #telem_int = gps_health + 2 * (gps_valid + 2 * (speed + 42 * (voltage + 40 * temperature)))
    #2, 4, 168, 6720
    telemetry['gps_health'] = eng_telem_int % 2
    telemetry['gps_valid'] = (eng_telem_int // 2) % 2
    telemetry['speed'] = ((eng_telem_int // 4) % 42) * 2
    telemetry['voltage'] = (((eng_telem_int // 168) % 40) * 0.05) + 3
    telemetry['temperature'] = (eng_telem_int // 6720) - 50
    
    return telemetry