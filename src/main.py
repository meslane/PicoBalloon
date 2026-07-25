import balloon
import time
import machine
import sys
import select
import wspr

def main():
    b = balloon.Balloon("config.json", "geofence.json")

    hw_status = b.selftest()
    
    mode = "selftest"
    
    if hw_status['Si5351'] == "FAIL" or hw_status['LIV3R'] == "FAIL" or hw_status['PPS'] == "FAIL":
        print("Self-test failed on critical component! Holding for 5s before resetting...")
        mode = "reset_sleep"
    elif hw_status['MS5607'] == "FAIL":
        print("Self-test failed on non-critical component. Starting state machine...")
    else:
        print("Self-test passed! Starting state machine in 10 seconds")
        print("Press 't' + ENTER to enter raw telemetry mode")
        print("Press 'c' + ENTER to play the 20m calibration tone")
        print("Press 'g' + ENTER to stream raw GPS data")
        print("Press ENTER to start state machine immediately")
        
        t_start = time.time()
        while True:
            spoll = select.poll()
            spoll.register(sys.stdin, select.POLLIN)

            if spoll.poll(0):  # Check for input without blocking
                char_in = sys.stdin.read(1)
                
                if char_in == 't':
                    mode = "telemetry"
                    break
                elif char_in == 'c':
                    mode = "calibration"
                    break
                elif char_in == 'g':
                    mode = "gps_stream"
                    break
                elif char_in == '\n':
                    mode = "state_machine"
                    break
                
            if (time.time() - t_start) >= 10:
                mode = "state_machine"
                break

    if mode == "reset_sleep":
        time.sleep(5) #nominally 10s
        machine.reset()
    elif mode == "telemetry":
        while True:
            b.print_telemetry()
            
            # Print expected W6NXP telem if using this mode
            if b.telemetry_mode == "W6NXP":
                # Subsquate / number of sats
                wspr_pwr = wspr.encode_w6nxp_sat_count(b.telemetry['satellites'])
                full_grid = wspr.LL2GS(b.telemetry['lat_deg'], b.telemetry['lon_deg'])
                grid_square = full_grid[:4]
                telem_call = full_grid[-2:]
                callsign = b.w6nxp_telem_prefix + telem_call
                print(f"Position + sat count telemetry: {callsign} {grid_square} {wspr_pwr}")
                
                # Altitude telem
                telem_call, grid_square, wspr_pwr = wspr.encode_w6nxp_alt_telem(b.telemetry['p_mbar'],
                                                                                b.telemetry['alt_m'],
                                                                                b.telemetry['groundspeed_kn'])
                callsign = b.w6nxp_telem_prefix + telem_call
                print(f"Altitude telemetry: {callsign} {grid_square} {wspr_pwr}")
                
                # ADC + Temp telem
                telem_call, grid_square, wspr_pwr = wspr.encode_w6nxp_adc_telem(b.telemetry['v_solar'],
                                                                                b.telemetry['v_in'],
                                                                                b.telemetry['l_front'],
                                                                                b.telemetry['l_back'],
                                                                                b.telemetry['temp_c'])
                callsign = b.w6nxp_telem_prefix + telem_call
                print(f"ADC + temp telemetry: {callsign} {grid_square} {wspr_pwr}\n")
            
            time.sleep(0.01)
    elif mode == "calibration":
        print("Transmitting tone, calibrate to 14.097.100 MHz")
        b.configure_clockgen()
        b.clockgen.enable_output(b.output, True)
        b.clockgen.transmit_wspr_tone(b.output, b.band, 100, correction=b.tx_correction)
        while True:
            pass
    elif mode == "gps_stream":
        while True:
            print(b.gps.get_GPRMC_data())
            print(b.gps.get_GPGGA_data())
            print()
    elif mode == "state_machine":
        while True:
            b.tick()
            time.sleep(0.01)

if __name__ == "__main__":
    main()