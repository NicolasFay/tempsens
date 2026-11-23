import smbus2

class TMP102:
    def __init__(self, bus_number=1, address=0x48):
        self._bus = smbus2.SMBus(bus_number)
        self._address = address

    def read_f(self) -> float:
        data = self._bus.read_i2c_block_data(self._address, 0x00, 2)
        raw = (data[0] << 4) | (data[1] >> 4)
        if raw > 2047:
            raw -= 4096
        return raw * 0.0625 * 1.8 + 32