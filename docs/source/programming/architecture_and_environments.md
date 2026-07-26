# ソフトウェアアーキテクチャと環境構築のパラダイム

本章では、大規模なロボティクスシステムやバックエンド開発において不可欠となる、ソフトウェアアーキテクチャの設計思想と、それを支える環境構築のパラダイム（Nix, Docker, WSL, ネイティブ環境）について論じます。

## 1. ROS2アーキテクチャの分離：コアロジックとミドルウェアの疎結合

ロボットソフトウェア開発においてよく陥る罠が、ROS2の `rclcpp` や `rclpy` といった通信ミドルウェアのAPIに、システムの中核となる制御ロジックやアルゴリズムを強く結合させてしまうことです。

履歴内で次のような洞察が示されています。
> 「最近ちょっと思ってるのが、lib部分とrosのpub/sub部分はなるべくわけたほうが良いのか、という。ros2部分をラッパーにしてファイル分けてれば、ros2使わない時でもファイル引っ張ってくればそんままライブラリで使えるしなぁ」

### 失敗例：強結合なアーキテクチャ

以下のコードは、ROS2のノードクラス内に直接アルゴリズムがハードコードされている例です。これでは、ROS2環境が存在しない場所（例えば単体テスト環境や、WebAssembly上のシミュレータなど）でこのアルゴリズムを再利用することが不可能です。

```cpp
class AutonomousNavNode : public rclcpp::Node {
public:
    AutonomousNavNode() : Node("nav_node") {
        sub_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
            "scan", 10, [this](const sensor_msgs::msg::LaserScan::SharedPtr msg) {
                // アルゴリズムがROSコールバック内に直書きされている
                double min_distance = std::numeric_limits<double>::max();
                for (auto r : msg->ranges) {
                    if (r < min_distance) min_distance = r;
                }
                if (min_distance < 0.5) {
                    // 障害物回避ロジック...
                }
            });
    }
private:
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr sub_;
};
```

### 解決策：Hexagonal Architecture (Ports and Adapters)

コアとなるロジックは、純粋なC++やRustのライブラリ（ライブラリクレート）として切り出し、ROS2のノードはそのライブラリを呼び出すだけの「アダプタ層（ラッパー）」として機能させるべきです。

```cpp
// --- pure_algorithm.hpp (ROSに依存しない純粋なライブラリ) ---
#include <vector>

namespace navigation {
    class ObstacleAvoidance {
    public:
        bool should_stop(const std::vector<float>& scan_ranges, float threshold = 0.5f) {
            for (float r : scan_ranges) {
                if (r < threshold) return true;
            }
            return false;
        }
    };
}

// --- ros_adapter.cpp (ROS2との橋渡しのみを行う) ---
#include "pure_algorithm.hpp"
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>

class AutonomousNavNode : public rclcpp::Node {
public:
    AutonomousNavNode() : Node("nav_node") {
        sub_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
            "scan", 10, [this](const sensor_msgs::msg::LaserScan::SharedPtr msg) {
                if (algo_.should_stop(msg->ranges)) {
                    RCLCPP_WARN(this->get_logger(), "Obstacle detected! Stopping.");
                }
            });
    }
private:
    navigation::ObstacleAvoidance algo_;
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr sub_;
};
```

この設計により、アルゴリズムの単体テスト（GTestなど）が極めて容易になり、システムの保守性が飛躍的に向上します。

## 2. 開発環境のアーキテクチャ：Docker vs Nix

現代の開発において「私の環境では動いた（It works on my machine）」という問題を解決するために、コンテナ化や宣言的環境構築が必須となっています。
履歴内では、DockerとNixOS/Nixパッケージマネージャの間で深い議論が交わされていました。

### Dockerの利点と限界

Docker（および Docker Compose）は、「最強の環境固定と本番持ってけるポテンシャル」を持ちます。
Ubuntuベースのイメージを使用すれば、ROS2のインストールや `apt` パッケージの追加も容易です。

**懸念点：**
GUIアプリケーション（rviz2やGazeboなど）の描画設定（X11転送やWaylandの設定）、デバイスパススルー（USBカメラ、シリアルポート、GPU）の設定が極めて煩雑になります。
また、コンテナのオーバーヘッドや、ホスト環境とのディレクトリ同期（Bind mount）におけるパーミッション問題など、ローカル開発環境としては「ロマンが足りない」だけでなく、実用上の摩擦が生じます。

### Nixの哲学：宣言的アプローチ

Nix（`flake.nix`）は、Infrastructure as Code の究極系であり、全ての依存関係をハッシュ化して管理します。
「Simpler than Ansible, More versatile than Docker」と評されるように、開発環境（`nix develop`）を構築する際、コンテナのような分離の壁を作らずに、ホストOS上で完全に隔離された依存ツリーを展開できます。

```nix
# flake.nix のシンプルな例
{
  description = "ROS2 Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
  };

  outputs = { self, nixpkgs }: {
    devShells.x86_64-linux.default = let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
    in pkgs.mkShell {
      buildInputs = [
        pkgs.colcon
        pkgs.ros2Packages.humble.ros-core
        pkgs.cmake
      ];
      shellHook = ''
        echo "Welcome to the reproducible ROS2 environment."
      '';
    };
  };
}
```

Nixを用いることで、FishやVimなどの使い慣れたホストOSの設定をそのまま維持しつつ、ネットワーク層の隔離（Docker特有のネットワークトラブル）を気にせずに開発に没頭できます。
しかし、「思っているほどシンプルではない」「構成ファイルに大量の設定を書くと、別のPCに移動した際にまた設定しなければならない」という学習コストと運用の難しさも指摘されています。

## 3. 結論

ソフトウェアアーキテクチャにおいては、フレームワーク（ROS2等）とドメインロジックを分離する「クリーンな設計」を心がけることで、技術的負債を最小限に抑えることができます。
また、環境構築においては、チーム開発やデプロイを前提とするならば Docker や Pixi を、完全な再現性とローカル環境でのシームレスな操作感を求める（かつ学習コストを許容できる）のであれば Nix を選択するなど、プロジェクトの要件に応じたアーキテクチャ選定が求められます。
