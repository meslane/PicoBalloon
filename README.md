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

The Si5351 has ~10-20 Hz of measured drift across temperature from startup to steady state. It is reccomended to let the oscillator warm up for approximately 10 minutes to ensure transmission accuracy.

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
The temperature reading returned by the MS5607 is coupled to the temperature of the PCBA, which includes self-heating. As such, it will typically over-report relative to the temperature of its environment by approx. 10C - 20C.

## Power Specs

### Current Draw

Test run at 5.2 V / 25 C with 330 Ohm current limiting resistors. About 10 mA additional draw is observed when the PPS LED is on in this condition. For flight it is reccomended to populated the LED current limiting resistors with values of > 1 kOhms.

| State | Current Draw (mA) | Power Draw (mW) |
| -------- | --------  | -------- |
| All devices on + state machine stopped | 50 | 260 |
| All devices on + State machine active (no tone) | 60 | 312 |
| All devices on + Playing Tone | 70  | 364 |

### Solar Panels

For V2.1, I use these flexible solar panels from powerfilm: https://www.mouser.com/ProductDetail/730-MPT4.8-75

Note that their open circuit voltage of 7.4V is higher than the rated max input voltage of the BC on V2.0 and V2.1. On V2.2 this will be fixed by switching to a converter with a higher input voltage rating.

### Power Sequencing
Testing on V2.1 revealed that the RP2040 will get stuck in a latched state if it is powered off of solar arrays without tying the RUN pin to GND until the 3.3V rail is at full scale. On V2.2 this is fixed by directly connecting the RUN pin to the open drain PGOOD signal of the buck converter. This will automatically reset the RP2040 if the output power rail droops too low. 

# Tracking

## WSPR Carrier Frequency
WSPR TX frequencies are specified as an offset relative to a base frequency for each band:

| Band     | Base Freq |
| -------- | --------  |
| 20m      | 14.097.000 MHz |
| 40m      | 7.040.000 MHz  |

Ex, when `offsets = [40]` in config.json, the balloon wil transmit at 14.097.040 MHz (subject to thermal drift over temp).

## Telemetry System
This balloon supports the use of the U4B telemetry system: https://qrp-labs.com/flights/s4#protocol

The U4B telem system further divides callsigns into a series of channels: https://traquito.github.io/channelmap/

To avoid collisions, channels are divided by the minute (mod 10) when they transmit telemetry, the first two digits of the "telemetry callsign", and the frequency they transmit at.

It is reccomended to reserve a slot on the above site and update your config.json to the following:

- `wspr_offsets` = \[freq - base frequency for band\]
- `telemetry_call` = ID13
- `telemetry_minute` = Minute

### Telem Format
The following telemetry (along with the above ID13) is encoded into the callsign, grid square, and power report for a telemetry message:

| Telem       | Raw Range | Precision   | Decoded Range |
| --------    | --------  | --------    | -------- |
| Subsquare   | AA - XX   | 3 x 4 miles | N/A |
| Altitude    | 0 - 1067  | 20 meters   | 0 - 21340 meters |
| Temperature | 0 - 89    | 1 C         | -50 - 39 C |
| Voltage     | 0 - 39    | 0.05 V      | 3 - 4.95 V |
| Speed       | 0 - 41    | 2 knots     | 0 - 82 knots |
| GPS Valid   | 0 - 1     | 1 bit       | Boolean |
| GPS Health  | 0 - 1     | 1 bit       | Boolean |

This telem was developed for the QRPLabs U4B, which doesn't exactly match this ballon in terms of hardware specs. We subtract 1 volt from `V-IN` when reported to get it into this range, so +1 V should be added back to the reported telemetry to get the true measured voltage.

Similarly, instead of encoding GPS validity with the GPS valid flag, we instead encode which light sensor has a higher reading. If `l_front` > `l_back`, this flag will be 1, else 0.

### Tracking
If you have a reserved channel, you can then track your flight on this website: https://wsprtv.com/

# Assembly Guide

## Through-Hole Capacitors
C24 and C21 on V2.0 and beyond should be populated with supercapcitors to hold charge from the solar panels (in lieu of a battery).

C24 and C21 are wired in series and are connected to the solar cell input through a protection diode. Ensure that the caps you use are rated for > 3.0 V DC bias.

Populating C24 and C21 with cap values > 2.2 uF is reccomended when powering the board over USB on the ground. USB power is often very poorly filtered and the board's power rail may be too noisy to properly power the RP2040 when bulk caps are not present. On V2.2 and beyond this is fixed by adding an additional surface mount 22 uF cap to the input rail.

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

## v2.1 -> v2.2 Hwardware Changelog

- Switch from LM3671 to TPS629206 to support 17V max input voltage from solar panels
	- Connect RP2040 RUN pin to PGOOD on the TPS629206 to prevent brownouts due to low input voltage
- Update voltage divider for V_SOLAR to use 47k resistor for max V_SOLAR of 18.8V
- Add 22uF SMT capacitor to buck converter input for power filtering when through hole caps are unpopulated
- Update LED current limiting resistor values to 1k Ohms
- Delete soldermask opening on inverted F antenna

## v2.2 -> v2.3 Hardware Changelog

- Add NJG1156PCD GPS FEM to signal chain to improve acquisition time

# Bug List

- Messages pulled from the WSPR database sometimes have speed values that don't match what is reported on the balloon and the WSPR message reported in this case doesn't match what the balloon says it transmitted. Need to find out why.