from datetime import datetime
import serial
import time
import zenoh

GOHOME_HOUR = 18
GOHOME_MINUTE = 56

# Serial接続
ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
time.sleep(2)

# その日中に実行されたかどうかのフラグ
done_today = False

# Zenohネットワークに接続する
z = zenoh.open()
sub = z.declare_subscriber("heater/command", callback)

def callback(sample):
    cmd = sample.payload.decode()
    print(f"コマンド: {cmd}")

    if cmd == "ACTIVATE":
        ser.write(b'1')
        print("ヒーターをOFFにします")
        print("手動で実行されました")



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
