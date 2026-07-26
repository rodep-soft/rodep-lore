# ロボティクスチーム 技術ナレッジ・知見まとめ

本ドキュメントは、チームのチャット履歴全データから抽出・精読し、チーム内で議論・共有された技術的知見、ハマりどころ、デバッグ手順、設計思想、失敗談とその解決策を漏れなくカテゴリに分類・再構成して詳細にまとめたものです。

---

## 1. Linuxのコマンド・システム運用・シェルスクリプト

### (1) ファイルシステムと Linux の本質・パーミッション
- **Inode の本質**:
  - `Inode` はデータ実体ではなくディスク上のブロックを指すポインタ構造体である。
  - **ファイルの本質は「名前や拡張子」にはない**。Linux において拡張子は単なる表示用の文字列に過ぎず、OS側の意味や実行可能性はパーミッションおよびマジックバイト等で決まる。
  - 空ディレクトリを含めた再帰的削除には `rmdir -p` が便利。
- **ディスク管理と常用 OS の「庭師」的メンテナンス**:
  - Arch Linux や Ubuntu を常用・ビルド（`yay`, `docker`, `pacman`）していると、`yay` のビルドキャッシュ（178GB に達することもある）、`docker images`、`/var/cache/pacman/pkg`、`journalctl` ログ、`~/.local`、古いカーネル（`old kernels`）、`node_modules`、`/nix/store` 等が 1TB 級の SSD をあっという間に圧迫する。
  - 定期的に `docker system df` や `pacman -Scc` 等を実行し、システム容量を掃除・管理する「庭師」的な運用手順が必要。

### (2) ログ調査・プロセスデバッグ・システム監視
- **`less` と `journalctl` の重要性**:
  - 大量ログの閲覧には `less` や `journalctl` を使用するのが Linux の標準手法。
  - Ubuntu/Debian/Arch におけるシステムサービスログはすべて `journalctl` に集約されている。問題発生時は `journalctl -u gdm.service` のようにサービス指定でログを確認することが問題切り分けの第一歩。
- **カーネル・プロセス状態の確認**:
  - デバイスやドライバ、システムの挙動確認には `/proc`（例: `/proc/<pid>/stack` でプロセスがフューテックス `futex_wait` で停止しているか等を確認）や `/sys` ディレクトリの構造を把握しておくことが重要。
  - システムコール解析には `strace` や `journalctl` を組み合わせる。
- **プロセス制御**:
  - バックグラウンド実行の基本は `nohup command &`（追加インストール不要で安定）。実業務や開発では `tmux` や `systemd` サービス化を使い分ける。
  - 暴走した ROS ノードの確実な殺し方: `pkill -9 -f ros && ros2 daemon stop` を実行することで、バックグラウンドのデーモンとノードを完全にリセットできる。

### (3) ネットワーク運用・DNS・トラブルシューティング
- **`nslookup` と `systemd-resolved` の挙動の違い**:
  - `nslookup` や `/etc/resolv.conf` は `systemd-resolved` 採用環境下ではローカルループバック（`127.0.0.53` 等の stub resolver）を指している。
  - 実際にマシンが参照しているアップストリーム DNS サーバーを正確に調べる場合は、`/etc/resolv.conf` を見るのではなく **`resolvctl status`** を実行するのが確実。
- **Linux ネットワーキングと Firewall/NAT の基礎**:
  - `iptables` や `nftables` はユーザー空間のフロントエンド（設定インターフェース）であり、Linux におけるパケットフィルタリングや NAT の本体は **`netfilter`** カーネルモジュールである。
- **ネットワークデバッグ・スクリプト**:
  - `traceroute` の ICMP/TCP パケット送信には `sudo traceroute -T <target>` のように特権が必要。
- **Tailscale / メッシュ VPN 運用時の注意点**:
  - ローカルの `/etc/hosts` に Tailscale ノードの古いホスト名が残っていると、MagicDNS や Tailscale 側IPより `/etc/hosts` が優先されて通信が接続不能になるトラブルが発生する。
  - Tailscale ノードはキーの期限切れ（expire）が発生するため、定期的な認証更新が必要。

### (4) シェルスクリプトと非互換性
- **Fish シェルの非互換性と Python への移行**:
  - Fish シェルでスクリプトを書くと Bash/Zsh 等の他環境と互換性がなくなり自動化でトラブルの原因になる。
  - 数行を超える複雑な自動化・コマンド制御スクリプトは、無理にシェルスクリプトで書かず Python の `subprocess` や `os` モジュールで書く方が保守性・移植性が高い。
