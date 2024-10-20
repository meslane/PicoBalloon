import machine
import sys
import time

import i2c_device
import uart_device
import spi_device
import wspr

CLKGEN_SCL = 22
CLKGEN_SDA = 21
CLKGEN_CHANNEL = 0

clockgen_i2c = machine.SoftI2C(scl=machine.Pin(CLKGEN_SCL), sda=machine.Pin(CLKGEN_SDA),
                            freq=100000, timeout=500000)
clockgen = i2c_device.SI5351(clockgen_i2c)

gps_uart = machine.UART(0, baudrate=9600,
                        tx=machine.Pin(16), rx=machine.Pin(17), timeout=100)
gps_wake = machine.Pin(15, machine.Pin.OUT)
gps_reset = machine.Pin(14, machine.Pin.OUT)
gps_pps = machine.Pin(18, machine.Pin.IN)
gps = uart_device.LIV3(gps_uart, wake=gps_wake, reset=gps_reset,
                       pps=gps_pps)

altimeter_spi = machine.SoftSPI(baudrate=100000,
                            polarity=0,
                            phase=0,
                            firstbit=machine.SPI.MSB,
                            bits=8,
                            sck=machine.Pin(4),
                            mosi=machine.Pin(5),
                            miso=machine.Pin(6))
altimeter = spi_device.MS5607(altimeter_spi, machine.Pin(7, machine.Pin.OUT))

clockgen.configure_output_driver(CLKGEN_CHANNEL)
clockgen.enable_output(CLKGEN_CHANNEL, True)
clockgen.transmit_wspr_tone(channel=0, band="20m", offset=100)

v_in_adc = machine.ADC(26)
v_solar_adc = machine.ADC(27)

def adc_avg(adc, counts):
    adc_sum = 0
    
    for i in range(counts):
        adc_sum += adc.read_u16()
        
    return adc_sum / counts

while True:
    print(gps.get_GPGGA_data())
    alt_dict = altimeter.get_pressure_and_temperature()
    print(alt_dict)
    
    v_in = adc_avg(v_in_adc, 10) * (3.3/65536)
    v_solar = adc_avg(v_solar_adc, 10) * (3.3/65536)
    
    print("V_IN: {:0.2f}V".format(v_in))
    print("V_SOLAR: {:0.2f}V".format(v_solar))
    
    print()
    
    time.sleep(0.01)
