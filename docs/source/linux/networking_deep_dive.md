# Networking Deep Dive

## Linuxネットワークスタックの深層：systemd-networkdとiwdによるモダンな無線LAN管理

Linuxにおけるネットワーク管理は、古くは `ifconfig` や `wpa_supplicant` から始まり、現在では `NetworkManager` がデファクトスタンダードとして広く普及しています。しかし、組み込み機器やサーバー、あるいはカスタマイズを好むArch Linuxユーザーなどの間では、より軽量でシステムと密結合した `systemd-networkd` と `iwd` (iNet Wireless Daemon) の組み合わせが注目されています。

本稿では、これらのコンポーネントのアーキテクチャから、具体的な設定例、そして泥臭いトラブルシューティングの手順までを徹底的に解説します。

### 1. iwdとwpa_supplicantのアーキテクチャ比較

長らくLinuxの無線LAN認証を支えてきた `wpa_supplicant` ですが、近年ではIntelが主導して開発した `iwd` への移行が進んでいます。

`wpa_supplicant` は巨大なコードベースを持ち、レガシーなプロトコルを含めほぼ全ての仕様を網羅しています。しかし、その分フットプリントが大きく、D-Bus APIの設計もやや古いものとなっています。
一方 `iwd` は、Linuxカーネルの機能を最大限に活用（例：カーネルの暗号化APIの利用）し、モダンなD-Busインターフェースを提供することで、高速なローミングとリソース消費の削減を実現しています。

#### 1.1. NetworkManagerバックエンドとしてのiwd

NetworkManagerはデフォルトで `wpa_supplicant` を使用しますが、バックエンドを `iwd` に切り替えることが可能です。これにより、フロントエンドの利便性（nmcliやGUIツール）を保ちつつ、バックエンドの高速化を図ることができます。

```ini
## /etc/NetworkManager/conf.d/iwd.conf
[device]
wifi.backend=iwd
```

設定後、サービスを再起動することでバックエンドが切り替わります。

```bash
sudo systemctl restart NetworkManager
```

### 2. systemd-networkdとiwdの統合

NetworkManagerを使用せず、純粋な systemd エコシステムでネットワークを構築する場合、`systemd-networkd` と `iwd` を組み合わせます。この構成は非常に軽量であり、不要な抽象化レイヤーを排除できるため、トラブル発生時の切り分けが容易になるという利点があります。

#### 2.1. iwdのスタンドアロン設定

まず、iwd 自体にネットワーク設定を管理させるための基本設定を行います。

```ini
## /etc/iwd/main.conf
[General]
EnableNetworkConfiguration=true

[Network]
NameResolvingService=systemd
```

この設定により、iwd が DHCP クライアント機能や DNS 解決機能（systemd-resolvedへの連携）を有効化します。

#### 2.2. Wi-Fiネットワークへの接続

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
## /var/lib/iwd/MySSID.psk
[Security]
Passphrase=YourSecretPassword
```

#### 2.3. systemd-networkdによるインターフェース管理

有線LAN（eth0など）と併用する場合や、より複雑なルーティングが必要な場合は、`systemd-networkd` でインターフェースを管理します。

```ini
## /etc/systemd/network/20-wireless.network
[Match]
Name=wlan0

[Network]
DHCP=yes
IgnoreCarrierLoss=3s

[DHCPv4]
RouteMetric=20
```

`RouteMetric` を設定することで、有線LAN（例: Metric=10）が接続された際に、自動的に有線LANが優先されるように構成できます。

### 3. 泥臭いトラブルシューティング事例

ネットワーク周りのトラブルは、カーネルモジュール、デーモン、設定ファイルの各層で発生する可能性があります。ここでは実際のログに基づいたトラブルシューティング事例を紹介します。

#### 3.1. スリープ復帰後にWi-Fiが見つからない

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
## /etc/modprobe.d/iwlwifi.conf
options iwlwifi power_save=0
options iwlmvm power_scheme=1
```

設定後、モジュールを再読み込みします。

```bash
sudo rmmod iwlmvm iwlwifi
sudo modprobe iwlwifi
sudo systemctl restart iwd
```

