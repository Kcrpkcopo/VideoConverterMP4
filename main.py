import os
import sys
import subprocess
import threading
import time
import customtkinter as ctk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

# =============================
# COLOR 定義
# =============================
COLOR = {
    "bg_root": "#101010",
    "bg_title": "#101010",
    "bg_drop": "#1a1a1a",
    "bg_block": "#181818",
    "bg_log": "#0f0f0f",
    "bg_button": "#262626",
    "bg_button_hover": "#303030",
    "bg_button_disabled": "#1c1c1c",
    "bg_progress": "#262626",
    "fg_progress_idle": "#00ff99",
    "fg_progress_work": "#ffaa00",
    "text_main": "#e0e0e0",
    "text_sub": "#b0b0b0",
    "log_ok": "#00ff99",
    "log_err": "#ff6666",
    "log_info": "#cccccc",
}

# =============================
# PyInstaller 対応
# =============================
def resource_path(p):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.abspath(p)

FFMPEG = resource_path("ffmpeg.exe")
FFPROBE = resource_path("ffprobe.exe")
ICON_FILE = resource_path("video_change.ico")  # ここで ICO を指定

# =============================
# GUI 初期化
# =============================
ctk.set_appearance_mode("dark")
root = TkinterDnD.Tk()
root.title("VideoConverterMP4")
root.iconbitmap(ICON_FILE)  # タイトルバー・タスクバーのアイコンを設定
root.geometry("500x450")
root.resizable(False, False)
root.configure(bg=COLOR["bg_title"])

# =============================
# 状態
# =============================
files = []
groups = []
cancel_flag = False
current_process = None
SUPPORTED_OTHER = (".mov", ".avi", ".mkv", ".ts", ".webm", ".mpg")

# =============================
# ログ
# =============================
def log(msg, tag="info"):
    log_box.insert("end", msg + "\n", tag)
    log_box.see("end")

# =============================
# ボタン制御
# =============================
def lock_buttons():
    btn_convert.configure(state="disabled")
    btn_cancel.configure(state="normal")

def unlock_all():
    btn_convert.configure(state="disabled")
    btn_cancel.configure(state="disabled")

def unlock_convert():
    btn_convert.configure(state="normal")
    btn_cancel.configure(state="disabled")

# =============================
# リセット
# =============================
def reset_state():
    global files, groups, cancel_flag
    files = []
    groups = []
    cancel_flag = False
    progress.set(0)
    progress_label.configure(text="進捗: 0%")
    time_label.configure(text="残り時間: -")
    progress.configure(progress_color=COLOR["fg_progress_idle"])
    unlock_all()

# =============================
# キャンセル
# =============================
def cancel_process():
    global cancel_flag, current_process
    cancel_flag = True
    if current_process and current_process.poll() is None:
        current_process.kill()
    log("🛑 処理をキャンセルしました", "err")
    reset_state()

# =============================
# ドロップ
# =============================
def on_drop(event):
    reset_state()
    raw = root.tk.splitlist(event.data)
    all_files = []

    for p in raw:
        p = p.strip("{}")
        if os.path.isdir(p):
            for r, _, fs in os.walk(p):
                for f in fs:
                    all_files.append(os.path.join(r, f))
        else:
            all_files.append(p)

    mts = [f for f in all_files if f.lower().endswith(".mts")]
    m2ts = [f for f in all_files if f.lower().endswith(".m2ts")]
    mp4 = [f for f in all_files if f.lower().endswith(".mp4")]
    other = [f for f in all_files if f.lower().endswith(SUPPORTED_OTHER)]

    if (mts or m2ts) and mp4:
        messagebox.showwarning("混在エラー", "MTS/M2TS と MP4 を同時に処理できません")
        return

    if mp4:
        log("ℹ MP4なので変換しません", "info")
        reset_state()
        return

    global files, groups
    if mts:
        files = sorted(mts)
        log(f"📥 MTS 読み込み完了 ({len(files)} files)", "info")
        groups = [[(f, 0, 0, 0)] for f in files]  # 自動判定
        unlock_convert()
        log("📋 処理内容:", "info")
        log(f"- MTS {len(files)}本 → MP4に結合（コピー）", "info")
        log("- 元ファイル名は保持されます（Premiere Pro 互換）", "info")
        return

    if m2ts:
        files = sorted(m2ts)
        log(f"📥 M2TS 読み込み完了 ({len(files)} files)", "info")
        groups = [[(f, 0, 0, 0)] for f in files]  # 自動判定
        unlock_convert()
        log("📋 処理内容:", "info")
        log(f"- M2TS {len(files)}本 → 個別MP4に変換して結合", "info")
        log("- 元ファイル名は保持されます（Premiere Pro 互換）", "info")
        return

    if other:
        files = sorted(other)
        log(f"📥 変換対象 ({len(files)} files)", "info")
        groups = [[(f, 0, 0, 0)] for f in files]
        unlock_convert()
        log("📋 処理内容:", "info")
        log(f"- {len(other)}本 → MP4に変換（単体変換）", "info")
        log("- 元ファイル名は保持されます（Premiere Pro 互換）", "info")
        return

    messagebox.showwarning("非対応", "対応形式ではありません")

