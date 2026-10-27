# crosspoint-jp-fonts(非公式)

[CrossPoint Reader](https://github.com/crosspoint-reader/crosspoint-reader)(Xteink X4 向けのオープンソースのファームウェア)で使う、
**アンチエイリアスを濃くした日本語フォント(`.cpfont`)の作り方**です。

> **非公式・無保証です。** CrossPoint Reader、FreeInk、Xteink、フォントの権利者とは関係がありません。自己責任でご利用ください。
> **フォントそのもの(`.ttf` / `.cpfont`)は、このリポジトリに含まれません。** スクリプトと手順だけです(理由は「ライセンス」を参照)。

ファームウェア側の改造は、[crosspoint-reader-jp](https://github.com/homunet/crosspoint-reader-jp) にあります(こちらと併せて使うと、最も効果が出ます)。

## 何をするか

公式のウェブのフォントビルダー(`https://crosspointreader.com/fonts`)は、`fontconvert_sdcard.py` を使っています。その出力は、
アンチエイリアスが弱めです。原因は次の 2 点です。

1. フォントに入っている TrueType のヒンティング(命令)で、線が画素の境目に揃えられ、灰色の縁になる画素が少なくなる。
2. 8bit の濃度を、4bit に切り捨ててから閾値で 4 段階に落とすため、薄い縁の画素が白に落ちる。

このリポジトリの `--smooth` は、元のスクリプトに次の変更だけを加えます(差分は [`patches/fontconvert_sdcard-smooth.diff`](patches/fontconvert_sdcard-smooth.diff))。

- ヒンティングを無効にして描画する(`FT_LOAD_NO_HINTING`)。
- 8bit の濃度を、ガンマ補正した表(256 エントリ)で、四捨五入して 4 段階にする(`--aa-gamma`、既定 0.75)。
- **太らせる処理(エンボールデン)はしない。** `--smooth` を付けない場合の出力は、元のスクリプトとバイト単位で同一です。

### 効果の例
BIZ UDMincho Regular、16pt、フォント自身のグリフだけ(`--intervals cjk-jp`)で、画素の割合を比べた値です。

| | 白 | 薄い灰色 | 濃い灰色 | 黒 |
|---|---|---|---|---|
| 元のスクリプト | 58.6% | 7.1% | 9.7% | 24.6% |
| `--smooth` | 50.5% | 10.6% | 13.2% | 25.7% |

灰色の画素が増える一方で、黒は 1 ポイント程度しか増えません(線が太くなっていません)。比較画像: [`docs/before_after_16.png`](docs/before_after_16.png)、[拡大](docs/before_after_16_zoom.png)。

## 作り方

### 1. 準備
```
pip install freetype-py fonttools brotli pillow
scripts/fetch_fallback_fonts.sh        # 公式ビルダーと同じ Noto の fallback フォントを取得(SHA-256 で検証)
```
フォント(例: [BIZ UD](https://github.com/googlefonts/morisawa-biz-ud-mincho) の `BIZUDMincho-Regular.ttf` と `-Bold.ttf`)は、ご自身で入手してください。

### 2. ビルド
```
BOLD_TTF=BIZUDMincho-Bold.ttf scripts/build.sh BIZUDMincho-Regular.ttf BIZ_UDMincho 8,10,12,14,16,18 out --smooth
```
- 公式のウェブビルダーと同じ構成(`--intervals reading,cjk-jp` と、Noto の fallback)です。
- `--smooth` を外すと、公式ビルダーと同じ出力になります(`--aa-gamma` は `--smooth` のときだけ有効です)。
- `--aa-gamma 1.0` は線形で最も薄く、小さいほど縁が濃くなります。

**注意:** `--intervals cjk-jp` だけでビルドすると、BIZ UD のグリフが飛び飛びになり、インターバルが 4,096 個を超えて、ファームウェアが**ファイルを拒否します**。
公式と同じ `reading,cjk-jp` と fallback フォントを使うと、穴が埋まって 16 個程度になります。

### 3. SD カードに入れる
```
/fonts/<フォルダ名>/<名前>_<サイズ>.cpfont
```
- 本体のフォント一覧に出る名前は、**フォルダ名**です(ファイル名ではありません)。ファイル名は、末尾の `_<サイズ>.cpfont` だけが解釈されます。
- 公式版と濃い版を並べる例:
  ```
  /fonts/BIZ UDMincho/BIZ_UDMincho_16.cpfont
  /fonts/BIZ UDMincho Strong AA/BIZ_UDMincho_StrongAA_16.cpfont
  ```
- フォルダ名に半角スペースを使っています。一覧に出ない場合は、アンダースコアに替えてください。

### 4. 確認(デコーダ)
```
python3 scripts/cpfont_decode.py info   out/BIZ_UDMincho_16.cpfont       # ファームの読み込み検査と同じ検証
python3 scripts/cpfont_decode.py render out/BIZ_UDMincho_16.cpfont a.png # 4 階調で描画して画像にする
```

## サイズの目安
2 スタイル(Regular + Bold)・約 2.5 万グリフで、8pt が約 3.7 MB、16pt が約 12 MB、18pt が約 15 MB です。

## ライセンス

- **スクリプト:** MIT です。`fontconvert_sdcard.py` と `cpfont_version.py` は、[crosspoint-tools](https://github.com/crosspoint-reader/crosspoint-tools)(MIT、Copyright (c) 2025 SoFriendly)を元にしています。`LICENSE` はその原文です。変更点は `patches/` にあり、変更部分も MIT です。`build.sh`、`fetch_fallback_fonts.sh`、`cpfont_decode.py` も MIT です。
- **フォント:** BIZ UD と Noto のフォントは **SIL Open Font License 1.1** です。`.cpfont` は、これらのグリフを含む派生物です。**配布するときは、OFL の本文と著作権表示を同梱する必要があります。** このリポジトリは、フォントも `.cpfont` も配布しません。詳細は [`NOTICE.md`](NOTICE.md) を参照してください。
