def GS2LL(gs):
    if len(gs) > 4:
        lat = (ord(gs[1]) - 65) * 10 + (ord(gs[3]) - 48) + (ord(gs[5]) - 97) * (2.5/60) + (2.5/120) - 90
        lon = (ord(gs[0]) - 65) * 20 + (ord(gs[2]) - 48) * 2 + (ord(gs[4]) - 97) * (5/60) + (5/120) - 180
    else:
        lat = (ord(gs[1]) - 65) * 10 + (ord(gs[3]) - 48) + (2.5/120) - 90
        lon = (ord(gs[0]) - 65) * 20 + (ord(gs[2]) - 48) * 2 + (5/120) - 180
    return (lat, lon)

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
                 40,43,47,50,53,57,60]

    power_int = power_lut.index(power)

    eng_telem_int = 0
    eng_telem_int += (ord(grid_square[0]) - ord('A')) * 34200
    eng_telem_int += (ord(grid_square[1]) - ord('A')) * 1900
    eng_telem_int += (ord(grid_square[2]) - ord('0')) * 190
    eng_telem_int += (ord(grid_square[3]) - ord('0')) * 19
    eng_telem_int += power_int

    #print(eng_telem_int)

    #telem_int = gps_health + 2 * (gps_valid + 2 * (speed + 42 * (voltage + 40 * temperature)))
    #2, 4, 168, 6720
    telemetry['gps_health'] = eng_telem_int % 2
    telemetry['gps_valid'] = (eng_telem_int // 2) % 2
    telemetry['speed'] = ((eng_telem_int // 4) % 42) * 2
    telemetry['voltage'] = (((eng_telem_int // 168) % 40) * 0.05) + 3
    telemetry['temperature'] = (eng_telem_int // 6720) - 50

    return telemetry

def int_to_wspr(telem_int):
    power_lut = [0,3,7,10,13,17,
                 20,23,27,30,33,37,
                 40,43,47,50,53,57,60]

    power = power_lut[telem_int % 19]

    grid_square = []
    grid_square.insert(0, chr((telem_int // 19) % 10 + ord('0')))
    grid_square.insert(0, chr((telem_int // 190) % 10 + ord('0')))
    grid_square.insert(0, chr((telem_int // 1900) % 18 + ord('A')))
    grid_square.insert(0, chr((telem_int // 34200) % 18 + ord('A')))

    callsign = []
    callsign.insert(0, chr((telem_int // 615600) % 26 + ord('A')))
    callsign.insert(0, chr((telem_int // 16005600) % 26 + ord('A')))

    return (''.join(callsign), ''.join(grid_square), power)

def wspr_to_int(callsign, grid_square, power):
    power_lut = [0,3,7,10,13,17,
                 20,23,27,30,33,37,
                 40,43,47,50,53,57,60]

    telem_int = power_lut.index(power)

    telem_int += (ord(grid_square[3]) - ord('0')) * 19
    telem_int += (ord(grid_square[2]) - ord('0')) * 190
    telem_int += (ord(grid_square[1]) - ord('A')) * 1900
    telem_int += (ord(grid_square[0]) - ord('A')) * 34200

    telem_int += (ord(callsign[-1]) - ord('A')) * 615600
    telem_int += (ord(callsign[-2]) - ord('A')) * 16005600

    return telem_int

def encode_w6nxp_adc_telem(v_solar, v_in, l_front, l_back, temp):
    assert -64 <= temp <= 63
    assert 0 <= l_back <= 3.0
    assert 0 <= l_front <= 3.0
    assert 3.0 <= v_in <= 9.3
    assert 3.0 <= v_solar <= 9.3

    telem_int = (round((v_solar - 3) * 10) << 22) | (round((v_in - 3) * 10) << 16) | (round(l_front * 5) << 12) | (round(l_back * 5) << 8) | round((temp + 64) * 2)

    return telem_int

def decode_w6nxp_adc_telem(callsign, grid_square, power):
    telem_int = wspr_to_int(callsign, grid_square, power)

    temp = ((telem_int % 256) / 2) - 64
    l_back = ((telem_int >> 8) % 16) / 5
    l_front = ((telem_int >> 12) % 16) / 5
    v_in = (((telem_int >> 16) % 64) / 10) + 3
    v_solar = (((telem_int >> 22) % 64) / 10) + 3

    telem_dict = {
        "temp": temp,
        "l_back": l_back,
        "l_front": l_front,
        "v_in": v_in,
        "v_solar": v_solar
    }

    return telem_dict

def encode_w6nxp_alt_telem(pressure, altitude, speed):
    assert 0 <= pressure <= 1350
    assert 0 <= altitude <= 32399
    assert 0 <= speed <= 189

    power_lut = [0,3,7,10,13,17,
                 20,23,27,30,33,37,
                 40,43,47,50,53,57,60]

    power = power_lut[speed % 19]

    grid_square = []
    grid_square.insert(0, chr((speed // 19) % 10 + ord('0')))

    altitude_scaled = int(altitude / 10)
    grid_square.insert(0, chr((altitude_scaled % 10) + ord('0')))
    grid_square.insert(0, chr((altitude_scaled // 10) % 18 + ord('A')))
    grid_square.insert(0, chr((altitude_scaled // 180) % 18 + ord('A')))

    callsign = []
    pressure_scaled = int(pressure / 2)
    callsign.insert(0, chr((pressure_scaled % 26) + ord('A')))
    callsign.insert(0, chr((pressure_scaled // 26) % 26 + ord('A')))

    return (''.join(callsign), ''.join(grid_square), power)

def decode_w6nxp_alt_telem(callsign, grid_square, power):
    power_lut = [0,3,7,10,13,17,
                 20,23,27,30,33,37,
                 40,43,47,50,53,57,60]

    speed = power_lut.index(power)
    speed += (ord(grid_square[3]) - ord('0')) * 19

    altitude = (ord(grid_square[2]) - ord('0'))
    altitude += (ord(grid_square[1]) - ord('A')) * 10
    altitude += (ord(grid_square[0]) - ord('A')) * 180
    altitude *= 10

    pressure = (ord(callsign[-1]) - ord('A'))
    pressure += (ord(callsign[-2]) - ord('A')) * 26
    pressure *= 2

    alt_dict = {
        "speed": speed,
        "altitude": altitude,
        "pressure": pressure
    }

    return alt_dict

def encode_w6nxp_subsquare_telem(grid, subsquare, satellites):
    assert 0 <= satellites <= 18

    power_lut = [0,3,7,10,13,17,
                 20,23,27,30,33,37,
                 40,43,47,50,53,57,60]

    power = power_lut[satellites % 19]

    return (subsquare[0:2].upper(), grid, power)

def decode_w6nxp_subsquare_telem(callsign, grid_square, power):
    full_grid = grid_square + callsign.lower()

    power_lut = [0,3,7,10,13,17,
                 20,23,27,30,33,37,
                 40,43,47,50,53,57,60]

    satellites = power_lut.index(power)

    return (full_grid, satellites)

def main():
    test_int = encode_w6nxp_adc_telem(4.1, 9.1, 2.6, 2.4, -10.5)

    print(test_int)

    call, grid, power = int_to_wspr(test_int)
    print(call, grid, power)
    print(wspr_to_int(call, grid, power))

    print(decode_w6nxp_adc_telem(call, grid, power))

    alt_call, alt_grid, alt_power = encode_w6nxp_alt_telem(1006,50,127)
    print(alt_call, alt_grid, alt_power)
    print(decode_w6nxp_alt_telem(alt_call, alt_grid, alt_power))

    sub_call, sub_grid, sub_power = encode_w6nxp_subsquare_telem("DM03", "tu", 5)
    print(sub_call, sub_grid, sub_power)
    print(decode_w6nxp_subsquare_telem(sub_call, sub_grid, sub_power))

if __name__ == "__main__":
    main()