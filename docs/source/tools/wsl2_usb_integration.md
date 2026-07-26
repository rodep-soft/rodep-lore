# WSL2 と USB 連携：ネイティブLinuxとの溝を埋める泥臭い運用術

このドキュメントでは、開発環境としての WSL2 (Windows Subsystem for Linux 2) における、USBデバイスのパススルー、udevルールの設定、および特有のネットワークトラブルについて、過去の技術議論から抽出した知見を詳解します。

## 1. WSL2とネイティブLinuxの決定的な違い

WSL2は、Hyper-Vアーキテクチャ上で軽量なLinuxカーネル（Microsoft提供）を動かしている仕組みです。そのため、「完全なLinux環境」と誤認して作業を進めると、ハードウェアアクセスやネットワークの壁に直面します。

> [!WARNING]
> 通常のネイティブLinuxであれば `modprobe vhci-hcd` などで簡単にUSBデバイスをバインドできる場面でも、WSL2ではWindowsホスト側とのやり取りが発生するため、そのままでは機能しません。

## 2. USBデバイスのパススルー (usbipd-win)

WSL2でマイコン（STM32など）やUSBカメラを認識させるための標準的なソリューションが `usbipd-win` です。

### 2.1 基本的なワークフロー
1. **Windows側でのバインド**:
   コマンドプロンプトやPowerShellから、対象のUSBデバイス（Vendor ID / Product ID）をWSL向けにバインドします。
2. **WSL側でのアタッチ**:
   バインドされたデバイスをWSL側にアタッチします。

**泥臭い自動化の知見**:
毎回PowerShellを開いてアタッチするのは非常に面倒です。
解決策として、`$PROFILE` (`Microsoft.PowerShell_profile.ps1`) にWSLへのアタッチコマンドをエイリアスとして仕込み、WSL2側から `powershell.exe` を一回叩くだけでデバイスが認識されるようにする運用が効果的です。

### 2.2 Udev ルールの設定
WSL2にパススルーされたデバイスに対して、権限（Permission denied）エラーを防ぐために `udev` ルールを記述します。

```udev
# 例: ST-Link/V2-1 (STM32 nucleo f446re board)
# `lsusb -v` でidVendorとidProductを確認
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="374b", MODE="0666"

# 例: AsusTek AURA LED Controller
SUBSYSTEM=="usb", ACTION=="add", ATTRS{idVendor}=="0b05", ATTRS{idProduct}=="19af", MODE="0666"
```
ルールを追加した後は、必ず `udevadm control --reload-rules && udevadm trigger` を実行してルールを反映させます。

## 3. WSL2 ネットワークと SSH のトラブルシューティング

WSL2を使用していると、「外部へのPingが通らない」「SSH接続ができない（Timeoutする）」といったネットワークトラブルが頻発します。

### 3.1 DNSと外部アクセスの問題
WSL2はWindowsホストの仮想スイッチを経由して通信を行うため、Windows側のファイアウォールやVPNソフトウェア（特に企業用VPN）が干渉し、パケットがドロップされるケースが多々あります。
- `resolv.conf` の自動生成を無効化し、`8.8.8.8` などを明示的に指定することで解決する場合がある。
- `wsl_cannot_ping_outside` などの事象は、WSL2の仮想ネットワークアダプタのNAT設定に起因することが多い。

### 3.2 X11 / Wayland GUIの扱い
WSLgの導入により、GUIアプリケーションも比較的スムーズに動くようになりましたが、`/run/user/1000/` 以下のソケット群（WaylandやPulseAudio関連）のパーミッションやマウント状況によっては、RvizなどのROSツールが起動しないことがあります。
GUIが重いと感じた場合は、Xwaylandラッパーのオーバーヘッドを疑い、必要に応じてネイティブのXサーバー（VcXsrvなど）への切り替えも検討されます。

## 4. なぜWSL2を使うのか？ (ネイティブとの比較)

過去の議論において、WSL2環境下での `Docker Compose` ビルド（コンテナ再生成）に13〜14秒程度かかることが指摘されています。これはネイティブLinux環境（約10秒）に比べて明確なオーバーヘッドです。

- **結論**: 「普段使い（Daily driver）としてのWindowsの利便性」と「Linux開発環境」を両立させたい層にとってはWSL2は有用ですが、USBハードウェア制御や極限のパフォーマンス（コンパイル速度、GUIの軽量さ）を求めるロボティクス・組み込み開発においては、UbuntuやArch Linuxのネイティブインストール、あるいは Pixi や Nix といった代替ツールの使用が最終的な最適解となる傾向にあります。
