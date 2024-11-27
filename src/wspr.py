import machine
import sys
import time
import random

import i2c_device
import uart_device

def parity(val: int, bit_len: int = 32):
    '''
    Calculate the parity of a given integer
    return 1 if the number of bits is odd
    return 0 if the number of bits is even
    '''
    bit_sum = 0
    for i in range(bit_len):
        bit_sum += (val >> i) & 0x01
        
    return bit_sum % 2

def bit_reverse(val: int, bit_len: int = 8):
    '''
    Reverse the bits in a given int
    '''
    val_rev = 0
    
    for i in range(bit_len):
        val_rev |= ((val >> i) & 0x01) << (bit_len - 1 - i)

    return val_rev

def wspr_int(char):
    '''
    Convert a char to an int the way WSPR wants it
    '''
    
    c = ord(char)
    
    if 48 <= c <= 57:
        return c - 48
    elif c == 32:
        return 36
    else:
        return c - 65 + 10

def generate_wspr_message(callsign: str, grid: str, power: int):
    #28 bits callsign
    #15 bits locator
    #7 bits power level
    
    valid_powers = (0, 3, 7)
    
    assert power % 10 in valid_powers
    assert 0 <= power <= 60

    #third character must be a digit, prepend spaces if not
    while not callsign[2].isdigit():
        callsign = " " + callsign
      
    #callsigns must be 6 chars, pad if not
    while len(callsign) != 6:
        callsign += " "
        
    #squash callsign into 28 bit integer
    call_int = 0
    for i, c in enumerate(callsign):
        if i == 0:
            call_int = wspr_int(c)
        elif i == 1:
            call_int = call_int * 36 + wspr_int(c)
        elif i == 2:
            call_int = call_int * 10 + wspr_int(c)
        else:
            call_int = 27 * call_int + wspr_int(c) - 10
    
    #squash grid square into 15 bit integer
    grid_int = int((179 - 10 * (ord(grid[0]) - 65) - int(grid[2])) * 180 + 10 * (ord(grid[1]) - 65) + int(grid[3]))
    
    #encode power and add it to grid square int
    pwr_int = grid_int * 128 + power + 64
    
    #combine into 50 bit int
    comb_int = ((call_int << 22) | (pwr_int & 0x3FFFFF)) << 6
    
    #pack comb_int into c_array
    c_array = [0] * 11
    for i in range(7):
        c_array[i] = (comb_int >> 8 * (6 - i)) & 0xFF
    
    #apply FEC encoding
    R_0 = 0 #shift registers
    R_1 = 0
    FEC_array = []
    
    for i in range(81):
        #shift to make room for next bit
        R_0 <<= 1
        R_1 <<= 1
        
        #shift in MSB
        int_bit = (c_array[int(i / 8)] >> (7 - (i % 8))) & 0x01
        
        #populate shift registers
        R_0 |= int_bit
        R_1 |= int_bit

        #AND with magic numbers and calculate parity
        R_0_parity = parity(R_0 & 0xF2D05351)
        R_1_parity = parity(R_1 & 0xE4613C47)

        #push to bit array
        FEC_array.append(R_0_parity)
        FEC_array.append(R_1_parity)

    #interleave bits
    d_array = [0] * 162
    i = 0
    for j in range(255):
        r = bit_reverse(j)
        
        if (r < 162):
            d_array[r] = FEC_array[i]
            i += 1
            
        if (i >= 162):
            break

    #merge with sync vector (162 bits)
    sync = [1,1,0,0,0,0,0,0,1,0,0,0,1,1,1,0,0,0,1,0,0,1,0,1,1,1,1,0,0,0,0,0,0,0,1,0,0,1,0,1,0,0,
            0,0,0,0,1,0,1,1,0,0,1,1,0,1,0,0,0,1,1,0,1,0,0,0,0,1,1,0,1,0,1,0,1,0,1,0,0,1,0,0,1,0,
            1,1,0,0,0,1,1,0,1,0,1,0,0,0,1,0,0,0,0,0,1,0,0,1,0,0,1,1,1,0,1,1,0,0,1,1,0,1,0,0,0,1,
            1,1,0,0,0,0,0,1,0,1,0,0,1,1,0,0,0,0,0,0,0,1,1,0,1,0,1,1,0,0,0,1,1,0,0,0]

    output = [0] * 162
    for i in range(162):
        output[i] = sync[i] + 2 * d_array[i]
        
    return output

