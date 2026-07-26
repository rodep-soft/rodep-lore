# STM32におけるI2C通信とIMUノイズ対策の泥臭い実録

組み込みシステム、特にモータやアクチュエータを多用するロボティクス環境において、STM32のI2C通信とIMU（慣性計測装置）のノイズ問題は開発者を最も悩ませるトラブルの一つです。本稿では、ハードウェア設計からSTM32 HALのソフトウェア実装に至るまで、現場で実際に遭遇した失敗例とその解決プロセスを詳細に記録します。

## 1. 悲劇の始まり：I2Cバスのハングアップ

STM32（特にSTM32F1やF4シリーズ）のハードウェアI2Cは、ノイズに対して非常に敏感です。モータの駆動時や、リレーの切り替え時に発生するスパイクノイズがSCL（クロック）またはSDA（データ）ラインに乗ると、I2Cペリフェラルが異常な状態に陥り、バスがハングアップします。

典型的な症状としては、`HAL_I2C_Mem_Read()` が `HAL_TIMEOUT` または `HAL_ERROR` を返し続け、再起動するまで通信が一切復旧しないというものです。

### 失敗例：単純なHALの利用
初期の実装では、以下のように単純にHAL関数を呼び出していました。

```c
// 失敗しやすい初期の実装例
uint8_t data[6];
HAL_StatusTypeDef status = HAL_I2C_Mem_Read(&hi2c1, IMU_ADDR, REG_ACCEL, I2C_MEMADD_SIZE_8BIT, data, 6, 100);

if (status != HAL_OK) {
    // 単純なエラー出力のみで復旧処理がない
    printf("I2C Error!\n");
}
```

このコードでは、一度I2Cバスがロックされると、マイコンをリセットするまで復旧できません。ロボットの運用中においては致命的な欠陥となります。

## 2. ハードウェアレベルのノイズ対策

ソフトウェアで対処する前に、ハードウェアレベルでI2Cバスの安定性を確保することが鉄則です。

### 2.1 プルアップ抵抗の最適化
I2Cモジュールに内蔵されている10kΩ程度のプルアップ抵抗では、ケーブル長が10cmを超える場合や、隣接するモータ線からのクロストークがある場合には不十分です。
SDA、SCLラインに対して、**2.2kΩ〜4.7kΩ**の外部プルアップ抵抗をマイコンの直近とセンサの直近の両方に配置することで、信号の立ち上がり波形（スルーレート）を改善し、ノイズマージンを稼ぎます。

### 2.2 ダンピング抵抗の追加
オーバーシュートやアンダーシュートによる誤動作を防ぐため、SDAおよびSCLラインの直列に**33Ω〜47Ω**のダンピング抵抗を挿入します。これにより、インピーダンスマッチングが図られ、反射波による波形の乱れを抑えることができます。

### 2.3 グラウンド分離とシールド
モータ駆動用のGND（パワーGND）と、マイコン・センサ用のGND（シグナルGND）は必ず分離し、一点アースで接続します。さらに、I2Cケーブルはツイストペア線を避け（SDAとSCLを撚るとクロストークが増大します）、SDAとGND、SCLとVCCといった形でペアにするか、全体をシールド線で覆うことが有効です。

## 3. ソフトウェアレベルのI2Cバス・リカバリ実装

ハードウェア対策を施しても、突発的なESD（静電気放電）等によるハングアップはゼロにはできません。そのため、ソフトウェアによる自動リカバリ機構が必須となります。

I2Cバスがロックされる主な原因は、スレーブ（IMU側）がSDAラインをLOWに引っ張ったままの状態（ACK待ち等）でマスター（STM32側）がリセットされたり、通信が中断したりすることです。

### 堅牢なリカバリ手順

1. STM32のI2Cペリフェラルを無効化する。
2. SCLおよびSDAピンを汎用GPIO（オープンドレイン出力）に設定する。
3. SDAがHIGHになるまで、SCLをソフトウェアでクロック（最大9回）トグルする。
4. SDAがHIGHになったら、STOPコンディション（SCLがHIGHの状態でSDAをLOWからHIGHへ）を生成する。
5. ピンの設定を代替機能（Alternate Function）に戻し、I2Cペリフェラルを再初期化する。