- **終了ステータス（Exit Code）の解釈**:
  - Unix/Linux コマンドの終了コード `0` は「成功（エラーなし）」を意味する。プログラム上の真偽値（`True=1`, `False=0`）とは定義が真逆であるため、条件文やシェル連携時に混同しないよう注意する。

---

## 2. Gitの高度な使い方・運用フロー・開発プラクティス

### (1) コミットとブランチの運用思想
- **「コミットに完璧主義は不要」**:
  - 「実機で動く状態になるまでコミットしない」はアンチパターン。途中のコードであってもトピックブランチを切って細かくコミット＆プッシュすべき。
  - 動かないコードやビルド未完了のテストノードは、`colconignore` を配置してビルド対象から外し、GitHubに共有してチームでレビューできるようにする。
- **PR（プルリクエスト）の早期化と放置防止**:
  - PR を放置するとメインブランチとの差分が広がり、コンフリクト解決が極めて困難になる。Draft PR や Issue・Discussions を活用して透明性の高い進捗共有を行う。
- **Issue / Discussions の活用方針**:
  - バグ報告、WSL2/Docker の環境構築問題、追加タスクは Discord の雑談で済ませず、リポジトリの Issue / Discussions に残すことで、知見の検索性と追跡可能性が劇的に向上する。

### (2) 安全な履歴操作 (`git reset` vs `git stash`)
- **`git reset --hard` のリスク**:
  - 共有リポジトリやチーム開発中に `git reset --hard` を不用意に叩くと作業データ喪失のリスクが高い。
  - 退避には `git stash push` を使うか、履歴を残す `git reset --soft` を検討する。

### (3) サブモジュール（Git Submodule）とリポジトリ分離
- **巨大パッケージのモジュール化**:
  - micro-ROS や モータードライバ等、他者・公式が管理する巨大なコードをプロジェクト内に直接組み込むとリポジトリが肥大化する。独立したリポジトリとして Fork し、`git submodule` で管理することで、`git clone` の軽量化と依存管理を両立する。
- **個人環境設定の混入防止**:
  - nvim や VS Code などの個人用ドットファイルを共通リポジトリにコミット/Submodule化しない。プロジェクトリポジトリにはチーム共通の開発設定のみを含める。

### (4) Git 事故とトラブルシューティング
- **`.gitignore` 未設定による成果物誤コミット**:
  - `a.out` や `main.exe`、`build/` フォルダなどのバイナリ成果物を誤ってコミットすると、GitHub 上の差分表示が重くなりブラウザがフリーズする原因になる。
  - すでにリモートに追跡されたファイルは `git rm --cached` で追跡を解除し、`.gitignore` に追記する。
- **空ディレクトルの罠**:
  - Git は空のディレクトリを追跡しないため、ローカルだけに手動作成した空設定フォルダがあってビルドが通っていても、CI（GitHub Actions）環境でディレクトリが存在せずビルドが失敗することがある。
- **複数機体（1号機・2号機）のコード管理**:
  - 機体ごとのパラメータやコード変更を直にメインブランチにマージすると崩壊する。機体ごとに `tag` を打つか、明確にブランチを分けて運用する。

---

## 3. C++ / Python / Rust 等のプログラミング知見・設計思想

### (1) C++ のハマりどころと最適化
- **型選定と `size_t` の扱い**:
  - `std::vector::size()` 等の戻り値と比較する際は `size_t` を使うが、`size_t` は環境依存の符号なし整数（unsigned）であるため、通常の `for` ループのカウンターに安易に使うとアンダーフロー等のバグを引き起こしやすい。
- **`volatile` の誤用と `std::atomic` / `std::mutex`**:
  - `volatile` はコンパイラによる最適化（レジスタキャッシュ）を抑制し、メモリMapped I/O等のハードウェアアクセスを保証するためのものであり、**C++仕様においてマルチスレッド間のスレッドセーフ（排他制御）を保証するものではない**。マルチスレッドでの同期には `std::atomic` や `std::mutex` を正しく使用すること。
- **スマートポインタと `std::weak_ptr`**:
  - ROS2 のノード内コールバックやタイマー等で `this` をキャプチャする際、コールバックがノードオブジェクトより長生きする可能性がある場合は、循環参照やクラッシュを防ぐために `weak_from_this()` / `std::weak_ptr` を使用する。
- **テンプレート（Template）過剰使用の抑制**:
  - 小さな処理に対して安易に `template` を多用すると、コンパイル時間の増大（ビルド遅延）とコード肥大化を招く。ビルド時間の短縮には高速リンカー **`mold`** の導入が非常に効果的。
- **静的解析・品質ツール**:
  - `sanitizer`（AddressSanitizer / UndefinedBehaviorSanitizer）、`perf`、`clang-tidy` を C++ ビルドパイプラインに組み込むことで、メモリリークや未定義動作を早期発見できる。