#### 3.2. WPA3エンタープライズ環境での認証失敗

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
## /var/lib/iwd/EnterpriseSSID.8021x
[Security]
EAP-Method=PEAP
EAP-Identity=user@domain.com
EAP-PEAP-Phase2-Method=MSCHAPV2
EAP-PEAP-Phase2-Identity=user@domain.com
EAP-PEAP-Phase2-Password=password
CACert=/etc/ssl/certs/ca-certificates.crt
```

### 4. 総括

`systemd-networkd` と `iwd` の組み合わせは、初期設定のハードルこそ高いものの、一度構築してしまえば非常に堅牢かつ軽量なネットワーク環境を提供します。
ブラックボックス化されがちなネットワークスタックを透明化し、構成要素を理解することは、高度なインフラストラクチャを運用する上で不可欠な知見と言えるでしょう。


---

## ネットワークアーキテクチャとトラフィック制御

Linuxのネットワークスタックは高機能である反面、その複雑さゆえにトラブルシューティングが困難になりがちです。
名前解決のレイヤーにおいては、`systemd-resolved` の振る舞いを理解することが第一歩です。`/etc/resolv.conf` がローカルのスタブリゾルバ（127.0.0.53）を指している環境では、単純な `nslookup` だけでなく、`resolvectl query` や `resolvectl status` を使用して、システム全体のキャッシュ状態やルーティングドメインの設定を正確に把握することが解決の糸口となります。

また、パケットのルーティングやファイアウォールの設定においては、`iptables` や `nftables` を操作しますが、これらはカーネル空間の `netfilter` サブシステムのインターフェースに過ぎません。パケットが物理インターフェースに到達してから、PREROUTING、FORWARD、POSTROUTINGといったチェインを通過する一連のデータフローを理解することが、高度なルーティングやNATの設定を行う上で必須となります。特に、大量の通信を行う環境ではコネクショントラッキングのテーブルが溢れ（`nf_conntrack: table full, dropping packet`）、通信が突如として遮断される問題が発生しやすいため、`sysctl` を用いて `net.netfilter.nf_conntrack_max` を引き上げるなどの予防措置が必要です。

大容量のセンサーデータ（高解像度カメラ画像やポイントクラウドなど）を安定して伝送するためには、カーネルのネットワークバッファの最適化が効果的です。`sysctl` で `net.core.rmem_max` や `net.core.wmem_max`、`net.ipv4.tcp_window_scaling` を拡張し、必要に応じてNICのリングバッファを `ethtool -G` コマンドで引き上げることで、パケットロスの発生を最小限に抑え、劇的なスループット向上を実現できます。

---

## systemd-networkdとdhcpcdによるネットワーク管理の比較

Linux環境において、IPアドレスが正常に割り当てられない場合、場当たり的に`dhcpcd`コマンドを再実行して解決を図ることがあります。しかし、現代のUbuntuなどのディストリビューションでは、`systemd-networkd`が標準的なネットワーク管理デーモンとして稼働していることが多く、両者が競合することでシステムが不安定になる原因となります。

安定したインフラを構築するためには、`dhcpcd`の利用を控え、`systemd-networkd`にDHCP管理を一任する設計が推奨されます。設定は`/etc/systemd/network/`以下のファイルに静的に記述し、`sudo networkctl renew`などのコマンドを用いて状態の更新を行う方が、より健全で予見可能なネットワーク動作を保証します。

また、DNS解決においても`systemd-resolved`が稼働している場合、`nslookup`などのコマンドはスタブリゾルバ（例：127.0.0.53）を参照します。そのため、実際に利用されている上流のDNSサーバーを確認する際は、`resolvectl status`コマンドを使用することが正確なトラブルシューティングに繋がります。

---

## WSL2環境下でのUSBデバイスパススルーとDockerネットワークの課題

Windows Subsystem for Linux 2 (WSL2) を用いた開発環境では、ハードウェアとの連携やネットワーク周りで特有の課題が生じます。USBデバイスの認識については、`usbipd`を用いて一度バインドを行い、PowerShellのプロファイルにWSLへのアタッチ処理を記述することで、WSL2側でPowerShellコマンドを一度実行するだけでデバイスを認識させる自動化が可能です。

グラフィックに関しては、WSL2はXwaylandラッパーを経由して描画を行っています。コンテナ技術の利用においては、WSL2経由でのDocker Compose実行は、ネイティブLinux環境と比較してコンテナの再構築にオーバーヘッドが発生する傾向があります。

ネットワーク面では、WSL2の仮想スイッチやルーティング設定に起因して外部へのPingが通らない、あるいはSSH接続がタイムアウトするといった事象が頻発します。また、USBデバイスをコンテナにマウントする際のドライバ読み込みも、WSL2特有のカーネル設定やバージョンに依存するため、適切なカーネルコンフィギュレーションとネットワーク設定の調整が不可欠です。

---
