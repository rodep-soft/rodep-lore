from datetime import datetime
import serial
import time

GOHOME_HOUR = 21
GOHOME_MINUTE = 50

# Serial接続
ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
time.sleep(2)

# その日中に実行されたかどうかのフラグ
done_today = False

while True:
    now = datetime.now()

    if (now.hour == GOHOME_HOUR and now.minute == GOHOME_MINUTE
        and not done_today):
        
        print("21時50分です。帰る時間です！")
        print("ヒーターをOffにします")
        
        ser.write(b'1')

        done_today = True
    
    if now.hour == 0:
        done_today = False

    # CPUに負荷をかけすぎないようにする
    time.sleep(30)

# 閉じる
ser.close()