### (2) Python の使いどころと限界
- **適切な適用領域**:
  - 複雑なオブジェクト指向（OOP）を強要する大スケールシステムには向かないが、データ解析、CLI ツール（`subprocess`）、通信プロトコル試作（`requests`）、テストの自動化において威力を発揮する。
- **GIL (Global Interpreter Lock) の制約**:
  - Python は GIL の存在と動的型のオーバーヘッドにより、プロセス内ゼロコピー（Intra-process zero-copy）や数kHzオーダーの超低レイテンシ制御・通信には適さない。高頻度処理は C++ / Rust に委ねるべきである。

### (3) Rust のハマりどころと強力な機能
- **所有権（Ownership）と Borrow Checker の難所**:
  - 双方向リスト（LinkedList）やグラフ構造を書こうとすると、Borrow Checker と真っ向から衝突し `Option<Rc<RefCell<Node>>>` や `Arc<Mutex<T>>` のようなネスト（型地獄）が発生する。
  - 本番コードでの `unwrap()` の多用は禁物。`?` 演算子、`match`、`if let` による徹底したエラーハンドリングを行う。
- **`clap` による CLI 実装**:
  - `clap` パッケージの `derive` スタイルを使うことで、非常に型安全かつ宣言的にコマンドライン引数を解析できる。
- **パフォーマンス特性**:
  - Rust の `--release` ビルドにおける最適化レベルは極めて高く、C++ の `-O3` ビルドと同等以上の実行速度を発揮するケースが多い。

### (4) ソフトウェア設計思想
- **Cargo Cult Programming / Copy-Paste Ninja / Pattern Zealot の回避**:
  - 内部構造や動作用件を理解せず、AIや他人のコードをコピペして組み込む行為（カーゴ・カルト・プログラミング）を警戒すること。また、問題解決ではなく「デザインパターンを適用すること」自体が目的化する愚を避ける。
- **早すぎる最適化（Premature Optimization）の禁止**:
  - 「Premature optimization is the root of all evil」。まず正常に動くシンプルなコードを書き、ボトルネックが測定されてから最適化を行う。
- **「God Object（神オブジェクト）」の回避**:
  - 1つのノードやクラス（例: `joy_controller`）の中に、キネマティクス計算・状態遷移・通信処理など全機能を詰め込むのはアンチパターン。単一責任の原則に従ってコンポーネントを分解する。

---

## 4. 環境構築 (Docker / WSL2 / Ubuntu / Proxmox)

### (1) Docker / Docker Compose / DevContainer
- **非 Linux ホスト（macOS / Windows）における Docker の動作モデル**:
  - Docker は Linux カーネル機能（Cgroups, Namespaces）に依存しているため、macOS や Windows 上ではハイパーバイザ上の Linux VM 経由で動作している。そのため、I/O やコンテナ起動にネイティブ Linux 以上のオーバーヘッドが生じる。
- **マルチステージビルド (Multi-stage Build)**:
  - C++ や Rust 等のコンパイル言語では、ビルド用コンテナと実行用コンテナを分離することで、デプロイ用イメージからコンパイラやビルド依存を排除し、イメージサイズを劇的に軽量化できる。
- **VS Code DevContainer の推奨**:
  - DevContainer (`.devcontainer`) を導入することで、チーム全員の開発環境・ツールチェーン・コンテナ設定が完全に統一され、「個人の環境だけで動く」問題を撲滅できる。

### (2) WSL2 (Windows Subsystem for Linux 2)
- **USB デバイスのパススルー (`usbipd-win`)**:
  - WSL2 内で ST-Link、CAN アナライザ、LiDAR などの USB デバイスを認識させるには `usbipd-win` を使用する。
  - PowerShell 側で `usbipd bind` を行い、WSL2 起動時に自動アタッチするスクリプトを組むことで開発効率が向上する。
- **WSL2 カスタムカーネルビルド**:
  - WSL2 標準カーネルでは `joydev`（ジョイスティック `/dev/input/js*`）や仮想 CAN が無効化されている場合がある。
  - 解決策として、Microsoft の WSL2 用 Linux カーネルソースを取得し、`make menuconfig` で `CONFIG_INPUT_JOYDEV=y` 等を設定してカスタムビルドし `.wslconfig` で指定して起動する。

---

## 5. ROS2 のデバッグ・実装手法・システムアーキテクチャ

### (1) ノード設計・プロセス内通信・コンポーネント化
- **ノード分割のトレードオフ**:
  - 機能ごとにノードを細かく分けると耐障害性が高まるが、DDS 通信のオーバーヘッドが発生する。
