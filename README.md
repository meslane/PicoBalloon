```
###  ###  ##  #  ##   #  #   #    #   #  ##      # # ###   ###
#  #  #  #   # # # # # # #   #   # # # # # #     # #   #   # #
###   #  #   # # ##  ### #   #   # # # # # #     # # ###   # #
#     #  #   # # # # # # #   #   # # # # # #     # # #     # #
#    ###  ##  #  ##  # # ### ###  #   #  # #      #  ### # ###
```

# Hardware Details

## RP2040

## Si5351

### PIN MAPPINGS
- SDA = GPIO21
- SCL = GPIO22

### CALIBRATION

The 25 MHz crystal used is not particuarly accurate, and calibration 
with a frequency counter may be needed to ensure that the output tone 
matches the programmed frequency.

### WARMUP

The Si5351 has ~10-20 Hz of measured drift across temperature from 
startup to steady state. It is reccomended to let the oscillator 
warm up for approximately 30 minutes to ensure transmission accuracy.

## TESEO LIV3R GPS

### PIN MAPPINGS
- UART TX = GPIO16
- UART RX = GPIO17
- WAKE = GPIO15
- RESET = GPIO14
- PPS = GPIO18

## MS5607 Altimeter

### PIN MAPPINGS
- SCK = GPIO4
- MOST = GPIO5
- MISO = GPIO6
- CS = GPIO7

### DATASHEET NOTES 
- D1 = pressure reading
- D2 = temperature reading

### Temperature Reading
The temperature reading returned by the MS5607 is coupled to the
temperature of the PCBA, which includes self-heating. As such,
it will typically over-report relative to the temperature of its
environment by approx. 10C - 20C.

# Change Logs
## v1.0 -> v1.1 Hardware Changelog

- Change header for SWD to 2.54mm pin header from test points
- Add bleeder resistor to supercap
- Remap I2C for Si5351 to use hardware I2C
- Remap SPI for MS5607 to use hardware SPI
- Add inveted F GPS antenna
- Add test points to serial lines (I2C/SPI/maybe UART)
- Add filtering to ADC solar/output voltage sense lines
- Add output capacitance to boost converter

## v1.1 -> v2.0 Hardware Changelog

- Switch to 5V -> 3.3V buck converter to enable use of higher voltage solar cells
- Delete the 5V -> 2.5V LDO and power the converter directly off the +5V USB source instead
- Delete the GPS LNA + filter and direct connect antenna to the RF_IN pin on the GPS module
	- This is fine because there is little routing loss and therefore low NF degradation between the module and antenna
	- Antenna will have the rolloff of a 1st order bandpass filter for out of band rejection
- Add dedicated through hole pin for a wire antenna as a backup in case the inverted F antenna doesn't work
- Add soldermask opening on inverted F to allow cutting + soldering GND
- Update silkscreen to add pinout labels for debug header + V_SOLAR input voltage range

## v2.0 -> v2.1 Hardware Changelog

- Add voltage dividers to power rail ADC telemetry lines

# Telemetry System
This balloon supports the use of the U4B telemetry system: https://qrp-labs.com/flights/s4#protocol