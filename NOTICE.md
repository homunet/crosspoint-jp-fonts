# NOTICE

このリポジトリは、次のものを**配布しません**(スクリプトだけを含みます)。作成した `.cpfont` を配布する場合は、下記のライセンス条件に従ってください。

## スクリプト
- `scripts/fontconvert_sdcard.py`、`scripts/cpfont_version.py`: [crosspoint-tools](https://github.com/crosspoint-reader/crosspoint-tools) より。MIT License、Copyright (c) 2025 SoFriendly(`LICENSE` に原文)。`patches/fontconvert_sdcard-smooth.diff` は、それに対する変更です。

## フォント(このリポジトリには含まれません)
- **BIZ UDMincho / BIZ UDGothic:** Copyright 2022 The BIZ UDMincho Project Authors / The BIZ UDGothic Project Authors。SIL Open Font License 1.1。
  <https://github.com/googlefonts/morisawa-biz-ud-mincho>、<https://github.com/googlefonts/morisawa-biz-ud-gothic>
- **Noto フォント(fallback)**: `scripts/fetch_fallback_fonts.sh` が取得します。SIL Open Font License 1.1。
  取得元と SHA-256 は、`scripts/fallback-fonts.sha256` と、取得元の `SOURCES.md` / `OFL.txt`
  (<https://github.com/crosspoint-reader/crosspoint-tools/tree/master/scripts/font-builder/default-fallback-fonts>)を参照してください。

## OFL の主な条件(要約。正式な条件は各 OFL の本文を参照)
- フォントを単体で販売してはいけません。
- 派生物にも、元の著作権表示と OFL の本文を付けて配布します。
- 派生物は、同じ OFL の条件で配布します。
