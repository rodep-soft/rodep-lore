# Linuxネットワークスタックの深層：systemd-networkdとiwdによるモダンな無線LAN管理

Linuxにおけるネットワーク管理は、古くは `ifconfig` や `wpa_supplicant` から始まり、現在では `NetworkManager` がデファクトスタンダードとして広く普及しています。しかし、組み込み機器やサーバー、あるいはカスタマイズを好むArch Linuxユーザーなどの間では、より軽量でシステムと密結合した `systemd-networkd` と `iwd` (iNet Wireless Daemon) の組み合わせが注目されています。

本稿では、これらのコンポーネントのアーキテクチャから、具体的な設定例、そして泥臭いトラブルシューティングの手順までを徹底的に解説します。

## 1. iwdとwpa_supplicantのアーキテクチャ比較

長らくLinuxの無線LAN認証を支えてきた `wpa_supplicant` ですが、近年ではIntelが主導して開発した `iwd` への移行が進んでいます。

`wpa_supplicant` は巨大なコードベースを持ち、レガシーなプロトコルを含めほぼ全ての仕様を網羅しています。しかし、その分フットプリントが大きく、D-Bus APIの設計もやや古いものとなっています。
一方 `iwd` は、Linuxカーネルの機能を最大限に活用（例：カーネルの暗号化APIの利用）し、モダンなD-Busインターフェースを提供することで、高速なローミングとリソース消費の削減を実現しています。

### 1.1. NetworkManagerバックエンドとしてのiwd

NetworkManagerはデフォルトで `wpa_supplicant` を使用しますが、バックエンドを `iwd` に切り替えることが可能です。これにより、フロントエンドの利便性（nmcliやGUIツール）を保ちつつ、バックエンドの高速化を図ることができます。

```ini
# /etc/NetworkManager/conf.d/iwd.conf
[device]
wifi.backend=iwd
```

設定後、サービスを再起動することでバックエンドが切り替わります。

```bash
sudo systemctl restart NetworkManager
```

## 2. systemd-networkdとiwdの統合

NetworkManagerを使用せず、純粋な systemd エコシステムでネットワークを構築する場合、`systemd-networkd` と `iwd` を組み合わせます。この構成は非常に軽量であり、不要な抽象化レイヤーを排除できるため、トラブル発生時の切り分けが容易になるという利点があります。

### 2.1. iwdのスタンドアロン設定

まず、iwd 自体にネットワーク設定を管理させるための基本設定を行います。

```ini
# /etc/iwd/main.conf
[General]
EnableNetworkConfiguration=true

[Network]
NameResolvingService=systemd
```

この設定により、iwd が DHCP クライアント機能や DNS 解決機能（systemd-resolvedへの連携）を有効化します。

### 2.2. Wi-Fiネットワークへの接続

`iwctl` コマンドを使用して、対話的あるいはスクリプトからネットワークに接続します。

```bash
$ iwctl
[iwd]# device list
                                    Devices                                   
--------------------------------------------------------------------------------
  Name                Mac Address         Powered   Adapter   Mode      
--------------------------------------------------------------------------------
  wlan0               00:11:22:33:44:55   on        phy0      station   

[iwd]# station wlan0 scan
[iwd]# station wlan0 get-networks
[iwd]# station wlan0 connect "MySSID"
```

接続が成功すると、`/var/lib/iwd/` 以下にプロファイルが作成されます。

```ini
# /var/lib/iwd/MySSID.psk
[Security]
Passphrase=YourSecretPassword
```

### 2.3. systemd-networkdによるインターフェース管理

有線LAN（eth0など）と併用する場合や、より複雑なルーティングが必要な場合は、`systemd-networkd` でインターフェースを管理します。

```ini
# /etc/systemd/network/20-wireless.network
[Match]
Name=wlan0

[Network]
DHCP=yes
IgnoreCarrierLoss=3s

[DHCPv4]
RouteMetric=20
```

`RouteMetric` を設定することで、有線LAN（例: Metric=10）が接続された際に、自動的に有線LANが優先されるように構成できます。

## 3. 泥臭いトラブルシューティング事例

ネットワーク周りのトラブルは、カーネルモジュール、デーモン、設定ファイルの各層で発生する可能性があります。ここでは実際のログに基づいたトラブルシューティング事例を紹介します。

### 3.1. スリープ復帰後にWi-Fiが見つからない

**事象:** サスペンドから復帰後、`iwctl station wlan0 scan` を実行してもネットワークが一切表示されない。

**調査:**
カーネルのログ（dmesg）と systemd のジャーナルを確認します。

```bash
$ sudo dmesg | grep iwlwifi
[ 1023.456789] iwlwifi 0000:03:00.0: Microcode SW error detected. Restarting 0x2000000.
[ 1023.567890] iwlwifi 0000:03:00.0: Failed to wake NIC

$ sudo journalctl -u iwd -f
Jan 26 14:10:15 hostname iwd[543]: WARNING: src/station.c:station_roam_timeout() 
Jan 26 14:10:15 hostname iwd[543]: wlan0: Disconnect event
```

**原因と解決策:**
Intel系のWi-Fiモジュール（iwlwifi）におけるファームウェアのバグや、PCIeの省電力機能（ASPM）の不整合が原因です。
回避策として、カーネルパラメータでASPMを無効化するか、iwlwifi のオプションで省電力機能をオフにします。

```conf
# /etc/modprobe.d/iwlwifi.conf
options iwlwifi power_save=0
options iwlmvm power_scheme=1
```

設定後、モジュールを再読み込みします。

```bash
sudo rmmod iwlmvm iwlwifi
sudo modprobe iwlwifi
sudo systemctl restart iwd
```

### 3.2. WPA3エンタープライズ環境での認証失敗

**事象:** 大学や企業のネットワーク（802.1X認証）において、接続が途中で切断される。

**調査:**
iwd のデバッグログを有効にして再起動します。

```bash
sudo systemctl edit iwd.service
```

```ini
[Service]
ExecStart=
ExecStart=/usr/lib/iwd/iwd -d
```

ログを確認すると、EAP-TLS のハンドシェイク中に証明書の検証エラーが発生していることがわかります。

```bash
$ sudo journalctl -u iwd | grep EAP
Jan 26 15:20:10 hostname iwd[890]: src/eap-tls-common.c:eap_tls_check_certificate() Certificate validation failed
Jan 26 15:20:10 hostname iwd[890]: src/eap.c:eap_rx_failure() EAP failure received
```

**原因と解決策:**
プロファイルにルート証明書のパスが正しく指定されていない、あるいは証明書の有効期限が切れていることが原因です。プロファイルを修正します。

```ini
# /var/lib/iwd/EnterpriseSSID.8021x
[Security]
EAP-Method=PEAP
EAP-Identity=user@domain.com
EAP-PEAP-Phase2-Method=MSCHAPV2
EAP-PEAP-Phase2-Identity=user@domain.com
EAP-PEAP-Phase2-Password=password
CACert=/etc/ssl/certs/ca-certificates.crt
```

## 4. 総括

`systemd-networkd` と `iwd` の組み合わせは、初期設定のハードルこそ高いものの、一度構築してしまえば非常に堅牢かつ軽量なネットワーク環境を提供します。
ブラックボックス化されがちなネットワークスタックを透明化し、構成要素を理解することは、高度なインフラストラクチャを運用する上で不可欠な知見と言えるでしょう。
