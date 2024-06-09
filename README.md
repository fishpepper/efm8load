# efm8load.py

A python-only implementation of the efm8 bootloader protocol.  
Check out http://fishpepper.de/2016/10/15/efm8-bootloader-flash-tool-efm8load-py/ for more info.


## Status
| Microcontroller Unit (MCU) | Identify | Read | Write |
| - | - | - | - |
| EFM8BB10F8G  | 🟢 | 🟢 | 🟢 |
| EFM8BB52F32G | 🟢 | 🟢 | 🟡 |

🟢 = Working,
🟡 = Not tested,
🔴 = Not working


## Info
- Connect the MCU to the rs232:
    * MCU RXD to TXD
    * MCU TXD to RXD
    * MCU 3v3 to 3v3 **or** MCU 5v to 5v **(⚠️Do not mix 5v with 3v3! Check the datasheet for V<sub>VDD</sub> and `Voltage on VDD supply pin`⚠️)**
    * MCU GND to GND
    * MCU C2D to GND
- Empty targets boot right into the bootloader (flash[0] = 0xFF -> bootloader)


## Requirements
- python3 + pip
- USB to UART Bridge Controller (e.g. CP2102)
- CP210x USB to UART Bridge VCP Drivers
- C2D Pin **must** be pulled low (connected to GND) during powerup to enter the bootload mode (Review section `5.3.1 Entering Bootload Mode` [documents/an945-efm8-factory-bootloader-user-guide.pdf](documents/an945-efm8-factory-bootloader-user-guide.pdf) for the right Pin numbers)


## Setup
```bash
# Install the necessary packages
pip install -r requirements.txt
```

## Usage
```bash
# Identify the chip
python efm8load.py -p <COM_PORT> -i

# Dump the flash memory to file
python efm8load.py -p <COM_PORT> -r dumped_flash.hex

# ⚠️Upload/Write file to flash memory⚠️
python efm8load.py -p <COM_PORT> -w dumped_flash.hex
```


## TODO
- Add a protection to stop users from overwriting the bootloader area
- Information about decompiling the dumped flash memory
