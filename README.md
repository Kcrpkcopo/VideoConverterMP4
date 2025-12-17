# 🎬 VideoConverterMP4

## 概要
VideoConverterMP4 は、ドラッグ＆ドロップするだけで動画を MP4 に変換する Windows 専用ツールです。

- MTS は自動結合して MP4 に変換
- M2TS は個別変換後に結合
- その他形式も MP4 に変換
- 元ファイル名は保持（Premiere Pro 互換）

### 開発の背景
SONY製カメラで撮影された MTS/M2TS ファイルを Adobe Premiere Pro に読み込む際、  
音声が正しく認識されずノイズだけになる問題を回避することを目的としています。

---

## 対応形式
- MTS, M2TS, MP4, MOV, AVI, MKV, TS, WEBM, MPG

---

## 使用方法

### ビルド済み exe で実行
1. exe を起動
2. 変換したいファイル / フォルダをドラッグ＆ドロップ
3. 「変換開始」を押す
4. 出力は同フォルダ内 `converted_mp4`
5. 変換完了時にダイアログと効果音で通知されます

### ソースから実行する場合
1. Python 環境を用意
2. 必要ライブラリをインストール
   ```bash
   pip install -r requirements.txt