def LL2GS(lat, lon):
    '''
    Given a latitude and longitude, return a six-digit maidenhead grid square
    '''
    char_list = [' '] * 6
    
    #longitude in 20 degree increments, latitude in 10 degree increments
    char_list[0] = chr(ord('A') + int((lon + 180) / 20))
    char_list[1] = chr(ord('A') + int((lat + 90) / 10))
    
    #longitude in 2 degree increments, latitude in 1 degree increments
    char_list[2] = chr(ord('0') + int((lon % 20) / 2))
    char_list[3] = chr(ord('0') + int(lat % 10))
    
    #longitude in 5' increments, latitude in 2.5' increments
    char_list[4] = chr(ord('a') + int(((lon % 2) / 2) * 24))
    char_list[5] = chr(ord('a') + int((lat % 1) * 24))
    
    return ''.join(char_list)
    
def encode_subsquare_and_altitude_telemetry(callsign_channel: str, subsquare: str, altitude: int):
    '''
    Encode balloon telemetry into the format documented at https://qrp-labs.com/flights/s4#protocol
    Also see: https://traquito.github.io/faq/channels
    
    Args:
        callsign_channel: a 2 char string designating which letter/number combination to use for channelizing telemetry over WSPR
        subsquare: a 2 char string containing the last two characters of the balloon's extended 6 character maidenhead grid square
        altitude: the balloon's altitude in meters
    '''
    assert callsign_channel[0] == 'Q' or callsign_channel[0] == '0'
    assert ord(callsign_channel[1]) - 48 < 10 #second char must be an integer
    
    callsign = [' ', ' ', ' ', ' ', ' ', ' ']
    callsign[0] = callsign_channel[0]
    callsign[2] = callsign_channel[1]
    
    c1_int = ord(subsquare[0].lower()) - 97 #must be lowercase
    c2_int = ord(subsquare[1].lower()) - 97
    
    telem_int = (((c1_int * 24) + c2_int) * 1068) + (altitude // 20)
    print(telem_int)

    callsign_1_int = (telem_int // 17576) % 36
    print(callsign_1_int)
    if callsign_1_int < 10:
        callsign[1] = chr(ord('0') + callsign_1_int)
    else:
        callsign[1] = chr(ord('A') + (callsign_1_int - 10))
    
    callsign[3] = chr(ord('A') + (telem_int // 676) % 26)
    callsign[4] = chr(ord('A') + (telem_int // 26) % 26)
    callsign[5] = chr(ord('A') + telem_int % 26)
    
    return "".join(callsign)

def encode_engineering_telemetry(temperature: int,
                                 voltage: float,
                                 speed: int,
                                 gps_valid: int,
                                 gps_health: int):
    '''
    Encode ballon telemetry into the U4B telem format
    '''
    power_lut = [0,3,7,10,13,17,
                 20,23,27,30,33,37,
                 40,43,47,50,53,37,60]
    
    #force inputs into correct ranges
    if temperature > 39:
        temperature = 39
    elif temperature < -50:
        temperature = -50
        
    if voltage < 3.00:
        voltage = 3.00
    elif voltage > 4.95:
        voltage = 4.95
    
    if speed > 82:
        speed = 82
    elif speed < 0:
        speed = 0
    
    if gps_valid != 0:
        gps_valid = 1
    if gps_health != 0:
        gps_health = 1
    
    #format into range expected
    temperature += 50
    voltage = round((voltage - 3) / 0.05)
    speed //= 2
    
    #convert to int
    telem_int = gps_health + 2 * (gps_valid + 2 * (speed + 42 * (voltage + 40 * temperature)))

    #encode int into grid square + power level
    power = power_lut[telem_int % 19]
    grid_square = [' ', ' ', ' ', ' ']
    grid_square[3] = chr(ord('0') + (telem_int // 19) % 10)
    grid_square[2] = chr(ord('0') + (telem_int // 190) % 10)
    grid_square[1] = chr(ord('A') + (telem_int // 1900) % 18)
    grid_square[0] = chr(ord('A') + (telem_int // 34200) % 18)
    
    return (''.join(grid_square), power)