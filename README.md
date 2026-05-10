```
  ____  _           ____        _ _                    __     ______    _ 
 |  _ \(_) ___ ___ | __ )  __ _| | | ___   ___  _ __   \ \   / /___ \  / |
 | |_) | |/ __/ _ \|  _ \ / _` | | |/ _ \ / _ \| '_ \   \ \ / /  __) | | |
 |  __/| | (_| (_) | |_) | (_| | | | (_) | (_) | | | |   \ V /  / __/ _| |
 |_|   |_|\___\___/|____/ \__,_|_|_|\___/ \___/|_| |_|    \_/  |_____(_)_|
```

# Hardware Details

## RP2040

All versions of the Picoballon to date use the RP2040 MCU with the micropython bootloader.

### Bootloader Installation

To install the micropython bootloader, download the **Pico** image from this webpage: https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico/3

To flash your picoballoon, short the `BOOT` pin in the debug header (labeled on the bottom side silkscreen on V2.0 and beyond) to GND. With `BOOT` shorted, plug the board into USB. If you were successful, you should see the board show up as a mass storage device in file explorer. To flash the board, drag and drop the downloaded image into this folder. This should cause the device to reboot.

After flashing, remove the jumper between `BOOT` and GND, and plug the board in again normally. It should show up as a serial device. On an un-programmed board, you should be dropped into a micropython shell when you connect to it over PuTTY or another serial terminal of your choosing.

### Programming (Thonny IDE)

Using the Thonny IDE, your flashed board should show up as an RP2040 serial device in the bottom right. 

To program your board with the picoballon software, navigate to the picoballoon src folder in the left side file plane, highlight all files in the folder, right click, and select: "Upload to /". If you are connected to a board, this will upload all code files to your picoballoon. Now, whenever the board is powered in headless mode, it will automatically run the balloon state machine.

### ADC Channels

The RP2040 has 4x ADCs, which are mapped as follows on V1.1 and beyond (but voltage sense is only functional on V2.1 and beyond).

| GPIO Pin | Channel   |
| -------- | --------  |
| P26      | V_IN      |
| P27      | V_SOLAR   |  
| P28      | LSENS_BOT |
| P29      | LSENSE_TOP|

#### Light Sensor Calibration
The board has a top and bottom light sensor to give a coarse measure of board orientation relative to the sun while in flight. These sensors should also be calibrated to ensure best accuracy. 

The reccomended procedure to calibrate the light sensors is to hold the board up to a bright light and record the maximum reading when each side is fipped to face the light source. Measure the ratio between the top and bottom sensor, and apply it as a correction using the `lsense_top_correction` and `lsense_bot_correction` fields in the config file. These correction factors are multiplied by the raw reading, so the default factor of 1 == no correction.

## Si5351

The Si5351 is a CMOS clock generator that serves as the FM transmitter for the balloon's WSPR beacon. It must pass the ballon's selftest on startup in order to start the state machine.

### PIN MAPPINGS

| GPIO Pin | Si5351    |
| -------- | --------  |
| P21      | SDA       |
| P22      | SCL       |

### CALIBRATION

The 25 MHz crystal used is not particuarly accurate, and calibration with a frequency counter is needed to ensure that the output tone matches the programmed frequency.

In the serial console, hit c + ENTER when prompted to enter calibration mode. This will play a constant tone at the frequency printed in console. Measure the frequency of this tone on a spectrum analyzer and set the `tx_correction` field in the config.json file to  `-1 * delta_f`, where `delta_f` is the measured offset between the specified frequency and the measured frequency

### WARMUP

The Si5351 has ~10-20 Hz of measured drift across temperature from 
startup to steady state. It is reccomended to let the oscillator 
warm up for approximately 10 minutes to ensure transmission accuracy.

## TESEO LIV3R GPS

The LIV3R is the ballon's GPS module which is used to get position and altitude fixes. It must pass the ballon's selftest on startup in order to start the state machine.

### PIN MAPPINGS

| GPIO Pin | LIV3R     |
| -------- | --------  |
| P14      | RESET     |
| P15      | WAKE      |
| P16      | UART TX   |
| P17      | UART RX   |
| P18      | PPS       |

## MS5607 Altimeter

The MS5607 is a barimetric pressure and temperature sensor. It is not required to function for the balloon to work in U4B telemetry mode, and the state machine will still proceed if it fails the built-in selftest.

### PIN MAPPINGS
- SCK = GPIO4
- MOSI = GPIO5
- MISO = GPIO6
- CS = GPIO7

| GPIO Pin | MS5607    |
| -------- | --------  |
| P4       | SCK       |
| P5       | MOSI      |
| P6       | MISO      |
| P7       | CS        |

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