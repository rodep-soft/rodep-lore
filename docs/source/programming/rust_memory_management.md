# 現代ロボティクスにおけるRustのメモリ管理と並行処理設計

本章では、ロボティクス開発（特にROS2環境）において、C++からRustへと移行する際に直面するメモリ管理のパラダイムシフトと、その実践的な設計思想について深掘りします。

## 1. 所有権システムと `std::unique_ptr` の比較

従来のC++（Modern C++）では、ヒープ上のリソース管理に `std::unique_ptr` を用いることがベストプラクティスとされてきました。しかし、明示的な `std::move` の記述が必要であり、所有権の移動がコード上で煩雑になるケースが多々あります。

```cpp
// C++での一意な所有権の移動
#include <iostream>
#include <memory>

class SensorData {
public:
    std::vector<double> values;
    SensorData() { values.resize(1000); }
};

void process_data(std::unique_ptr<SensorData> data) {
    // 処理
}

int main() {
    auto data = std::make_unique<SensorData>();
    // 明示的にmoveする必要がある
    process_data(std::move(data));
    // ここで data にアクセスすると未定義動作（セグフォの可能性）
    return 0;
}
```

対してRustでは、言語レベルで所有権（Ownership）が組み込まれているため、ムーブセマンティクスがデフォルトです。
履歴内でも言及されていた通り、「`unique_ptr` だと明示的にムーブするが、Rustだと単にmemcpyと元変数を使用不可にするだけで速く、シンプル」という特徴があります。

```rust
// Rustでの所有権の移動
struct SensorData {
    values: Vec<f64>,
}

impl SensorData {
    fn new() -> Self {
        Self { values: vec![0.0; 1000] }
    }
}

fn process_data(data: SensorData) {
    // 処理
}

fn main() {
    let data = SensorData::new();
    // デフォルトでムーブされる
    process_data(data);
    // ここで data にアクセスするとコンパイルエラーとなる（安全）
    // println!("{:?}", data.values); // Compile Error!
}
```

このように、Rustではダングリングポインタや二重解放（Double Free）といったメモリ関連のバグをコンパイル時に完全に排除できます。

## 2. 参照カウントと並行処理： `std::shared_ptr` から `Arc` へ

ROS2のような分散非同期システムでは、複数のコールバックやスレッドで状態を共有することが頻繁に発生します。
C++では `std::shared_ptr` と `std::mutex` を組み合わせて用いますが、Rustでは `Arc` (Atomic Reference Counted) と `Mutex` (または `RwLock`) を用います。

履歴にて、「C++でもatomicデフォならもう、何か考えずにArc使いたくなるよなぁ」とあるように、並行プログラミングにおいて状態を共有する際の安全性と利便性はRustに軍配が上がります。

### 失敗例：C++におけるデータ競合

```cpp
#include <iostream>
#include <thread>
#include <memory>
#include <vector>

struct SharedState {
    int counter = 0;
};

int main() {
    auto state = std::make_shared<SharedState>();
    std::vector<std::thread> threads;

    for (int i = 0; i < 10; i++) {
        threads.emplace_back([state]() {
            // ミューテックスによる保護を忘れるとデータ競合が発生
            for (int j = 0; j < 1000; j++) {
                state->counter++; 
            }
        });
    }

    for (auto& t : threads) { t.join(); }
    std::cout << state->counter << std::endl; // 10000にならないことが多い
    return 0;
}
```

### 解決策：Rustの `Arc<Mutex<T>>`

Rustでは、スレッド間で安全に共有可能であること（`Send` および `Sync` トレイト）が型システムで保証されています。
`Arc` の中身を可変にするためには、必ず `Mutex` などの内部可変性（Interior Mutability）を提供するプリミティブを経由しなければなりません。

```rust
use std::sync::{Arc, Mutex};
use std::thread;

struct SharedState {
    counter: i32,
}

fn main() {
    let state = Arc::new(Mutex::new(SharedState { counter: 0 }));
    let mut handles = vec![];

    for _ in 0..10 {
        let state_clone = Arc::clone(&state);
        let handle = thread::spawn(move || {
            // ロックを取得しなければ値にアクセスできない（コンパイラが強制）
            for _ in 0..1000 {
                let mut data = state_clone.lock().unwrap();
                data.counter += 1;
            }
        });
        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("Counter: {}", state.lock().unwrap().counter); // 確実に10000
}
```

しかし、ROS2 (rclrs) の文脈において、「ドライバあるし Arc<Mutex<>> のクローン地獄になりそうだし、ROSっぽくない」という懸念も挙げられていました。
実際、ノード間で過度に状態を共有するアーキテクチャは、ロックの競合によるパフォーマンス低下（Contention）を招きます。

## 3. `rclrs` と ROS2 エコシステムにおけるメモリ管理

RustでROS2のノードを実装する `rclrs` においては、コールバック内でデータをどのように処理するかが課題となります。
センサデータ（例えば `sensor_msgs/msg/JointState` や LiDARの点群データ）は大容量になりがちです。

### ゼロコピー通信とライフタイム

理想的には、ROS2のミドルウェア（DDS）から受け取ったデータをコピーせずにコールバックで処理することが求められます。
C++の `rclcpp` では、`std::unique_ptr` を受け取るシグネチャを用いることでこれを実現しています。

Rustにおいても、コールバックに渡されるメッセージの所有権やライフタイムを厳密に管理することで、不要なメモリ確保（アロケーション）を削減できます。

```rust
use rclrs::{Context, Node};
use sensor_msgs::msg::JointState;
use std::sync::{Arc, Mutex};

fn main() -> Result<(), rclrs::RclrsError> {
    let context = Context::new(std::env::args())?;
    let mut node = context.create_node("joint_state_listener")?;

    // 状態を保持するための構造体
    let latest_state = Arc::new(Mutex::new(None));
    let state_clone = Arc::clone(&latest_state);

    let _subscription = node.create_subscription::<JointState, _>(
        "/joint_states",
        rclrs::QOS_PROFILE_DEFAULT,
        move |msg: JointState| {
            // メッセージの所有権を受け取る
            let mut state = state_clone.lock().unwrap();
            *state = Some(msg); // 必要なデータだけを保持し、古いものは自動でDropされる
        },
    )?;

    rclrs::spin(&node)?;
    Ok(())
}
```

上記のように、Rustの厳格なコンパイラの下では、クロージャ環境への変数のキャプチャや、スレッド間のデータ受け渡しが極めて安全かつ明瞭になります。
「Arc<Mutex<T>>のクローン地獄」を回避するためには、アクターモデルのようにスレッド間でメッセージパッシング（`std::sync::mpsc` や `crossbeam-channel`）を行う設計を採用し、共有メモリへの依存を減らすことが効果的です。

## 結論

Rustのメモリ管理モデルは、一見すると制約が厳しく学習曲線が急に見えますが、ロボティクスソフトウェアにおける致命的なメモリバグを未然に防ぐ強力な武器となります。特にC++に慣れ親しんだエンジニアにとって、`unique_ptr` や `shared_ptr` の概念をより安全に昇華させたRustの所有権・借用システムは、次世代のシステムプログラミングにおいて不可欠な知識と言えるでしょう。
