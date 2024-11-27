import balloon
import time
import machine
import sys
import select

def main():
    b = balloon.Balloon("config.json")

    hw_status = b.selftest()
    
    mode = "selftest"
    
    if hw_status['Si5351'] == "FAIL" or hw_status['LIV3R'] == "FAIL":
        print("Self-test failed on critical component! Holding for 10s before resetting...")
        mode = "reset_sleep"
    elif hw_status['MS5607'] == "FAIL":
        print("Self-test failed on non-critical component. Starting state machine...")
    else:
        print("Self-test passed! Starting state machine in 10 seconds")
        print("Press 't' + ENTER to enter raw telemetry mode")
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
                elif char_in == '\n':
                    mode = "state_machine"
                    break
                
            if (time.time() - t_start) >= 10:
                mode = "state_machine"
                break

    if mode == "reset_sleep":
        time.sleep(10)
        machine.reset()
    elif mode == "telemetry":
        while True:
            b.print_telemetry()
            time.sleep(0.01)
    elif mode == "state_machine":
        while True:
            b.tick()
            time.sleep(0.01)

if __name__ == "__main__":
    main()