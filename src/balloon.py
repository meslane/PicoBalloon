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
            self.band = config['wspr_band']
            self.offsets = config['wspr_offsets']
            self.tx_correction = config['tx_correction']
            self.telemetry_mode = config['telemetry_mode']
            self.telemetry_call = config['telemetry_call']
            self.log_to_file = config['log_to_file']
            
            #mod 10 of the time in minutes, determines when telemetry is sent in accordance with https://traquito.github.io/channelmap/
            if config['telemetry_minute'] > 0:
                self.telemetry_minute = config['telemetry_minute'] - 1
            else:
                self.telemetry_minute = 9
        
        #GPIO init
        if self.version == "1.0":
            CLKGEN_SCL = 22
            CLKGEN_SDA = 21
            CLKGEN_CHANNEL = 0
            CLKGEN_OUTPUT = 0
            
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
            CLKGEN_SDA = 20
            CLKGEN_SCL = 21
            CLKGEN_CHANNEL = 0
            CLKGEN_OUTPUT = 0
            
            GPS_TX = 16
            GPS_RX = 17
            GPS_WAKE = 15
            GPS_RESET = 14
            GPS_PPS = 18
            GPS_CHANNEL = 0
            
            ALTIMETER_MOSI = 3
            ALTIMETER_MISO = 4
            ALTIMETER_SCK = 2
            ALTIMETER_CS = 5
            ALTIMETER_CHANNEL = 0
            
            LED = 25
            
            V_IN_ADC_IN = 27
            V_SOLAR_ADC_IN = 26
            V_LSENS_BOT_ADC_IN = 28
            V_LSENS_TOP_ADC_IN = 29
        else:
            raise NotImplementedError

        #GPS Init
        gps_uart = machine.UART(GPS_CHANNEL, baudrate=9600,
                        tx=machine.Pin(GPS_TX), rx=machine.Pin(GPS_RX), timeout=100)
        gps_wake = machine.Pin(GPS_WAKE, machine.Pin.OUT)
        gps_reset = machine.Pin(GPS_RESET, machine.Pin.OUT)
        self.gps_pps = machine.Pin(GPS_PPS, machine.Pin.IN)
        self.gps = uart_device.LIV3(gps_uart, wake=gps_wake, reset=gps_reset,
                               pps=self.gps_pps)
        
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
            altimeter_spi = machine.SPI(baudrate=100000,
                polarity=0,
                phase=0,
                firstbit=machine.SPI.MSB,
                bits=8,
                id=ALTIMETER_CHANNEL,
                sck=machine.Pin(ALTIMETER_SCK),
                mosi=machine.Pin(ALTIMETER_MOSI),
                miso=machine.Pin(ALTIMETER_MISO))
        else:
            raise NotImplementedError
        
        self.altimeter = spi_device.MS5607(altimeter_spi, machine.Pin(ALTIMETER_CS, machine.Pin.OUT))
        
        #WSPR Clock Generator Init
        if self.version == "1.0":
            clockgen_i2c = machine.SoftI2C(scl=machine.Pin(CLKGEN_SCL),
                                           sda=machine.Pin(CLKGEN_SDA),
                                           freq=100000, timeout=10000)
        elif self.version == "1.1":
            clockgen_i2c = machine.I2C(id=CLKGEN_CHANNEL,
                                       scl=machine.Pin(CLKGEN_SCL),
                                       sda=machine.Pin(CLKGEN_SDA),
                                       freq=100000, timeout=10000)
        else:
            raise NotImplementedError        
        
        self.clockgen = i2c_device.SI5351(clockgen_i2c)
        
        #ADC Init
        self.v_in_adc = machine.ADC(V_IN_ADC_IN)
        self.v_solar_adc = machine.ADC(V_SOLAR_ADC_IN)
        self.l_front_adc = machine.ADC(V_LSENS_TOP_ADC_IN)
        self.l_back_adc = machine.ADC(V_LSENS_BOT_ADC_IN)
        
        #LED
        self.led = machine.Pin(LED, machine.Pin.OUT)
        
        #PPS
        self.pps_count = 0
        self.last_pps = 0
        
        #WSPR message
        self.tone_index = 0
        self.message = []
        
        self.offset_index = 0
        self.output = CLKGEN_OUTPUT
        
        #WSPR constants
        self.tone_period = 683 #ms
        self.tone_spacing = 1.465 #Hz
        self.message_length = 162 #tones
        
        #Transmit timer
        self.timer = machine.Timer(period=self.tone_period, mode = machine.Timer.PERIODIC,
                   callback=None)
        self.timer.deinit()
        
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
        
        #don't init watchdog to start
        self.watchdog = None

        #fun!
        self.loadchars = ['|', '/', '-', '\\']
        self.char_index = 0
        
        #start GPS interrupt only after everything else succeeds
        self.gps_pps.irq(trigger=machine.Pin.IRQ_RISING, handler=self.pps_interrupt)

    def pps_interrupt(self, *args):
        self.led.toggle()
        self.pps_count += 1
    
    def selftest(self):
        print("Running Built-In Hardware Self-Test...")
        
        status = {"Si5351": "FAIL",
                   "LIV3R": "FAIL",
                   "MS5607": "FAIL"}
        
        #test clockgen
        try:
            self.clockgen.i2c_write(0x19, 0x77)
            if self.clockgen.i2c_read(0x19) == 0x77:
                status['Si5351'] = "PASS"
            self.clockgen.i2c_write(0x19, 0x00)
        except OSError:
            pass
        
        #test GPS
        status['LIV3R'] = "PASS"
        #await data over UART
        i = 0
        while self.gps.uart.any() == 0:
            i += 1
            time.sleep(0.01)
            
            if i > 100:
                status['LIV3R'] = "FAIL" #fail if we time out
                break
        
        #test Altimeter
        try:
            prom = int.from_bytes(self.altimeter.read_prom(0), "big")
            if prom != 0x0000 and prom != 0xFFFF:
                status['MS5607'] = "PASS"
        except OSError:
            pass
        
        for key in status.keys():
            print("{} - {}".format(key, status[key]))
        
        return status
    
    def configure_clockgen(self):
        '''
        Set transmit freq and get frontend ready
        '''
        self.clockgen.configure_output_driver(self.output)
        self.clockgen.enable_output(self.output, False)

    def transmit_message(self):
        '''
        start timer and begin transmitting
        '''
        self.timer.init(period = self.tone_period,
                        mode = machine.Timer.PERIODIC,
                        callback = self.transmit_next_tone)

    def transmit_next_tone(self, *args):
        '''    
        Transmit the next tone in the message buffer
        This should be called from a clock interrupt, not directly
        '''
        #make sure we got one in the chamber
        assert len(self.message) == self.message_length
        assert self.band != None
        assert self.offsets != None
        assert self.output != None
        
        if self.tone_index >= 162:
            self.clockgen.enable_output(self.output, False)
            self.timer.deinit() #message is finished, stop timer
            self.tone_index = 163
        else:
            if self.tone_index == 0:
                self.clockgen.enable_output(self.output, True)
            
            if isinstance(self.offsets, int):
                tone_offset = self.offsets + (self.message[self.tone_index] * self.tone_spacing)
            else:
                tone_offset = self.offsets[self.offset_index] + (self.message[self.tone_index] * self.tone_spacing)
            
            self.tone_index += 1
            self.clockgen.transmit_wspr_tone(self.output, self.band,
                                             tone_offset, correction=self.tx_correction)
    def update_telemetry(self):
        gprmc_dict = self.gps.get_GPRMC_data()
        gps_dict = self.gps.get_GPGGA_data()
        alt_dict = self.altimeter.get_pressure_and_temperature()
        v_in = adc_avg(self.v_in_adc, 10) * (3.3/65536)
        v_solar = adc_avg(self.v_solar_adc, 10) * (3.3/65536)
        l_front = adc_avg(self.l_front_adc, 10) * (3.3/65536)
        l_back = adc_avg(self.l_back_adc, 10) * (3.3/65536)
        
        self.telemetry['lat_deg'] = gps_dict['lat_deg']
        self.telemetry['lon_deg'] = gps_dict['lon_deg']
        self.telemetry['t_utc'] = gps_dict['t_utc']
        self.telemetry['alt_m'] = gps_dict['alt_m']
        self.telemetry['satellites'] = gps_dict['satellites']
        self.telemetry['groundspeed_kn'] = gprmc_dict['groundspeed_kn']
        
        self.telemetry['temp_c'] = alt_dict['t_c']
        self.telemetry['p_mbar'] = alt_dict['p_mbar']
        
        self.telemetry['v_solar'] = v_solar
        self.telemetry['v_in'] = v_in
        self.telemetry['l_front'] = l_front
        self.telemetry['l_back'] = l_back
    
    def tick(self):
        start_state = self.state
        
        if self.state == "init":
            self.pps_count = 0
            #self.watchdog = machine.WDT(timeout=2000) #2s watchdog expiration
            self.state = "wait_for_time"
            
        elif self.state == "wait_for_time":
            gps_dict = self.gps.get_GPGGA_data()
            
            #print(gps_dict)
            print("{}       ".format(gps_dict['t_utc']), end='\r')
            
            if gps_dict['t_utc'] > (self.pps_count + 10) and gps_dict['satellites'] > 0:
                print()
                self.state = "wait_for_fix"
        
        elif self.state == "wait_for_fix":
            gps_dict = self.gps.get_GPGGA_data()
            
            print("Satellites: {} {}       ".format(gps_dict['satellites'],
                                             self.loadchars[self.char_index]),
                                             end='\r')
            self.char_index = self.char_index + 1 if self.char_index < 3 else 0
            
            if int(gps_dict['lat_deg']) != 0 or int(gps_dict['lon_deg']) != 0:
                print()
                self.configure_clockgen()
                self.state = "collect_telemetry"
         
        elif self.state == "collect_telemetry":
            gprmc_dict = self.gps.get_GPRMC_data()
            
            d_now = gprmc_dict['date_utc']
            t_now = gprmc_dict['t_utc']
            wspr_text = ""
            
            #do normal WSPR message
            if (self.telemetry_mode == "WSPR") or (self.telemetry_mode == "U4B" and (int(t_now) // 100) % 10 != self.telemetry_minute):
                #update telemetry only once every 4 minutes to avoid tears in location
                self.update_telemetry()
                print(self.telemetry)
                
                grid_square = wspr.LL2GS(self.telemetry['lat_deg'], self.telemetry['lon_deg'])[:4]
                self.message = wspr.generate_wspr_message(self.callsign, grid_square, 10)
                wspr_text = "{} {} {}".format(self.callsign, grid_square, 10)
                print(wspr_text)
            
            #transmit U4B telemetry every other message
            elif (self.telemetry_mode == "U4B" and (int(t_now) // 100) % 10 == self.telemetry_minute):
                #grab telem if at beginning so we know we have good data
                if self.telemetry['v_solar'] == 0 and self.telemetry['v_in'] == 0:
                    self.update_telemetry()
                    print(self.telemetry)
                
                subsquare = wspr.LL2GS(self.telemetry['lat_deg'], self.telemetry['lon_deg'])[-2:]

                #define GPS = healthy if it sees at least 8 satellites
                if self.telemetry['satellites'] >= 8:
                    gps_health = 1
                else:
                    gps_health = 0
                    
                #encode which brightness sensor is reading higher as the normal U4B GPS status flag
                #this will give us a very coarse reading on which direction the tracker is facing
                if self.telemetry['l_front'] >= self.telemetry['l_back']:
                    board_orientation = 1
                else:
                    board_orientation = 0

                callsign = wspr.encode_subsquare_and_altitude_telemetry(self.telemetry_call, subsquare, int(self.telemetry['alt_m']))
                gs_and_power = wspr.encode_engineering_telemetry(self.telemetry['temp_c'],
                                                                 self.telemetry['v_solar'] + 2, #get this into the range U4B expects
                                                                 self.telemetry['groundspeed_kn'],
                                                                 board_orientation,
                                                                 gps_health)
                
                self.message = wspr.generate_wspr_message(callsign, gs_and_power[0], gs_and_power[1])
                wspr_text = "{} {} {}".format(callsign, gs_and_power[0], gs_and_power[1])
                print(wspr_text)
            
            if self.log_to_file == True:
                with open("log.csv", "a") as f:
                    f.write("{},{},{}\n".format(d_now, t_now, wspr_text))
            
            self.state = "wait_for_transmit"

        elif self.state == "wait_for_transmit":
            gps_dict = self.gps.get_GPGGA_data()
            
            #if we lose lock, go back
            if int(gps_dict['lat_deg']) == 0 and int(gps_dict['lon_deg']) == 0:
                self.state = "wait_for_fix"
            else:
                t_gps = int(gps_dict['t_utc'])
                if ((t_gps // 100) % 2 == 1) and (t_gps % 100 == 59):
                    self.state = "await_pps"
        
        elif self.state == "await_pps":
            if self.pps_count != self.last_pps:
                self.transmit_message()
                self.state = "transmit"
        
        elif self.state == "transmit":
            if self.tone_index == 163:
                self.tone_index = 0
                self.state = "collect_telemetry"
        
        self.last_pps = self.pps_count
        
        if self.state != start_state:
            print("{} - {}".format(self.state, self.pps_count))
            
        #self.watchdog.feed() #pet watchdog to prevent resetting if loop is still active
            
    def print_telemetry(self):
        self.update_telemetry()
        print(self.telemetry)