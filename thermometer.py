import smbus2
import time

bus = smbus2.SMBus(1)
address = 0x48

while True:
    data = bus.read_i2c_block_data(address, 0x00, 2)
    # Combine 12-bit data
    temp_raw = (data[0] << 4) | (data[1] >> 4)
    # Handle negative temperatures (two's complement)
    if temp_raw > 2047:
        temp_raw -= 4096
    temp_c = temp_raw * 0.0625
    temp_f = (temp_c * 1.8) + 32
    print(f"Temperature: {temp_f:.2f} °F")
    time.sleep(1)
