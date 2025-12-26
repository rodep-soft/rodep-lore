import serial

# Serial接続
ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)

# send command
ser.write(1)



# 閉じる
ser.close()
