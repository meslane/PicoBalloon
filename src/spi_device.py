import machine
import time
import struct
import math

class SPI_Device:
    def __init__(self, spi: machine.SPI, cs: machine.Pin):
        self.spi = spi
        self.cs = cs
        
        self.cs.value(1) #set CS high to deselect chip by default
        
    def spi_write_byte(self, data):
        byte = struct.pack(">B", data)
        #print(byte)
        self.spi.write(byte)
        
class MS5607(SPI_Device):
    def __init__(self, spi: machine.SPI, cs: machine.Pin):
        super().__init__(spi, cs)
        
        #reset on init to allow coefficients to load into PROM
        self.reset()
        
        #load calibration coefficients from PROM
        self.ROM = []
        for i in range(0,8):
            self.ROM.append(int.from_bytes(self.read_prom(i), "big"))
            
        print(self.ROM)
        
    def reset(self):
        self.cs.value(0)
        self.spi_write_byte(0x1E) #send reset command
        time.sleep(10e-3) #wait 10ms for reset to complete
        self.cs.value(1)
        
    def convert_and_read(self, d, osr=4):
        '''
        Begin result conversion on the altimeter and return the raw result for post-processing
        
        Args:
            d: Convert D1 (pressure) or D2 (temperature)
            osr: Sensor oversampling rate (default=4)
        '''
        
        #D1 = pressure, D2 = temperature
        assert 1 <= d <= 2
        assert 0 <= osr <= 4
        convert_command = 0x40 + ((d - 1) * 16) + (2 * osr)

        #start conversion
        self.cs.value(0)
        self.spi_write_byte(convert_command)
        time.sleep(20e-3)
        self.cs.value(1)
        
        time.sleep(5e-3)
        
        #start ADC read
        self.cs.value(0)
        self.spi_write_byte(0x00)
        raw_data = self.spi.read(3)
        self.cs.value(1)
        
        return int.from_bytes(raw_data, "big")
    
    def read_prom(self, addr):
        address = 0xA0 + (2 * addr)
        
        self.cs.value(0)
        self.spi_write_byte(address)
        word = self.spi.read(2)
        self.cs.value(1)
        
        return word
    
    def get_temperature(self):
        D2 = self.convert_and_read(2)
        C5 = self.ROM[5]
        C6 = self.ROM[6]
        
        dT = D2 - C5 * 256
        
        T = 2000 + dT * (C6 / (2 ** 23))
        
        return T / 100