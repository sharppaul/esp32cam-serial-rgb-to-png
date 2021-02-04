from datetime import datetime
from serial import *
from time import sleep
import numpy as np
from PIL import Image
import sys

import serial.tools.list_ports as port_list

ports = list(port_list.comports())

for p in ports:
    print(p)

COMMAND = "gaus"
IMAGE_BYTES = 57600
height = 120
width = 160
TIMEOUT_AFTER_SECONDS = 1.5

while True:
    if COMMAND == "gaus":
        COMMAND = "mem"
    else:
        COMMAND = "gaus"

    ESPCAM = Serial()
    ESPCAM.port = "COM3"
    ESPCAM.baudrate = 115200
    ESPCAM.parity = PARITY_NONE
    ESPCAM.stopbits = STOPBITS_ONE
    ESPCAM.bytesize = EIGHTBITS
    ESPCAM.timeout = 1

    start = datetime.now()

    print("Serial: ", ESPCAM.name)

    if not ESPCAM.isOpen():
        ESPCAM.open()

    sleep(3)

    ESPCAM.read(ESPCAM.in_waiting)

    sleep(3)

    print('Request {};'.format(COMMAND))

    ESPCAM.write('{};'.format(COMMAND).encode('ascii'))

    startwait = datetime.now()
    waitbytes = bytearray(b'')
    timeout = False

    while not timeout:
        inbytes = ESPCAM.read(ESPCAM.in_waiting)
        for b in inbytes:
            waitbytes.append(b)
        
        if b'Prepare File capture' in waitbytes:
            print("Prepare File capture")
            break

        elif b'Camera init failed' in waitbytes:
            timeout = True
            print("Camera init failed")
            break

        elif b'Camera probe failed' in waitbytes:
            timeout = True
            print("Camera probe failed")
            break

        elif b'Failed to get the frame on time!' in waitbytes:
            timeout = True
            print("Failed to get the frame on time!")
            break

        elif b'Timeout waiting for VSYNC' in inbytes:
            timeout = True
            print('Timeout waiting for VSYNC')

        else:
            timedelta = datetime.now() - startwait
            if timedelta.total_seconds() > TIMEOUT_AFTER_SECONDS * 4:
                timeout = True
                print(waitbytes)
                print('Timeout')
                continue

    if timeout:
        ESPCAM.write(b'reset;')
        ESPCAM.close()
        sleep(5)
        continue

    sleep(3)
    ESPCAM.read(ESPCAM.in_waiting)
    sleep(3)

    print("Start reading")

    rgbytes = bytearray(b'')

    timeouttimer = datetime.now()
    timeout = False
    reason = 'Timeout'
    running = True
    while running:
        # read data from serial port
        if ESPCAM.in_waiting > 0:
            inbytes = ESPCAM.read(ESPCAM.in_waiting)
            for b in inbytes:
                rgbytes.append(b)
           
            print("\r{}%".format(round(len(rgbytes) / IMAGE_BYTES * 100)), end="")
            
            timeouttimer = datetime.now()

        if len(rgbytes) >= IMAGE_BYTES:
            running = False

        timedelta = datetime.now() - timeouttimer
        if timedelta.total_seconds() > TIMEOUT_AFTER_SECONDS:
            timeout = True
            running = False

    print()

    ESPCAM.write(b'reset;')
    ESPCAM.close()

    if timeout:
        print(reason)
        if len(rgbytes) > 0:
            print(rgbytes)
        sleep(10)
        continue

    dateTimeObj = str(datetime.now()).replace(" ", "_").replace(':', '')
    fname = './rgb24/{}_{}.rgb24'.format(COMMAND, dateTimeObj)

    f = open(fname, 'wb')
    f.write(rgbytes)
    f.close()

    array = np.zeros([height, width, 3], dtype=np.uint8)
    finish = False
    try:
        for y in range(height):
            for x in range(width):
                i = ((y * width) + x) * 3
                array[y, x] = [
                    rgbytes[i+2],  # B
                    rgbytes[i+1],  # G
                    rgbytes[i]  # R
                ]

        finish = True
    except IndexError:
        print("IndexError: Out of range")
        print(len(rgbytes))

    if finish:
        image = Image.fromarray(array, "RGB")
        fname = './png/{}_{}.png'.format(COMMAND, dateTimeObj)
        image.save(fname)

        print("Saved as {}".format(fname))

    sleep(3)