以下に具体的な実装例を示します。

```c
// I2Cバスのロック解除関数の実装例
void I2C_ClearBus() {
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    // 1. I2Cペリフェラルの無効化
    __HAL_I2C_DISABLE(&hi2c1);

    // 2. ピンをGPIO出力（オープンドレイン）に変更
    GPIO_InitStruct.Pin = GPIO_PIN_8 | GPIO_PIN_9; // 例: PB8(SCL), PB9(SDA)
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_9, GPIO_PIN_SET); // SDA High
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8, GPIO_PIN_SET); // SCL High
    HAL_Delay(1);

    // 3. SDAがHIGHになるまでダミークロックを送信 (最大9回)
    for (int i = 0; i < 9; i++) {
        if (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_9) == GPIO_PIN_SET) {
            break;
        }
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8, GPIO_PIN_RESET); // SCL Low
        HAL_Delay(1);
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8, GPIO_PIN_SET);   // SCL High
        HAL_Delay(1);
    }

    // 4. STOPコンディションの生成
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_9, GPIO_PIN_RESET); // SDA Low
    HAL_Delay(1);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8, GPIO_PIN_SET);   // SCL High
    HAL_Delay(1);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_9, GPIO_PIN_SET);   // SDA High
    HAL_Delay(1);

    // 5. I2Cペリフェラルの再初期化
    HAL_I2C_DeInit(&hi2c1);
    HAL_I2C_Init(&hi2c1);
}
```

この処理を `HAL_I2C_Mem_Read` がエラーを返した際に呼び出すことで、システムを再起動することなく自律的に通信を復旧させることが可能になります。

## 4. IMUデータのフィルタリングとノイズ除去

ハードウェアと通信レイヤーが安定した後は、取得したIMUデータ自体のノイズ処理が課題となります。

ロボットの振動やモータの回転による周期的なノイズが加速度データに混入すると、姿勢推定アルゴリズム（カルマンフィルタやマホニーフィルタ）が発散する原因となります。

### デジタルローパスフィルタ（LPF）の活用
多くの最新IMU（例: MPU6050, BNO085など）には、ハードウェアのデジタルローパスフィルタ（DLPF）が内蔵されています。まずはこれを適切に設定することが第一歩です。
例えば、サンプリングレートを1kHzに設定した場合、DLPFのカットオフ周波数を42Hzや98Hz等、システムのダイナミクスに合わせて下げることで、高周波の機械的振動を効果的にカットできます。

### ソフトウェアでの移動平均と外れ値除去
ハードウェアLPFだけでは除去しきれない突発的なスパイク（I2Cのビット化けが原因で生じる異常値など）に対しては、ソフトウェアでメディアンフィルタや移動平均フィルタを適用します。

```c
// リングバッファを用いた単純な移動平均フィルタの実装例
#define FILTER_SIZE 10

typedef struct {
    float buffer[FILTER_SIZE];
    int index;
    float sum;
} MovingAverageFilter;

void Filter_Init(MovingAverageFilter *filter) {
    for (int i = 0; i < FILTER_SIZE; i++) {
        filter->buffer[i] = 0.0f;
    }
    filter->index = 0;
    filter->sum = 0.0f;
}

float Filter_Update(MovingAverageFilter *filter, float new_value) {
    // 最も古いデータを引く
    filter->sum -= filter->buffer[filter->index];
    // 新しいデータを追加する
    filter->buffer[filter->index] = new_value;
    filter->sum += new_value;
    
    // インデックスの更新
    filter->index = (filter->index + 1) % FILTER_SIZE;
    
    return filter->sum / FILTER_SIZE;
}
```

ただし、移動平均フィルタは位相遅れ（タイムラグ）を生じさせるため、制御ループの応答性に悪影響を及ぼす可能性があります。そのため、カットオフ周波数と応答性のバランスを慎重にチューニングする必要があります。

## まとめ

STM32におけるI2CとIMUの統合は、「繋げば動く」というものではありません。ノイズという目に見えない敵に対して、ハードウェア（抵抗や配線）とソフトウェア（エラーリカバリやフィルタリング）の両面から多段的な防御策を講じることで、初めて実運用に耐えうる堅牢なシステムが構築できます。
