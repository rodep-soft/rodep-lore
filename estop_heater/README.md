# 自動ヒーターOffスクリプト

## Why?

1. ヒーターの切り忘れが怖い
2. 21:50分に合図を出して片付けを始めるため

## 構成

Laptop <--(USBTypeC)--> Arduino <--(Wire)--> Servo (PUSH!)----> ヒーター電源

## Systemd Serviceとして登録

estop-heater.serviceを/etc/systemd/system/estop-heater.serviceに置く
  
このリポジトリを/home/rodep/rodep-loreと配置しておく必要がある


```bash
$ sudo systemctl daemon-reload
$ sudo systemctl start estop-heater
````
