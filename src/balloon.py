import machine
import sys
import time
import json

import uart_device
import spi_device
import i2c_device
import wspr

def adc_avg(adc, counts):
    adc_sum = 0
    
    for i in range(counts):
        adc_sum += adc.read_u16()
        
    return adc_sum / counts

class Balloon:
    def __init__(self, config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
            
            self.version = config['version']
            self.callsign = config['callsign']
            self.wspr_band = config['wspr_band']
            self.wspr_offset = config['wspr_offset']
            
            self.pps_count = 0
            
        if self.version == "1.0":
            CLKGEN_SCL = 22
            CLKGEN_SDA = 21
            CLKGEN_CHANNEL = 0
            
            GPS_TX = 16
            GPS_RX = 17
            GPS_WAKE = 15
            GPS_RESET = 14
            GPS_PPS = 18
            GPS_CHANNEL = 0
            
            ALTIMETER_MOSI = 5
            ALTIMETER_MISO = 6
            ALTIMETER_SCK = 4
            ALTIMETER_CS = 7
            
            LED = 25
            
            V_IN_ADC_IN = 26
            V_SOLAR_ADC_IN = 27
        elif self.version == "1.1":
            raise NotImplementedError

        #GPS Init + Interrupt
        gps_uart = machine.UART(GPS_CHANNEL, baudrate=9600,
                        tx=machine.Pin(GPS_TX), rx=machine.Pin(GPS_RX), timeout=100)
        gps_wake = machine.Pin(GPS_WAKE, machine.Pin.OUT)
        gps_reset = machine.Pin(GPS_RESET, machine.Pin.OUT)
        self.gps_pps = machine.Pin(GPS_PPS, machine.Pin.IN)
        self.gps = uart_device.LIV3(gps_uart, wake=gps_wake, reset=gps_reset,
                               pps=self.gps_pps)
        
        self.gps_pps.irq(trigger=machine.Pin.IRQ_RISING, handler=self.pps_interrupt)
        
        #Altimeter Init
        if self.version == "1.0":
            altimeter_spi = machine.SoftSPI(baudrate=100000,
                polarity=0,
                phase=0,
                firstbit=machine.SPI.MSB,
                bits=8,
                sck=machine.Pin(ALTIMETER_SCK),
                mosi=machine.Pin(ALTIMETER_MOSI),
                miso=machine.Pin(ALTIMETER_MISO)) 
        elif self.version == "1.1":
            raise NotImplementedError
        
        self.altimeter = spi_device.MS5607(altimeter_spi, machine.Pin(ALTIMETER_CS, machine.Pin.OUT))
        
        #WSPR Clock Generator Init
        if self.version == "1.0":
            clockgen_i2c = machine.SoftI2C(scl=machine.Pin(CLKGEN_SCL),
                                           sda=machine.Pin(CLKGEN_SDA),
                                           freq=100000, timeout=500000)
        elif self.version == "1.1":
            raise NotImplementedError
        
        self.clockgen = i2c_device.SI5351(clockgen_i2c)
        
        #ADC Init
        self.v_in_adc = machine.ADC(V_IN_ADC_IN)
        self.v_solar_adc = machine.ADC(V_SOLAR_ADC_IN)
        
        #LED
        self.led = machine.Pin(LED, machine.Pin.OUT)
        
        #Set state
        self.state = "init"
        
        #init telemetry dict
        self.telemetry = {"lat_deg": 0.0,
                          "lon_deg": 0.0,
                          "alt_m": 0.0,
                          "satellites": 0,
                          "temp_c": 0.0,
                          "p_mbar": 0.0,
                          "v_in": 0.0,
                          "v_solar": 0.0,
                          "l_front": 0.0,
                          "l_back": 0.0}

    def pps_interrupt(self, *args):
        self.led.toggle()
        self.pps_count += 1

    def tick(self):
        print(self.state)
        
        if self.state == "init":
            self.pps_count = 0
            self.state = "wait_for_time"
            
        elif self.state == "wait_for_time":
            gps_dict = self.gps.get_GPGGA_data()
            
            if gps_dict['t_utc'] > (self.pps_count + 10):
                self.state = "wait_for_fix"
        
        elif self.state == "wait_for_fix":
            gps_dict = self.gps.get_GPGGA_data()
            
            if int(gps_dict['lat_deg']) != 0 or int(gps_dict['lon_deg']) != 0:
                self.state = "collect_telemetry"
         
        elif self.state == "collect_telemetry":
            gps_dict = self.gps.get_GPGGA_data()
            alt_dict = self.altimeter.get_pressure_and_temperature()
            v_in = adc_avg(self.v_in_adc, 10) * (3.3/65536)
            v_solar = adc_avg(self.v_solar_adc, 10) * (3.3/65536)
            
            self.telemetry['lat_deg'] = gps_dict['lat_deg']
            self.telemetry['lon_deg'] = gps_dict['lon_deg']
            self.telemetry['alt_m'] = gps_dict['alt_m']
            self.telemetry['satellites'] = gps_dict['satellites']
            
            self.telemetry['temp_c'] = alt_dict['t_c']
            self.telemetry['p_mbar'] = alt_dict['p_mbar']
            
            self.telemetry['v_solar'] = v_solar
            self.telemetry['v_in'] = v_in
            
            self.state = "wait_for_transmit"

        elif self.state == "wait_for_transmit":
            gps_dict = self.gps.get_GPGGA_data()
            
            #if we lose lock, go back
            if int(gps_dict['lat_deg']) == 0 and int(gps_dict['lon_deg']) == 0:
                self.state = "wait_for_fix"
            else:
                t_gps = int(gps_dict['t_utc'])
                print(t_gps)
                print(t_gps // 100)
                if ((t_gps // 100) % 2 == 1) and (t_gps % 100 == 59):
                    self.state = "await_pps"
        
        elif self.state == "await_pps":
            pass
        
        elif self.state == "transmit":
            pass