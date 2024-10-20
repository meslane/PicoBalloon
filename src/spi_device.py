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
        '''
        Reset the chip
        '''
        self.cs.value(0)
        self.spi_write_byte(0x1E) #send reset command
        time.sleep(10e-3) #wait 10ms for reset to complete
        self.cs.value(1)
        
    def convert_and_read(self, d: int, osr: int=4):
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
        time.sleep(20e-3) #TODO: replace these with hardware sleeps
        self.cs.value(1)
        
        time.sleep(5e-3)
        
        #start ADC read
        self.cs.value(0)
        self.spi_write_byte(0x00)
        raw_data = self.spi.read(3)
        self.cs.value(1)
        
        return int.from_bytes(raw_data, "big")
    
    def read_prom(self, addr: int):
        '''
        Read from the chip's factory programmed PROM
        
        Args:
            addr: PROM address to read (0 - 7)
        '''
        assert 0 <= addr <= 8        
        
        address = 0xA0 + (2 * addr)
        
        self.cs.value(0)
        self.spi_write_byte(address)
        word = self.spi.read(2)
        self.cs.value(1)
        
        return word
    
    def get_temperature(self):
        '''
        Read and calculate the calibrated temperature
        '''
        D2 = self.convert_and_read(2)
        C5 = self.ROM[5]
        C6 = self.ROM[6]
        
        dT = D2 - C5 * 256
        
        T = 2000 + dT * (C6 / (2 ** 23))
        
        return T / 100
    
    def get_pressure_and_temperature(self):
        '''
        Read and calculate calibrated temperature and pressure
        '''
        D1 = self.convert_and_read(1)
        D2 = self.convert_and_read(2)
        
        C1 = self.ROM[1]
        C2 = self.ROM[2]
        C3 = self.ROM[3]
        C4 = self.ROM[4]
        C5 = self.ROM[5]
        C6 = self.ROM[6]
        
        dT = D2 - C5 * 256
        OFF = C2 * (2 ** 17) + (C4 * dT) / (2 ** 6)
        SENS = C1 * (2 ** 16) + (C3 * dT) / (2 ** 7)
        
        P = (D1 * SENS / (2 ** 21) - OFF) / (2 ** 15)
        T = 2000 + dT * (C6 / (2 ** 23))
        
        results_dict = {"p_mbar": P / 100,
                        "t_c": T / 100}
        return results_dict
    
    def get_altitude(self, p_mbar: float):
        '''
        Convert barometric pressure in millibars to altitude in meters
        '''
        p_ref = 1013
        return 44330 * (1 - (p_mbar/p_ref) ** (1/5.255))