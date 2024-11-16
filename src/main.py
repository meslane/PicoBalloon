import balloon
import time

balloon = balloon.Balloon("config.json")
while True:
    balloon.tick()
    time.sleep(0.01)