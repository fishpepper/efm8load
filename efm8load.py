#!/usr/bin/python
import serial
import argparse
import sys
import operator
import crcmod
from crcmod.predefined import *
from intelhex import IntelHex

# if you are missing the intelhex package, you can install it by 
# pip install intelhex --user
# the same goes for the crcmod
# pip install crcmod --user
class COMMAND:
    IDENTIFY = 0x30
    SETUP    = 0x31
    ERASE    = 0x32
    WRITE    = 0x33
    VERIFY   = 0x34

class RESPONSE:
    ACK         = 0x40
    RANGE_ERROR = 0x41
    BAD_ID      = 0x42
    CRC_ERROR   = 0x43
    TO_STR = { ACK: "ACK", RANGE_ERROR : "RANGE_ERROR", BAD_ID : "BAD_ID", CRC_ERROR : "CRC_ERROR" }


class EFM8Loader:
    """A python implementation of the EFM8 bootloader protocol"""
    def __init__(self, port, baud, debug = False):
        self.debug           = debug
        self.serial          = serial.Serial()
        self.serial.port     = port
        self.serial.baudrate = baud
        self.serial.timeout  = 1
        self.flash_page_size = 512
        self.open_port()

    def __del__(self):
        self.close_port()

    def open_port(self):
        print("> opening port '%s' (%d baud)" % (self.serial.port, self.serial.baudrate))
        try:
            self.serial.open()
        except:
            sys.exit("ERROR: failed to open serial port '%s'!" % (self.serial.port))

    def close_port(self):
        try:
            self.serial.close()
        except serial.SerialException:
            sys.exit("ERROR: failed to close serial port")

    def send_autobaud_training(self):
        if (self.debug): print("> sending training char 0xFF")
        for i in range(1):
            self.send_byte(0xff)

    def send_byte(self, b):
        try:
            self.serial.write(chr(b)) 
        except serial.SerialException:
            sys.exit("ERROR: failed to close serial port") 

    def identify_chip(self):
        #send autobaud training
        self.send_autobaud_training()
        #enable flash access
        self.enable_flash_access()
        #scan for all known ids
        device_ids = { 
                     0x16 : ["EFM8SB2", { } ],
                     0x30 : ["EFM8BB1", { 
                                         0x01 : "EFM8BB10F8G_QSOP24",                          
                                         0x02 : "EFM8BB10F8G_QFN20",
                                         0x03 : "EFM8BB10F8G_SOIC16",
                                         0x05 : "EFM8BB10F4G_QFN20",
                                         0x08 : "EFM8BB10F2G_QFN20"
                                         }],
                      0x32 : ["EFM8BB2", {       
                                         0x01 : "EFM8BB22F16G_QFN28",
                                         0x02 : "EFM8BB21F16G_QSOP24",
                                         0x03 : "EFM8BB21F16G_QFN20"
                                         }]
                     }
        #append all other possible device ids to this list:
        if (0):
            for x in range(0xFF):
                if (x not in device_ids):
                    #not yet, add to list
                    device_ids[x] = ["UNKNOWN_ID_0x%02X" % (x), {} ]

        #we will now iterate through all items, sort the dict 
        #in order to process the known ids first
        sorted_device_ids = sorted(device_ids.items(), key=operator.itemgetter(1))
	for device_id, device in sorted_device_ids:
            device_name = device[0]
            device_derivative_ids = device[1]
            print("> checking for device %s" % (device_name))
            for variant_id in range (25):
                #test all possible variant ids (fixme: what is a valid maximum here?)
                if (variant_id not in device_derivative_ids):
                     variant_name = "UNKNOWN_VARIANT_ID_0x%02X" % (variant_id)
                else:
                     variant_name = device_derivative_ids[variant_id]

                #if (self.debug): print("> checking for %s (id 0x%02X) - variant %s \t(0x%02X)..." % (device_name, device_id, variant_name, variant_id))
                if (self.check_id(device_id, variant_id)):
                    print("> success, detected an %s cpu (%s)" % (device_name, variant_name))
                    return variant_name
        sys.exit("> ERROR: could not find any device")

    def send(self, cmd, data):
        length = len(data)

        #check length
        if (length < 2) or (length > 130):
            sys.exit("> ERROR: invalid data length! allowed 2...130, got %d" % (length))

        try:
            if (self.debug): 
                data_str = "".join('0x{:02x} '.format(x) for x in data[:16])
                if (length > 16): data_str = data_str + "..."
                print("> sending $ len=%d cmd=0x%02X data={ %s}" % (length, cmd, data_str))
            self.serial.write('$')
            self.serial.write(chr(length + 1))
            self.serial.write(chr(cmd))
            self.serial.write(bytearray(data))

            #read back reply
            res_bytes = self.serial.read(1)
            #res_bytes = b"\x40"
            if (len(res_bytes) != 1):
                sys.exit("> ERROR: serial read timed out")
                return 0   
            else:         
                res = ord(res_bytes[0])
                if(self.debug): print("> reply 0x%02X" % (res))
		return res 

        except serial.SerialException:
            sys.exit("ERROR: failed to send data")


    def check_id(self, device_id, derivative_id):
        #verify that the given id matches the target
        return self.send(COMMAND.IDENTIFY, [device_id, derivative_id]) == RESPONSE.ACK
    
    def enable_flash_access(self):
        res = self.send(COMMAND.SETUP, [0xA5, 0xF1, 0x00])
        if (res != RESPONSE.ACK):
            sys.exit("> ERROR enabling flash access, error code 0x%02X (%s)" % (res, RESPONSE.TO_STR(res)))

    def erase_page(self, page):
        start = page * self.flash_page_size
        end   = start + self.flash_page_size-1
        print("> will erase page %d (0x%04X-0x%04X)" % (page, start, end))

    def write(self, address, data):
        if (len(data) > 128):
            sys.exit("ERROR: invalid chunksize, maximum allowed write is 128 bytes (%d)" % (len(data)))
        #print some of the data as debug info
        if (len(data) > 8):
            data_excerpt = "".join('0x{:02x} '.format(x) for x in data[:4]) + \
                           "... " + \
                           "".join('0x{:02x} '.format(x) for x in data[-4:])
        else:
            data_excerpt = "".join('0x{:02x} '.format(x) for x in data)
                
        print("> write at 0x%04X (%3d): %s" % (address, len(data), data_excerpt))
   
        #send request
        address_hi = (address >> 8) & 0xFF
        address_lo = address & 0xFF
        res = self.send(COMMAND.WRITE, [address_hi, address_lo] + data)
        if not (res == RESPONSE.ACK):
            sys.exit("ERROR: write failed at address 0x%04X (response = %s)" % (address, RESPONSE.TO_STR(res)))
 
    def verify(self, address, data):
        length = len(data)
        crc16 = crcmod.predefined.mkCrcFun('xmodem')(str(bytearray(data)))
        
        if (self.debug): print("> verify address 0x%04X (len=%d, crc16=0x%04X)" % (address, length, crc16))
        start_hi = (address >> 8) & 0xFF
        start_lo = address & 0xFF
        end      = address + length
        end_hi   = (end >> 8) & 0xFF
        end_lo   = end & 0xFF
        crc_hi   = (crc16 >> 8) & 0xFF
        crc_lo   = crc16 & 0xFF
        res = self.send(COMMAND.VERIFY, [start_hi, start_lo] + [end_hi, end_lo] + [crc_hi, crc_lo])
        return res

    def download(self, filename):
        print("> dumping flash content to '%s'" % filename)
        print("> please note that this will take long")
        self.debug = False

        #send autobaud training character
        self.send_autobaud_training()

        #enable flash access
        self.enable_flash_access()

        #the bootloader protocol does not allow reading flash
        #however it allows to verify written bytes
        #we will exploit this feature to dump the flash contents
        #for now assume 8kb flash
        flash_size = 8 * 1024
        ih = IntelHex()
        for address in range(flash_size):
            #test one byte by byte
            #first check 0x00
            byte = 0
            if (self.verify(address, [byte])):
                ih[address] = byte
            else:
                #now start with 0xFF (empty flash)
                for byte in range(0xFF, -1, -1):
                    if (self.verify(address, [byte]) == RESPONSE.ACK):
                        #success, the flash content on this address euals <byte>
                        ih[address] = byte
                        break
            print("> flash[0x%04X] = 0x%02X" % (address, byte))

        #done, all flash contents have been read, now store this to the file
        ih.write_hex_file(filename)
        

    def upload(self, filename):
        print("> uploading file '%s'" % (filename))
        
        #read hex file
        ih = IntelHex()
        ih.loadhex(filename)

        #send autobaud training character
        self.send_autobaud_training()
     
        #enable flash access
        self.enable_flash_access()

	#erase pages where we are going to write
        self.erase_pages_ih(ih)

        #write all data bytes
        self.write_pages_ih(ih)

        #verify data
        self.verify_pages_ih(ih)

    def erase_pages_ih(self, ih):
        """ erase all pages that are occupied """
        last_address = ih.addresses()[-1]
        last_page = int(last_address / self.flash_page_size)
        for page in range(last_page+1):
            start = page * self.flash_page_size
            end   = start +  self.flash_page_size-1
            page_used = False
            for x in ih.addresses():
                if x >= start and x <= end:
                    page_used = True
                    break
            if (page_used): 
                self.erase_page(page)

    def write_pages_ih(self, ih):   
        """ write all segments from this ihex to flash"""
        for start,end in ih.segments():
            #fetch data
            data = []
            for x in range(start,end):
                data.append(ih[x])
            #write in 128byte blobs
            data_pos = 0
            while ((data_pos + start) < end):
                length = min(128, end - (data_pos + start))
                self.write(start + data_pos, data[data_pos:data_pos+length])
                data_pos = data_pos + length

    def verify_pages_ih(self, ih):
        """ verify written data """
        last_address = ih.addresses()[-1]

        #first: check the whole blob at once:
        data = []
        for x in range(last_address + 1):
            data.append(ih[x])
        if (self.verify(0, data) == RESPONSE.ACK):
            #verify succeeded.
            print("> verify sucessfull")
            return 1
        else:
            #there was a verify mismatch somewhere,
            #do a pagewise compare to find the position of
            #the mismatch
            data_pos = 0
            while(data_pos < last_address):
                #build chunks of up to 128 byte
                length       =  min(128, (last_address-data_pos))
                data_pos_end = data_pos + length
                #fetch chunk from ih
                data=[]
                for x in range(length):  
                    data.append(ih[data_pos + x])
                #send verify request
                if (self.verify(data_pos, data) == RESPONSE.ACK):
                    print("> ERROR verify mismatch in between 0x%04X-0x%04X" % (data_pos, data_pos+length))
                    return 0
                #prepare for next chunk
                data_pos = data_pos_end + 1
        return 1

