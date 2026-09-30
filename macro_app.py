#!/usr/bin/env python3
import json
import threading
import time
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
import tkinter as tk

from pynput import keyboard, mouse


VALID_BUTTONS = {
    "left": mouse.Button.left,
    "right": mouse.Button.right,
    "middle": mouse.Button.middle,
}
PRESET_FILE = Path.home() / ".mouse_macro_presets.json"


class MacroActionEditor:
    def __init__(self, parent, action, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", pady=(0, 6))
        self.type_var = tk.StringVar(value=action.get("type", "move"))

        # 위/아래 이동 버튼
        move_btn_frame = ttk.Frame(self.frame)
        move_btn_frame.pack(side="left", padx=(0, 6))
        ttk.Button(move_btn_frame, text="↑", width=2, command=self.move_up).pack(side="left", padx=(0, 2))
        ttk.Button(move_btn_frame, text="↓", width=2, command=self.move_down).pack(side="left")

        ttk.Label(self.frame, text="유형").pack(side="left", padx=(0, 6))
        ttk.Combobox(self.frame, textvariable=self.type_var, values=["move", "click", "delay"], state="readonly", width=10).pack(side="left", padx=(0, 6))

        self.x_var = tk.StringVar(value=str(action.get("x", 0)))
        self.y_var = tk.StringVar(value=str(action.get("y", 0)))
        self.button_var = tk.StringVar(value=str(action.get("button", "left")))
        self.count_var = tk.StringVar(value=str(action.get("count", 1)))
        self.ms_var = tk.StringVar(value=str(action.get("ms", 500)))
        self.duration_var = tk.StringVar(value=str(action.get("duration_ms", 0)))

        self.fields_frame = ttk.Frame(self.frame)
        self.fields_frame.pack(side="left", fill="x", expand=True)
        self._refresh_fields()

        ttk.Button(self.frame, text="삭제", command=self.remove_self).pack(side="right")
        self.type_var.trace_add("write", lambda *_: self._refresh_fields())

    def _refresh_fields(self):
        for child in self.fields_frame.winfo_children():
            child.destroy()

        action_type = self.type_var.get()

        if action_type == "move":
            ttk.Label(self.fields_frame, text="x").pack(side="left")
            ttk.Entry(self.fields_frame, textvariable=self.x_var, width=7).pack(side="left", padx=(4, 8))
            ttk.Label(self.fields_frame, text="y").pack(side="left")
            ttk.Entry(self.fields_frame, textvariable=self.y_var, width=7).pack(side="left", padx=(4, 8))
            ttk.Button(self.fields_frame, text="캡처", command=self.start_capture).pack(side="left", padx=(0, 8))
            ttk.Label(self.fields_frame, text="ms").pack(side="left")
            ttk.Entry(self.fields_frame, textvariable=self.duration_var, width=8).pack(side="left", padx=(4, 0))
            return

        if action_type == "click":
            ttk.Label(self.fields_frame, text="버튼").pack(side="left")
            ttk.Combobox(self.fields_frame, textvariable=self.button_var, values=["left", "right", "middle"], state="readonly", width=8).pack(side="left", padx=(4, 8))
            ttk.Label(self.fields_frame, text="횟수").pack(side="left")
            ttk.Entry(self.fields_frame, textvariable=self.count_var, width=6).pack(side="left", padx=(4, 0))
            return

        ttk.Label(self.fields_frame, text="ms").pack(side="left")
        ttk.Entry(self.fields_frame, textvariable=self.ms_var, width=8).pack(side="left", padx=(4, 0))

    def start_capture(self):
        self.app.capture_position_for_editor(self)

    def remove_self(self):
        self.frame.destroy()
        self.app.remove_action_editor(self)

    def move_up(self):
        self.app.move_action_up(self)

    def move_down(self):
        self.app.move_action_down(self)

    def to_dict(self):
        action_type = self.type_var.get()
        if action_type == "move":
            return {"type": "move", "x": int(self.x_var.get() or 0), "y": int(self.y_var.get() or 0), "duration_ms": int(self.duration_var.get() or 0)}
        if action_type == "click":
            return {"type": "click", "button": self.button_var.get(), "count": int(self.count_var.get() or 1)}
        return {"type": "delay", "ms": int(self.ms_var.get() or 0)}


class MouseMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mouse Macro")
        self.root.geometry("950x750")
        self.root.minsize(800, 550)

        self.running = threading.Event()
        self.thread = None
        self.keyboard_listener = None
        self.capture_listener = None
        self.capture_editor = None
        self.preset_name_var = tk.StringVar(value="preset_1")
        self.hotkey_var = tk.StringVar(value="F2")
        self.preset_dict = {}

        self.load_presets()

        main = ttk.Frame(root, padding=12)
        main.pack(fill="both", expand=True)

        # Top control panel
        top_frame = ttk.Frame(main)
        top_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(top_frame, text="반복").pack(side="left")
        self.repeat_var = tk.StringVar(value="1")
        ttk.Entry(top_frame, textvariable=self.repeat_var, width=6).pack(side="left", padx=(6, 12))

        ttk.Label(top_frame, text="시작 딜레이(ms)").pack(side="left")
        self.start_delay_var = tk.StringVar(value="1000")
        ttk.Entry(top_frame, textvariable=self.start_delay_var, width=10).pack(side="left", padx=(6, 12))

        ttk.Button(top_frame, text="▶ 실행", command=self.start_macro).pack(side="left", padx=(0, 8))
        ttk.Button(top_frame, text="⏹ 중지", command=self.stop_macro).pack(side="left")

        self.status_var = tk.StringVar(value="준비 중")
        ttk.Label(top_frame, textvariable=self.status_var, foreground="darkblue", font=("", 10, "bold")).pack(side="right")

        # Preset panel
        preset_frame = ttk.LabelFrame(main, text="프리셋")
        preset_frame.pack(fill="x", pady=(0, 10))
        pf = ttk.Frame(preset_frame, padding=10)
        pf.pack(fill="x")

        ttk.Label(pf, text="이름").pack(side="left")
        ttk.Entry(pf, textvariable=self.preset_name_var, width=16).pack(side="left", padx=(6, 10))
        ttk.Button(pf, text="💾 저장", command=self.save_preset).pack(side="left", padx=(0, 6))
        ttk.Button(pf, text="📂 열기", command=self.load_selected_preset).pack(side="left", padx=(0, 6))
        ttk.Button(pf, text="🗑 삭제", command=self.delete_selected_preset).pack(side="left")

        self.preset_box = tk.Listbox(pf, height=6, width=24)
        self.preset_box.pack(side="right", padx=(10, 0), fill="y")

        # Hotkey panel
        hotkey_frame = ttk.LabelFrame(main, text="단축키")
        hotkey_frame.pack(fill="x", pady=(0, 10))
        hf = ttk.Frame(hotkey_frame, padding=10)
        hf.pack(fill="x")

        ttk.Label(hf, text="시작/중지").pack(side="left")
        ttk.Entry(hf, textvariable=self.hotkey_var, width=10).pack(side="left", padx=(6, 10))
        ttk.Button(hf, text="적용", command=self.apply_hotkey).pack(side="left")

        # Toolbar
        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 10))

        # 추가 메뉴버튼
        add_menu = tk.Menu(toolbar, tearoff=False)
        add_menu.add_command(label="이동", command=lambda: self.add_action({"type": "move", "x": 0, "y": 0, "duration_ms": 0}))
        add_menu.add_command(label="클릭", command=lambda: self.add_action({"type": "click", "button": "left", "count": 1}))
        add_menu.add_command(label="딜레이", command=lambda: self.add_action({"type": "delay", "ms": 500}))
        add_btn = ttk.Menubutton(toolbar, text="➕ 추가", menu=add_menu)
        add_btn.pack(side="left", padx=(0, 6))

        ttk.Button(toolbar, text="💾 JSON 저장", command=self.save_json).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="📂 JSON 열기", command=self.load_json).pack(side="left")

        # Action list
        action_frame = ttk.LabelFrame(main, text="액션")
        action_frame.pack(fill="both", expand=True)

        self.action_container = ttk.Frame(action_frame, padding=8)
        self.action_container.pack(fill="both", expand=True)

        self.action_editors = []
        self.add_action({"type": "move", "x": 100, "y": 200, "duration_ms": 0})
        self.add_action({"type": "click", "button": "left", "count": 1})
        self.add_action({"type": "delay", "ms": 500})

        self.refresh_preset_list()
        self.apply_hotkey()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.stop_hotkey_listener()
        self.stop_capture_listener()
        self.root.destroy()

    def stop_hotkey_listener(self):
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except:
                pass
            self.keyboard_listener = None

    def stop_capture_listener(self):
        if self.capture_listener:
            try:
                self.capture_listener.stop()
            except:
                pass
            self.capture_listener = None
        self.capture_editor = None

    def apply_hotkey(self):
        self.stop_hotkey_listener()
        hotkey = (self.hotkey_var.get() or "F2").strip().upper()
        self.hotkey_var.set(hotkey)

        try:
            self.keyboard_listener = keyboard.Listener(on_press=self._on_hotkey_press)
            self.keyboard_listener.start()
            self.status_var.set(f"단축키: {hotkey}")
        except Exception as exc:
            messagebox.showerror("오류", f"단축키 실패: {exc}")

    def _on_hotkey_press(self, key):
        try:
            key_name = key.char if hasattr(key, "char") else str(key).replace("'", "")
        except:
            key_name = str(key).replace("'", "")

        target = (self.hotkey_var.get() or "F2").strip().upper()
        if key_name.upper() == target:
            self.root.after(0, self.toggle_macro)
        return True

    def toggle_macro(self):
        if self.thread and self.thread.is_alive():
            self.stop_macro()
        else:
            self.start_macro()

    def capture_position_for_editor(self, editor):
        self.capture_editor = editor
        self.status_var.set("⚠️ 클릭할 위치를 선택하세요")
        self.stop_capture_listener()
        self.capture_listener = mouse.Listener(on_click=self._on_capture_click)
        self.capture_listener.start()

    def _on_capture_click(self, x, y, button, pressed):
        if not pressed or self.capture_editor is None:
            return
        self.root.after(0, lambda: self._set_capture_coords(x, y))
        self.stop_capture_listener()

    def _set_capture_coords(self, x, y):
        if self.capture_editor:
            self.capture_editor.x_var.set(str(int(x)))
            self.capture_editor.y_var.set(str(int(y)))
            self.status_var.set("좌표 설정 완료")

    def add_action(self, action):
        editor = MacroActionEditor(self.action_container, action, self)
        self.action_editors.append(editor)

    def remove_action_editor(self, editor):
        self.action_editors = [e for e in self.action_editors if e is not editor]

    def move_action_up(self, editor):
        try:
            idx = self.action_editors.index(editor)
            if idx > 0:
                self.action_editors[idx], self.action_editors[idx - 1] = self.action_editors[idx - 1], self.action_editors[idx]
                self._rebuild_action_display()
        except (ValueError, IndexError):
            pass

    def move_action_down(self, editor):
        try:
            idx = self.action_editors.index(editor)
            if idx < len(self.action_editors) - 1:
                self.action_editors[idx], self.action_editors[idx + 1] = self.action_editors[idx + 1], self.action_editors[idx]
                self._rebuild_action_display()
        except (ValueError, IndexError):
            pass

    def _rebuild_action_display(self):
        """액션 에디터들의 frame 재배치"""
        for editor in self.action_editors:
            editor.frame.pack(fill="x", pady=(0, 6))

    def get_actions(self):
        return [e.to_dict() for e in self.action_editors]

    def start_macro(self):
        if self.thread and self.thread.is_alive():
            messagebox.showinfo("알림", "이미 실행 중입니다")
            return

        actions = self.get_actions()
        if not actions:
            messagebox.showwarning("경고", "액션을 추가하세요")
            return

        try:
            repeat = max(1, int(self.repeat_var.get()))
            delay = max(0, int(self.start_delay_var.get()))
        except ValueError:
            messagebox.showerror("오류", "숫자만 입력 가능합니다")
            return

        self.running.set()
        self.status_var.set("⏳ 시작 대기 중...")
        self.thread = threading.Thread(target=self._run_macro, args=(actions, repeat, delay), daemon=True)
        self.thread.start()

    def stop_macro(self):
        self.running.clear()
        self.status_var.set("⏹ 중지됨")

    def _run_macro(self, actions, repeat, start_delay):
        controller = mouse.Controller()

        try:
            if start_delay > 0:
                time.sleep(start_delay / 1000.0)

            for loop_idx in range(1, repeat + 1):
                if not self.running.is_set():
                    self.status_var.set("중지됨")
                    return

                for action in actions:
                    if not self.running.is_set():
                        return

                    atype = action["type"]
                    if atype == "move":
                        controller.position = (int(action["x"]), int(action["y"]))
                        ms = int(action.get("duration_ms", 0) or 0)
                        if ms > 0:
                            time.sleep(ms / 1000.0)
                    elif atype == "click":
                        btn = VALID_BUTTONS.get(action.get("button", "left").lower(), mouse.Button.left)
                        cnt = max(1, int(action.get("count", 1) or 1))
                        controller.click(btn, count=cnt)
                    elif atype == "delay":
                        ms = max(0, int(action.get("ms", 0) or 0))
                        if ms > 0:
                            time.sleep(ms / 1000.0)

                self.status_var.set(f"✓ {loop_idx}/{repeat}")

            self.status_var.set("✓ 완료")
        except Exception as exc:
            self.status_var.set(f"✗ 오류")
            messagebox.showerror("실행 오류", str(exc))
        finally:
            self.running.clear()

    def load_presets(self):
        if not PRESET_FILE.exists():
            self.preset_dict = {}
            return
        try:
            data = json.loads(PRESET_FILE.read_text(encoding="utf-8"))
            self.preset_dict = data.get("presets", {}) if isinstance(data, dict) else {}
        except:
            self.preset_dict = {}

    def save_presets(self):
        PRESET_FILE.write_text(json.dumps({"presets": self.preset_dict}, ensure_ascii=False, indent=2), encoding="utf-8")

    def refresh_preset_list(self):
        self.preset_box.delete(0, tk.END)
        for name in sorted(self.preset_dict.keys()):
            self.preset_box.insert(tk.END, name)

    def save_preset(self):
        name = self.preset_name_var.get().strip()
        if not name:
            messagebox.showwarning("경고", "이름 입력")
            return

        data = {"repeat": max(1, int(self.repeat_var.get() or 1)), "actions": self.get_actions()}
        self.preset_dict[name] = data
        self.save_presets()
        self.refresh_preset_list()
        self.status_var.set(f"저장: {name}")

    def load_selected_preset(self):
        sel = self.preset_box.curselection()
        if not sel:
            messagebox.showwarning("경고", "선택")
            return

        name = self.preset_box.get(sel[0])
        if name not in self.preset_dict:
            return

        preset = self.preset_dict[name]
        # 모든 액션 에디터 제거 (frame도 함께 제거됨)
        for editor in list(self.action_editors):
            editor.frame.destroy()
        self.action_editors = []

        self.repeat_var.set(str(preset.get("repeat", 1)))
        for action in preset.get("actions", []):
            new_editor = MacroActionEditor(self.action_container, action, self)
            self.action_editors.append(new_editor)

        self.preset_name_var.set(name)
        self.status_var.set(f"불러옴: {name}")

    def delete_selected_preset(self):
        sel = self.preset_box.curselection()
        if not sel:
            return

        name = self.preset_box.get(sel[0])
        self.preset_dict.pop(name, None)
        self.save_presets()
        self.refresh_preset_list()

    def save_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = {"repeat": max(1, int(self.repeat_var.get() or 1)), "actions": self.get_actions()}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo("저장", path)

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return

        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            # 모든 액션 에디터 제거
            for editor in list(self.action_editors):
                editor.frame.destroy()
            self.action_editors = []

            self.repeat_var.set(str(data.get("repeat", 1)))
            for action in data.get("actions", []):
                new_editor = MacroActionEditor(self.action_container, action, self)
                self.action_editors.append(new_editor)

            self.status_var.set("불러옴")
        except Exception as exc:
            messagebox.showerror("오류", str(exc))


def main():
    root = tk.Tk()
    app = MouseMacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
