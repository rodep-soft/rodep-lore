# Package Manager

PackageManagerについてのOverview.

## PMとは何なのか

Softwareのインストール、削除、依存関係管理などをするためのツール.

以下はdebian-based Linux(UbuntuやMint)で`vim`をインストールするコマンドだが、内部では処理が数段階で行われており,

1. vimを探す(search)
2. 必要なライブラリを探す
3. download
4. install

以上を全て実行してくれる.

```bash
# ex.
# vim installation
$ sudo apt install vim
```

このコマンドはDistributionによって違うので、

- APT (Ubuntu, Mint, Debian etc.)
- DNF (Fedora)
- Pacman (Arch)
- Portage (Gentoo)
- Nix (NixOS)

など、使い方は基本的に似てはいるがオプション等はかなり違うことが多い.

Distroによって違うと不便に感じる人も多いので、開発時は`nix`や`homebrew`などを使ったり、`Docker`を使うことも多い.
Ubuntuの`snap`もdistroによらないが、

- nix > homebrew
- flatpak > snap

という評価を見かけることが多い.

Linux固有というわけでもなく、macOSだと`brew`, Windowsだと`winget`などのコマンドで同じことができる.

## プログラミング言語のPM

プログラミング言語にもPMが存在する場合があり、有名どころだと,

- PIP (Python)
- NPM, PNPM, YARN (nodejs)
- Composer (PHP)
- Cargo (Rust)

1つの言語で1つのPMという訳ではないので注意.







