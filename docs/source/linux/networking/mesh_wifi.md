# Mesh Networkの構築

## 背景

Wifiの電波が不安定な環境での安定化、高速化を計る試み.

原理としては、Wifiの電波を拾い何らかの中継機能を用いて独自のNetworkに流す.

## 注意

何もわからずにコマンドを叩くと後々非常に面倒事を引き起こす可能性があるため、
基本的なネットワークの知識とコマンドは必ず頭にいれておくこと.

また、規約上の問題がある可能性があるため自己責任で.

この記事を書いている時点ではLANでapprox.90Mbps程度の速度で流せてはいるので実用的ではあると思う.

## Routerは使えるのか

Enterprise認証でなければ使える. 九工大Wifi(KIT-IA/IB)はPEAP認証であるため、Routerの中継機能との両立が不可能.

そこでLinuxを設定し両立させることが目標.以下Linux(Ubuntu24.04)を想定. Windowsはおすすめしない.

## Implementation

### Gnome Share(NetworkManager)を使う方法

この方法であれば後続の設定はいらない.

1. NetworkManagerでWifiに接続(以下KIT-IA/IB接続設定例)
  - WPA2-Enterprise
  - PEAP(Protected EAP)
  - No CA certificate
  - Identity -> 九工大のID, xxxxYYYYみたいなやつ
  - Password -> 九工大パスワード

2. 共有

以下の通りに操作

GnomeControlCenter(Settings)
->Network
->Wired
->IPv4
->Shared_to_other_computers
->Apply

NetworkManagerが勝手にDHCPやら何からやってくれる.

### Manual Setup (上級者向け)

制御できないなら手を出さないこと.

#### Wifi接続

前述の`NetworkManager`を使っても良いが、`iwd`(wpa_supplicantの後継みたいなやつ)を推奨.

#### IP Forwarding

通常、PCは自分宛てのデータしか受け取らないため、IPv4のパケット転送を有効化しなければならない.

この機能をONにすることで、Routerとして振る舞うようになる.これは心臓部であるため絶対にやること.

```bash
# 0 -> OFF 1 -> ON
# IPv4転送, 中継許可

# これは一時的な有効化
$ sudo sysctl -w net.ipv4.ip_forward=1

# 永続化
$ echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
```
#### IP Addrの手動割当

ethxを独自NetworkのGatewayにするために固定IPを振る必要がある.

```bash
# インターフェース名は各自変更すること
# 以下はあくまで例なのでIPは10.xxでなくても良い. 自由
$ sudo ip addr 10.42.0.1/24 dev eth0
$ sudo ip link set eth0 up
```

#### NAT/Masquerade

LAN内のプライベートIPを外のWifiのIPに変換する必要がある.要するにnat.

`nftables`が現在は推奨.どっちでもよい.

`iptables`

```bash
# インターフェース名は各自変更すること
# wlan0 -> Wifi
# eth0 -> Ethernet
# $ ip aで確認可能

# NAT
$ sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE

# 行きLAN -> WAN
$ sudo iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT
# 戻りWAN -> LAN
$ sudo iptables -A FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT 
```
`nftables`

```bash
# nftablesでNATテーブルを作成し、マスカレードを有効化
sudo nft add table ip nat
sudo nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }
sudo nft add rule ip nat postrouting oifname "wlan0" masquerade
```

### DHCP Server

マストではないが、いちいち手動でIPを振るのはとても面倒なので、DHCPを導入する.

ここでは軽量な`dnsmasq`を紹介する.

設定ファイル`/etc/dnsmasq.conf`を作成.内容は以下.

```txt
interface=eth0

# 10.42.0.xの範囲でIPを貸し出す.DHCP Pool(50-150)
# 2-49はreservedとして固定用に一応開けておく
# 接続台数は最大101台
dhcp-range=10.42.0.50,10.42.0.150,12h

#server=8.8.8.8 # 上流からリレーするならいらない

# systemd-resolvedとポート53で競合しないように
bind-interfaces

# NetworkManagerの場合
# resolv-file=/var/run/NetworkManager/resolv.conf

# systemd-resolvedの場合
resolv-file=/run/systemd/resolve/resolv.conf
```

サーバ起動

```bash
$ sudo systemctl restart dnsmasq
```

### メモ

netplanを使うと良いかも.それについては今後かきたい

iwdについても別で記事を書きたい
