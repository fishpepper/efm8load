efm8load.py
===

A python-only implementation of the efm8 bootloader protocol

see http://fishpepper.de/2016/10/15/efm8-bootloader-flash-tool-efm8load-py/ for more info

Status: 
- tested on EFM8BB10F8G: identify, write, verify and read are working

Usage:
- connect rs232 (3.3V level!) to the RX and TX pins of your MCU
- empty targets boot right into the bootloader (flash[0] = 0xFF -> bootloader)
- flashed targets need the C2D pin pulled low during powerup to enter bootloader mode

TODO:
add a protection to stop users from overwriting the bootloader area
