import machine
import time
#from typing import Callable

class UART_Device:
    def __init__(self, uart: machine.UART):
        self.uart = uart
        
    def get_line(self):
        #await data over UART
        try:
            uart_str = self.uart.readline().decode("utf-8")
        except (UnicodeError, AttributeError) as e:
            uart_str = ""
            
        return uart_str
        
class LIV3(UART_Device):
    def __init__(self, uart: machine.UART,
                 wake: machine.Pin, reset: machine.Pin,
                 pps: machine.Pin):
        super().__init__(uart)
        self.wake = wake
        self.reset = reset
        self.pps = pps
        
        self.reset.value(1) #reset is active low, so set pin to high to force out of reset
        self.wake.value(1) #force wake up
        
    def pps_interrupt(self, *args):
        print("PPS!")
        self.led.toggle()
        
    def get_GPGGA_data(self):
        '''
        Block and await GPGGA string over UART from GPS module
        
        Returns:
            dict containing all GPGGA info
        '''
        
        #flush potentially stale data
        if self.uart.any() > 0:
            self.uart.flush()
        
        while True:
            #await data over UART
            while self.uart.any() == 0:
                pass
        
            try:
                uart_str = self.uart.readline().decode("utf-8")
            except UnicodeError:
                uart_str = "000000"
                
            if uart_str[0:6] == '$GPGGA':
                break
        
        #split all data into list
        '''
        c_buffer = []
        GPGGA_list = []
        for char in uart_str:
            if char != ',':
                c_buffer.append(char)
            else:
                GPGGA_list.append(''.join(c_buffer))
                c_buffer = []
        '''
        GPGGA_list = uart_str.split(',')
        
        GPGGA_dict = {}
        
        lat_arcmin = float(GPGGA_list[2])
        lon_arcmin = float(GPGGA_list[4])
        
        lat_remainder = (lat_arcmin % 100) / 60
        lon_remainder = (lon_arcmin % 100) / 60
        
        lat_deg = float(int(lat_arcmin / 100)) + lat_remainder
        lon_deg = float(int(lon_arcmin / 100)) + lon_remainder
        
        if GPGGA_list[3] == 'S':
            lat_deg *= -1
        if GPGGA_list[5] == 'W':
            lon_deg *= -1
        
        GPGGA_dict['t_utc'] = float(GPGGA_list[1])
        GPGGA_dict['lat_deg'] = lat_deg
        GPGGA_dict['lon_deg'] = lon_deg
        GPGGA_dict['alt_m'] = float(GPGGA_list[9])
        GPGGA_dict['und_m'] = float(GPGGA_list[11])
        GPGGA_dict['satellites'] = int(GPGGA_list[7])
        
        return GPGGA_dict
        
    def get_GPRMC_data(self):
        '''
        Block and await GPRMC string over UART from GPS module
        
        Returns:
            dict containing all GPRMC info
        '''
                #flush potentially stale data
        if self.uart.any() > 0:
            self.uart.flush()
        
        while True:
            #await data over UART
            while self.uart.any() == 0:
                pass
        
            try:
                uart_str = self.uart.readline().decode("utf-8")
            except UnicodeError:
                uart_str = "000000"
                
            if uart_str[0:6] == '$GPRMC':
                break
            
        GPRMC_list = uart_str.split(',')
        GPRMC_dict = {}
        
        lat_arcmin = float(GPRMC_list[3])
        lon_arcmin = float(GPRMC_list[5])
        
        lat_remainder = (lat_arcmin % 100) / 60
        lon_remainder = (lon_arcmin % 100) / 60
        
        lat_deg = float(int(lat_arcmin / 100)) + lat_remainder
        lon_deg = float(int(lon_arcmin / 100)) + lon_remainder
        
        if GPRMC_list[4] == 'S':
            lat_deg *= -1
        if GPRMC_list[6] == 'W':
            lon_deg *= -1
        
        try:
            mag_var = float(GPRMC_list[10])
        except ValueError:
            mag_var = 0
        
        if GPRMC_list[11] == 'E':
            mag_var *= -1
        
        GPRMC_dict['t_utc'] = float(GPRMC_list[1])
        GPRMC_dict['pos_status'] = GPRMC_list[2]
        GPRMC_dict['lat_deg'] = lat_deg
        GPRMC_dict['lon_deg'] = lon_deg
        GPRMC_dict['groundspeed_kn'] = float(GPRMC_list[7])
        GPRMC_dict['track_deg'] = float(GPRMC_list[8])
        GPRMC_dict['date_utc'] = int(GPRMC_list[9])
        GPRMC_dict['mag_var_deg'] = mag_var
        
        return GPRMC_dict
        
class TEL0132(UART_Device):
    def __init__(self, uart: machine.UART):
        super().__init__(uart)
        
    def get_time_and_position(self):
        '''
        Flush the UART buffer if full and grab the most recent UTC timestamp and coords from GPS
        
        Returns:
            (time, (lat, lon))
        '''
        if self.uart.any() > 0:
            self.uart.flush()
        
        while True:
            #wait for UART buffer to be full
            while self.uart.any() == 0:
                pass
            
            try:
                uart_str = self.uart.readline().decode("utf-8")
            except UnicodeError:
                uart_str = "000000"
            
            #exit once we get the right string
            if uart_str[0:6] == '$GNGGA':
                break
        
        #if no fix, return N/A
        if uart_str[6:8] == ',,':
            return ('N/A', (0,0))        
        
        gps_time = uart_str[7:9] + ':' + uart_str[9:11] + ':' + uart_str[11:13]
        gps_lat = int(uart_str[18:20]) + (float(uart_str[20:28]) / 60)
        gps_lon = int(uart_str[31:34]) + (float(uart_str[34:42]) / 60)

        #if south or west, make negative
        if uart_str[29] == 'S':
            gps_lat *= -1
        if uart_str[43] == 'W':
            gps_lon *= -1

        return (gps_time, (gps_lat, gps_lon))