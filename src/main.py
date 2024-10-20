import machine
import sys
import time

import i2c_device
import uart_device
import spi_device
import wspr

'''
i2c = machine.I2C(0, scl=machine.Pin(27), sda=machine.Pin(26),
                  freq=100000, timeout=500000)
'''
#uart0 = machine.UART(0, baudrate=9600, tx=machine.Pin(16), rx=machine.Pin(17), timeout=100)
#pps_in = machine.Pin(18, machine.Pin.IN)

#beacon = wspr.Beacon(i2c, uart0, pps_in)

#beacon.generate_message("W6NXP", "DM03", 13)
#beacon.configure_clockgen("20m", (80,85,90,95,100,105,110,115,120))


CLKGEN_SCL = 22
CLKGEN_SDA = 21
CLKGEN_CHANNEL = 0

clockgen_i2c = machine.SoftI2C(scl=machine.Pin(CLKGEN_SCL), sda=machine.Pin(CLKGEN_SDA),
                            freq=100000, timeout=500000)
clockgen = i2c_device.SI5351(clockgen_i2c)

gps_uart = machine.UART(0, baudrate=9600, tx=machine.Pin(16), rx=machine.Pin(17), timeout=100)
gps_wake = machine.Pin(15, machine.Pin.OUT)
gps_reset = machine.Pin(14, machine.Pin.OUT)
gps = uart_device.LIV3(gps_uart, wake=gps_wake, reset=gps_reset)

altimeter_spi = machine.SoftSPI(baudrate=10000,
                            polarity=0,
                            phase=0,
                            firstbit=machine.SPI.MSB,
                            bits=8,
                            sck=machine.Pin(4),
                            mosi=machine.Pin(5),
                            miso=machine.Pin(6))
altimeter = spi_device.MS5607(altimeter_spi, machine.Pin(7, machine.Pin.OUT))

#clockgen.register_dump()
clockgen.configure_output_driver(CLKGEN_CHANNEL)
clockgen.enable_output(CLKGEN_CHANNEL, True)
clockgen.transmit_wspr_tone(channel=0, band="20m", offset=100)

'''
while True:
    while gps.uart.any() == 0:
        pass
    
    try:
        uart_str = gps.uart.readline().decode("utf-8")
        print(uart_str)
    except UnicodeError:
        pass
'''

#altimeter.reset()
while True:
    #print(altimeter.convert_and_read(1,osr=4))
    #print(altimeter.convert_and_read(2,osr=4))
    print(altimeter.get_temperature())
    time.sleep(0.5)
    
    '''
    for i in range(8):
        print(altimeter.read_prom(i))
    '''  
