import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import json
import os
from itertools import product

SAVE_FILE = "saved_prompts.json"
MAX_SAVES = 50  # 保存数の上限

class PromptGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI画像プロンプト作成機")
        self.root.geometry("800x600")

        # ======= 固定部分エリア =======
        self.fixed_frame = tk.Frame(root)
        self.fixed_frame.pack(fill="x", pady=5)

        tk.Label(self.fixed_frame, text="固定部分:").pack(side=tk.LEFT)
        self.fixed_entries = []
        self.add_fixed_entry()

        self.fixed_button_frame = tk.Frame(root)
        self.fixed_button_frame.pack(fill="x", pady=2)
        tk.Button(self.fixed_button_frame, text="固定部分を追加", command=self.add_fixed_entry).pack(side=tk.LEFT, padx=5)
        tk.Button(self.fixed_button_frame, text="固定部分を削除", command=self.remove_fixed_entry).pack(side=tk.LEFT, padx=5)

        # ======= 可変部分エリア =======
        self.variable_frame = tk.Frame(root)
        self.variable_frame.pack(fill="x", pady=10)

        tk.Label(self.variable_frame, text="可変部分:").pack(anchor="w")
        self.variable_entries = []
        self.add_variable_section()

        self.variable_button_frame = tk.Frame(root)
        self.variable_button_frame.pack(fill="x", pady=2)
        tk.Button(self.variable_button_frame, text="可変部分を追加", command=self.add_variable_section).pack(side=tk.LEFT, padx=5)
        tk.Button(self.variable_button_frame, text="可変部分を削除", command=self.remove_variable_section).pack(side=tk.LEFT, padx=5)

        # ======= プロンプト生成ボタン =======
        self.generate_button = tk.Button(root, text="プロンプト生成", command=self.generate_prompts)
        self.generate_button.pack(pady=5)

        # ======= 出力エリア =======
        self.output_text = tk.Text(root, height=10, width=80)
        self.output_text.pack(pady=5)

        # ======= コピー＆リセットボタン =======
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=5)
        tk.Button(self.button_frame, text="コピー", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="リセット", command=self.reset_output).pack(side=tk.LEFT, padx=5)

        # ======= セーブ＆ロードエリア（画面下部） =======
        self.bottom_save_frame = tk.Frame(root)
        self.bottom_save_frame.pack(side="bottom", fill="x", pady=5)

        # セーブ名入力欄
        tk.Label(self.bottom_save_frame, text="保存名:").pack(side=tk.LEFT, padx=5)
        self.save_name_entry = tk.Entry(self.bottom_save_frame, width=20)
        self.save_name_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(self.bottom_save_frame, text="セーブ", command=self.save_prompt).pack(side=tk.LEFT, padx=5)
        tk.Button(self.bottom_save_frame, text="ロード", command=self.load_prompt).pack(side=tk.LEFT, padx=5)

        self.save_list = ttk.Combobox(self.bottom_save_frame, state="readonly", width=15)
        self.save_list.pack(side=tk.LEFT, padx=5)
        self.update_save_list()

    def add_fixed_entry(self):
        """固定部分の入力欄を追加"""
        entry = tk.Entry(self.fixed_frame, width=30)
        entry.pack(side=tk.LEFT, padx=5)
        self.fixed_entries.append(entry)

    def remove_fixed_entry(self):
        """最後の固定部分を削除"""
        if self.fixed_entries:
            entry = self.fixed_entries.pop()
            entry.destroy()

    def add_variable_section(self):
        """可変部分を追加（横に増える）"""
        frame = tk.Frame(self.variable_frame)
        tk.Label(frame, text=f"可変 {len(self.variable_entries) + 1}:").pack(anchor="w")

        entry_frame = tk.Frame(frame)
        entry_frame.pack(anchor="w", fill="x")

        entries = []
        self.add_variable_entry(entries, entry_frame)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(anchor="w")

        tk.Button(btn_frame, text="+", command=lambda: self.add_variable_entry(entries, entry_frame)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="-", command=lambda: self.remove_variable_entry(entries, entry_frame)).pack(side=tk.LEFT, padx=2)

        frame.pack(fill="x", pady=5)
        self.variable_entries.append((frame, entries, entry_frame))

    def add_variable_entry(self, entries, entry_frame):
        """可変部分の横の入力欄を増やす"""
        entry = tk.Entry(entry_frame, width=15)
        entry.pack(side=tk.LEFT, padx=5)
        entries.append(entry)

    def remove_variable_entry(self, entries, entry_frame):
        """可変部分の横の入力欄を削除"""
        if len(entries) > 1:
            entry = entries.pop()
            entry.destroy()

    def remove_variable_section(self):
        """最後の可変部分（縦）を削除"""
        if self.variable_entries:
            frame, entries, entry_frame = self.variable_entries.pop()
            frame.destroy()

    def generate_prompts(self):
        """プロンプトを生成"""
        fixed_texts = [entry.get().strip() for entry in self.fixed_entries if entry.get().strip()]
        variable_lists = [
            [entry.get().strip() for entry in entries if entry.get().strip()]
            for _, entries, _ in self.variable_entries
        ]
        variable_lists = [v for v in variable_lists if v]  # 空のリストを除外

        if not fixed_texts or not variable_lists:
            messagebox.showerror("エラー", "固定部分と可変部分を入力してください")
            return

        fixed_part = ",".join(fixed_texts)
        prompts = [f"{fixed_part}," + ",".join(variation) for variation in product(*variable_lists)]
        prompts = [p.replace(",,", ",") for p in prompts]  # ,, を削除

        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, "\n".join(prompts))

    def copy_to_clipboard(self):
        """クリップボードにコピー"""
        text = self.output_text.get("1.0", tk.END).strip()
        if text:
            pyperclip.copy(text)
            messagebox.showinfo("コピー完了", "プロンプトをクリップボードにコピーしました！")

    def reset_output(self):
        """出力欄をリセット"""
        self.output_text.delete("1.0", tk.END)

    def save_prompt(self):
        """現在の入力状態を保存（保存名付き）"""
        # 既存の保存データを読み込み（なければ空リスト）
        try:
            with open(SAVE_FILE, "r") as file:
                saves = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            saves = []

        # 入力された保存名（空なら自動付番）
        title = self.save_name_entry.get().strip()
        if not title:
            title = f"保存{len(saves) + 1}"

        save_data = {
            "title": title,
            "fixed": [entry.get() for entry in self.fixed_entries],
            "variables": [[entry.get() for entry in entries] for _, entries, _ in self.variable_entries]
        }

        saves.insert(0, save_data)
        saves = saves[:MAX_SAVES]  # 最大50個に制限

        with open(SAVE_FILE, "w") as file:
            json.dump(saves, file, indent=4)

        self.update_save_list()
        messagebox.showinfo("保存完了", f"プロンプトを「{title}」として保存しました！")

    def update_save_list(self):
        """保存リストを更新（保存名を表示）"""
        try:
            with open(SAVE_FILE, "r") as file:
                saves = json.load(file)
            # セーブ名（title）をコンボボックスに設定
            self.save_list["values"] = [save.get("title", f"保存{i+1}") for i, save in enumerate(saves)]
        except (FileNotFoundError, json.JSONDecodeError):
            self.save_list["values"] = []

    def load_prompt(self):
        """選択したプロンプトをロード"""
        try:
            with open(SAVE_FILE, "r") as file:
                saves = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            messagebox.showerror("エラー", "保存データが見つかりません")
            return

        selected_title = self.save_list.get()
        if not selected_title:
            messagebox.showerror("エラー", "ロードする保存データを選択してください")
            return

        # 保存データからタイトルが一致するものを検索
        for save in saves:
            if save.get("title") == selected_title:
                save_data = save
                break
        else:
            messagebox.showerror("エラー", "選択された保存データが見つかりません")
            return

        # 現在のUIの固定部分、可変部分を全て削除
        for entry in self.fixed_entries:
            entry.destroy()
        self.fixed_entries.clear()
        for frame, _, _ in self.variable_entries:
            frame.destroy()
        self.variable_entries.clear()

        # 固定部分を再構築
        for text in save_data.get("fixed", []):
            entry = tk.Entry(self.fixed_frame, width=30)
            entry.pack(side=tk.LEFT, padx=5)
            entry.insert(0, text)
            self.fixed_entries.append(entry)
        # 少なくとも１つは残す
        if not self.fixed_entries:
            self.add_fixed_entry()

        # 可変部分を再構築
        for var_list in save_data.get("variables", []):
            frame = tk.Frame(self.variable_frame)
            tk.Label(frame, text=f"可変 {len(self.variable_entries) + 1}:").pack(anchor="w")

            entry_frame = tk.Frame(frame)
            entry_frame.pack(anchor="w", fill="x")
            entries = []
            # 各エントリーを作成
            for txt in var_list:
                entry = tk.Entry(entry_frame, width=15)
                entry.pack(side=tk.LEFT, padx=5)
                entry.insert(0, txt)
                entries.append(entry)
            # もし空なら１つ作成
            if not entries:
                self.add_variable_entry(entries, entry_frame)

            btn_frame = tk.Frame(frame)
            btn_frame.pack(anchor="w")
            tk.Button(btn_frame, text="+", command=lambda e=entries, ef=entry_frame: self.add_variable_entry(e, ef)).pack(side=tk.LEFT, padx=2)
            tk.Button(btn_frame, text="-", command=lambda e=entries, ef=entry_frame: self.remove_variable_entry(e, ef)).pack(side=tk.LEFT, padx=2)

            frame.pack(fill="x", pady=5)
            self.variable_entries.append((frame, entries, entry_frame))

        messagebox.showinfo("ロード完了", f"「{selected_title}」の設定をロードしました！")

# メイン処理
if __name__ == "__main__":
    root = tk.Tk()
    app = PromptGeneratorApp(root)
    root.mainloop()
