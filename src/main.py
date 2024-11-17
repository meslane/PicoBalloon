import balloon
import time

def main():
    b = balloon.Balloon("config.json")

    hw_status = b.selftest()
    if hw_status['Si5351'] == "FAIL" or hw_status['LIV3R'] == "FAIL":
        print("Self-test failed on critical component! Holding before the state machine...")
        while True:
            pass
    elif hw_status['MS5607'] == "FAIL":
        print("Self-test failed on non-critical component. Starting state machine...")
    else:
        print("Self-test passed! Starting state machine...")

    while True:
        b.tick()
        time.sleep(0.01)

if __name__ == "__main__":
    main()