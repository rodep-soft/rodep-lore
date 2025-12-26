import serial
import time

# Serial接続
ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
time.sleep(3)
# send command
ser.write(b'1')



# 閉じる
ser.close()