- **プロセス内通信（Intra-process Communication / Zero-Copy）と Component**:
  - 大容量の画像データや高頻度制御においてゼロコピー転送を行うには、`rclcpp::NodeOptions().use_intra_process_comms(true)` を有効にし、メッセージを `std::unique_ptr` で publish/subscribe する必要がある。
  - これを実現するには、ノードを共有ライブラリ（Component）としてビルドし、単一のプロセスに動的ロードする構成をとる。
- **`twist_mux` による速度指令の安全統合**:
  - 手動操作（Joystick）と自動航行（Nav2）など複数の速度指令が衝突する場合、自前で制御用 switch 文を書くのではなく、標準の **`twist_mux`** を導入し優先度とタイムアウトで安全に統合する。

### (2) デバッグ・シミュレーション・トピックの作法
- **`use_sim_time:=true` の罠**:
  - Gazebo や ROS2 のシミュレーション環境、ROS Bag 再生時に `use_sim_time:=true` をノードに渡さないと、TF（座標変換）や MoveIt2、Nav2 が一切動作せず詰まる原因になる（実機動作時は `false`）。
- **シミュレーションと実機の透過的切替**:
  - トピック仕様を共通化した仮想コントロールパネルなどを作成しておくことで、コード変更なしでシミュレーションと実機を相互に差し替えてテスト可能になる。
- **`robot_localization` (EKF / Dual EKF)**:
  - IMU や車輪エンコーダのセンサ統合には `robot_localization` を使用する。
  - 自己位置推定では、ローカル用 EKF（`odom` -> `base_link`）とグローバル用 EKF（`map` -> `odom`）を組み合わせる **Dual EKF** 構成が標準。
- **標準メッセージ規格の尊重**:
  - 独自トピック構造体を乱立させず、`std_msgs`, `sensor_msgs`, `geometry_msgs` を優先的に使用する。
  - CAN 通信においても各ドライバ独自ではなく、ROS2 標準規格の **`can_msgs/msg/Frame`** に依存してノードを構築することが相互運用性において極めて重要。

---

## 6. 電子工作・マイコン制御・通信プロトコル (STM32 / CAN / IMU)

### (1) STM32 開発とビルド・書き込み環境
- **STM32CubeMX + VS Code / Makefile 運用**:
  - STM32CubeIDE を丸ごと使うより、STM32CubeMX でペリフェラル・クロックを設定し、Makefile や CMake として出力した上で VS Code や PlatformIO で開発する方が拡張性が高い。
- **Linux 用 udev ルール設定 (`ST-Link`)**:
  - ST-Link (Nucleo ボード等) を Linux に接続した際、`sudo` なしで書き込み・デバッグを行うため、`/etc/udev/rules.d/` にパーミッションを設定するルールを追加する。
- **非ブロッキングタイマー処理**:
  - マイコン制御で `delay()` を使うと割り込みや他処理がブロッキングされる。`HAL_GetTick()` を使用し、`if (HAL_GetTick() - prev_tick >= 1000)` の形式で非ブロッキングに周期処理を記述する。

### (2) CAN 通信 (Controller Area Network) & SocketCAN
- **Physical / Protocol 特性**:
  - CAN 通信の Recessive（1）および Dominant（0）の論理駆動は、I2C のオープンドレイン回路と概念的に近い。
- **SPI to CAN (MCP2515) と内蔵 CAN コントローラ**:
  - マイコン内蔵 CAN コントローラが最も低レイテンシだが、SPI 接続の CAN コントローラ（MCP2515）も広く使われる。
  - MCP2515 使用時は、クリスタル発振周波数（8MHz vs 16MHz）の設定指定ミスが原因で初期化エラーになる事例が多発する。
- **Linux SocketCAN とブリッジ**:
  - USB-CAN アナライザ等を Linux 上で扱う場合、`ros2socketcan` などを介して Linux の `can0` インターフェースと連携させる。これにより Linux 標準ツール（`candump` 等）で直接パケットを解析できる。

### (3) センサー制御・信号処理 (IMU / フィルタリング)
- **I2C クロックストレッチと応答確認**:
  - IMU センサ等で I2C 通信が不定になる場合、`HAL_I2C_IsDeviceReady()` でデバイスの準備状態を確認してからレジスタアクセスを行う。
- **IMU ドリフトと 1次ローパスフィルタ (IIR)**:
  - 角速度の単純積分はバイアス誤差が蓄積するため、静的キャリブレーションのみではドリフトを防げない。FFT でノイズを特定し、時定数を算出して離散化一次 IIR フィルタ（`val = alpha * new_val + (1 - alpha) * old_val`）をマイコン上に実装するのが標準手順。
