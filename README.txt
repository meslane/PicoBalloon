~==== RP2040 ====~

~==== Si5351 ====~

== PIN MAPPINGS ==
-SDA = GPIO21
-SCL = GPIO22

== CALIBRATION ==

The 25 MHz crystals used is not particuarly accurate, and calibration 
with a frequency counter may be needed to ensure that the output tone 
matches the programmed frequency.


== WARMUP ==

The Si5351 has ~10-20 Hz of measured drift across temperature from 
startup to steady state. It is reccomended to let the oscillator 
warm up for approximately 30 minutes to ensure transmission accuracy.

~==== TESEO LIV3R GPS ====~

== PIN MAPPINGS ==
-UART TX = GPIO16
-UART RX = GPIO17
-WAKE = GPIO15
-RESET = GPIO14
-PPS = GPIO18

~==== MS5607 Altimeter ====~

== PIN MAPPINGS ==
-SCK = GPIO4
-MOST = GPIO5
-MISO = GPIO6
-CS = GPIO7

== DATASHEET NOTES ==
-D1 = pressure reading
-D2 = temperature reading

== Temperature Reading ==
The temperature reading returned by the MS5607 is coupled to the
temperature of the PCBA, which includes self-heating. As such,
it will typically over-report relative to the temperature of its
environment by approx. 10C - 20C.

~==== v1.0 Known Issues and Desired Changes ====~

-Change header for SWD to 2.54mm pin header from test points - DONE
-Add bleeder resistor to supercap - DONE
-Change HF antenna and solar inputs from 2.54mm headers to screw terminals - WON'T DO
-Remap I2C for Si5351 to use hardware I2C - DONE
-Remap SPI for MS5607 to use hardware SPI - DONE
-Change some 0402s to 0603s for easier soldering - WON'T DO
-Add inveted F GPS antenna - DONE
-Add option for UFL port for external GPS antenna - WON'T DO
-Add test points to serial lines (I2C/SPI/maybe UART) - DONE
-Add filtering to ADC solar/output voltage sense lines - DONE
-Add output capacitance to boost converter - DONE