# =============================
# 変換
# =============================
def convert_worker():
    import winsound
    global cancel_flag, current_process
    cancel_flag = False
    lock_buttons()
    progress.set(0)
    progress_label.configure(text="進捗: 0%")
    time_label.configure(text="残り時間: 計算中...")
    progress.configure(progress_color=COLOR["fg_progress_work"])
    log("🎬 変換開始", "info")
    log("- 元ファイル名は保持されます", "info")
    log("- 拡張子のみ MP4 に変換されます", "info")

    out_root = os.path.join(os.path.dirname(files[0]), "converted_mp4")
    os.makedirs(out_root, exist_ok=True)
    total = len(groups)
    start = time.time()

    for i, g in enumerate(groups, 1):
        if cancel_flag:
            return

        base = os.path.splitext(os.path.basename(g[0][0]))[0]
        first_ext = os.path.splitext(g[0][0])[1].lower()

        if first_ext == ".mts":
            # MTS → コピー結合
            list_txt = os.path.join(out_root, f"{base}_list.txt")
            with open(list_txt, "w", encoding="utf-8") as f:
                for item in g:
                    f.write(f"file '{item[0]}'\n")
            out_mp4 = os.path.join(out_root, f"{base}.mp4")
            cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_txt,
                   "-c:v", "copy", "-c:a", "aac", out_mp4]
            current_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            current_process.wait()

        elif first_ext == ".m2ts":
            temp_mp4_list = []
            for j, (file_path, _, _, _) in enumerate(g):
                temp_mp4 = os.path.join(out_root, f"temp_{j}_{base}.mp4")
                cmd = [FFMPEG, "-y", "-i", file_path, "-c:v", "libx264", "-c:a", "aac", temp_mp4]
                current_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
                current_process.wait()
                temp_mp4_list.append(temp_mp4)
            list_txt = os.path.join(out_root, f"{base}_list.txt")
            with open(list_txt, "w", encoding="utf-8") as f:
                for temp_file in temp_mp4_list:
                    f.write(f"file '{temp_file}'\n")
            out_mp4 = os.path.join(out_root, f"{base}.mp4")
            cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", out_mp4]
            current_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            current_process.wait()
            for temp_file in temp_mp4_list:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        else:
            # その他 → 単体変換
            file_path = g[0][0]
            out_mp4 = os.path.join(out_root, f"{base}.mp4")
            cmd = [FFMPEG, "-y", "-i", file_path, "-c:v", "libx264", "-c:a", "aac", out_mp4]
            current_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            current_process.wait()

        progress.set(i / total)
        progress_label.configure(text=f"進捗: {int(i / total * 100)}%")
        elapsed = time.time() - start
        remain = int(elapsed / i * (total - i)) if i else 0
        time_label.configure(text=f"残り時間: {remain} 秒")

    log("🎉 変換完了", "ok")
    log(f"- 出力先: {out_root}", "info")
    winsound.MessageBeep()  # 完了時にSE
    messagebox.showinfo("完了", "変換が完了しました！")
    unlock_all()

# =============================
# GUI
# =============================
title_frame = ctk.CTkFrame(root, fg_color=COLOR["bg_title"])
title_frame.pack(fill="x")
ctk.CTkLabel(title_frame, text="📂 MP4へ変換します",
             font=("Segoe UI", 20), text_color=COLOR["text_main"]).pack(pady=15)

drop_frame = ctk.CTkFrame(root, height=120, fg_color=COLOR["bg_drop"])
drop_frame.pack(fill="x", padx=20)
drop_label = ctk.CTkLabel(drop_frame, text="ここにファイル / フォルダをドロップ",
                          font=("Segoe UI", 16), text_color=COLOR["text_main"])
drop_label.pack(expand=True)
drop_label.drop_target_register(DND_FILES)
drop_label.dnd_bind("<<Drop>>", on_drop)

control_frame = ctk.CTkFrame(root, fg_color=COLOR["bg_block"])
control_frame.pack(fill="x", padx=20, pady=10)
btn_convert = ctk.CTkButton(control_frame, text="変換開始", state="disabled",
                            command=lambda: threading.Thread(target=convert_worker, daemon=True).start())
btn_convert.pack(pady=4)
btn_cancel = ctk.CTkButton(control_frame, text="キャンセル", state="disabled", command=cancel_process)
btn_cancel.pack(pady=4)

progress_frame = ctk.CTkFrame(root, fg_color=COLOR["bg_block"])
progress_frame.pack(fill="x", padx=20)
progress = ctk.CTkProgressBar(progress_frame, width=400)
progress.set(0)
progress.pack(pady=(10, 3))
progress_label = ctk.CTkLabel(progress_frame, text="進捗: 0%", text_color=COLOR["text_sub"])
progress_label.pack()
time_label = ctk.CTkLabel(progress_frame, text="残り時間: -", text_color=COLOR["text_sub"])
time_label.pack(pady=(0, 10))

log_frame = ctk.CTkFrame(root, fg_color=COLOR["bg_block"])
log_frame.pack(fill="both", expand=True, padx=15, pady=(5, 10))
log_box = ctk.CTkTextbox(log_frame, height=80, fg_color=COLOR["bg_log"], text_color=COLOR["text_main"])
log_box.pack(fill="both", expand=True, padx=10, pady=10)
log_box.tag_config("ok", foreground=COLOR["log_ok"])
log_box.tag_config("err", foreground=COLOR["log_err"])
log_box.tag_config("info", foreground=COLOR["log_info"])

root.mainloop()