if __name__ == "__main__":
    argp = argparse.ArgumentParser(description='efm8load - a plain python implementation for the EFM8 usart bootloader protocol')

    group = argp.add_mutually_exclusive_group()
    group.add_argument("-w", "--write", metavar="filename", help="upload the given hex file to the flash memory")
    group.add_argument("-r", "--read", metavar="filename", help="download the flash memory contents to the given filename") #action="store_true", nargs=1)
    group.add_argument("-i", "--identify", help="identify the chip", action="store_true") #action="store_true", nargs=0)

    #argp.add_argument('filename', help='firmware file to upload to the mcu')
    argp.add_argument('-b', '--baudrate', type=int, default=115200, help='baudrate (default is 115200 baud)')
    argp.add_argument('-p', '--port', default="/dev/ttyUSB0", help='port (default is /dev/ttyUSB0)')
    args = argp.parse_args()

    print("########################################")
    print("# efm8load.py - (c) 2016 fishpepper.de #")
    print("########################################")
    print("")

    efm8loader = EFM8Loader(args.port, args.baudrate, debug=True)

    if (args.identify):
        efm8loader.identify_chip()
    elif (args.write):
        efm8loader.upload(args.write)
    elif (args.read):
        efm8loader.download(args.read)
    else:
        argp.print_help()

    print 
    sys.exit(1)
