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
PRESET_FILE = Path(__file__).with_name("presets.json")


def normalize_hotkey_name(name):
    if name is None:
        return "F2"
    text = str(name).strip().upper()
    if text.startswith("KEY."):
        text = text.replace("KEY.", "")
    if text.startswith("F") and text[1:].isdigit():
        return text
    return text


class MacroActionEditor:
    def __init__(self, parent, action):
        self.parent = parent
        self.frame = ttk.Frame(parent.action_container)
        self.frame.pack(fill="x", pady=(0, 6))
        self.action = action
        self.type_var = tk.StringVar(value=action.get("type", "move"))

        ttk.Label(self.frame, text="유형").pack(side="left", padx=(0, 6))
        ttk.Combobox(
            self.frame,
            textvariable=self.type_var,
            values=["move", "click", "delay"],
            state="readonly",
            width=10,
        ).pack(side="left", padx=(0, 6))

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
            ttk.Button(self.fields_frame, text="현재 좌표", command=self.capture_position).pack(side="left", padx=(0, 8))
            ttk.Label(self.fields_frame, text="move_ms").pack(side="left")
            ttk.Entry(self.fields_frame, textvariable=self.duration_var, width=8).pack(side="left", padx=(4, 0))
            return

        if action_type == "click":
            ttk.Label(self.fields_frame, text="버튼").pack(side="left")
            ttk.Combobox(
                self.fields_frame,
                textvariable=self.button_var,
                values=["left", "right", "middle"],
                state="readonly",
                width=8,
            ).pack(side="left", padx=(4, 8))
            ttk.Label(self.fields_frame, text="횟수").pack(side="left")
            ttk.Entry(self.fields_frame, textvariable=self.count_var, width=6).pack(side="left", padx=(4, 0))
            return

        ttk.Label(self.fields_frame, text="딜레이(ms)").pack(side="left")
        ttk.Entry(self.fields_frame, textvariable=self.ms_var, width=8).pack(side="left", padx=(4, 0))

    def capture_position(self):
        self.parent.capture_position_for_editor(self)

    def remove_self(self):
        self.frame.destroy()
        self.parent.remove_action_editor(self)

    def to_dict(self):
        action_type = self.type_var.get()
        if action_type == "move":
            return {
                "type": "move",
                "x": int(self.x_var.get()),
                "y": int(self.y_var.get()),
                "duration_ms": int(self.duration_var.get() or 0),
            }
        if action_type == "click":
            return {
                "type": "click",
                "button": self.button_var.get(),
                "count": int(self.count_var.get() or 1),
            }
        return {"type": "delay", "ms": int(self.ms_var.get() or 0)}


class MouseMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mouse Macro UI")
        self.root.geometry("900x700")
        self.root.minsize(760, 520)

        self.running = threading.Event()
        self.thread = None
        self.keyboard_listener = None
        self.capture_listener = None
        self.capture_editor = None
        self.preset_name_var = tk.StringVar(value="preset_1")
        self.hotkey_var = tk.StringVar(value="F2")
        self.preset_list = {}

        self.load_presets()

        main = ttk.Frame(root, padding=12)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(top, text="반복 횟수").pack(side="left")
        self.repeat_var = tk.StringVar(value="3")
        ttk.Entry(top, textvariable=self.repeat_var, width=8).pack(side="left", padx=(6, 12))

        ttk.Label(top, text="시작 전 딜레이(ms)").pack(side="left")
        self.start_delay_var = tk.StringVar(value="1000")
        ttk.Entry(top, textvariable=self.start_delay_var, width=10).pack(side="left", padx=(6, 12))

        ttk.Button(top, text="시작", command=self.start_macro).pack(side="left", padx=(0, 8))
        ttk.Button(top, text="중지", command=self.stop_macro).pack(side="left")

        self.status_var = tk.StringVar(value="대기 중")
        ttk.Label(top, textvariable=self.status_var, foreground="darkblue").pack(side="right")

        preset_panel = ttk.LabelFrame(main, text="프리셋")
        preset_panel.pack(fill="x", pady=(0, 10))
        pp = ttk.Frame(preset_panel, padding=10)
        pp.pack(fill="x")

        ttk.Label(pp, text="이름").pack(side="left")
        ttk.Entry(pp, textvariable=self.preset_name_var, width=16).pack(side="left", padx=(6, 10))
        ttk.Button(pp, text="프리셋 저장", command=self.save_preset).pack(side="left", padx=(0, 8))
        ttk.Button(pp, text="프리셋 불러오기", command=self.load_selected_preset).pack(side="left", padx=(0, 8))
        ttk.Button(pp, text="프리셋 삭제", command=self.delete_selected_preset).pack(side="left")

        self.preset_box = tk.Listbox(pp, height=8, width=20)
        self.preset_box.pack(side="right", fill="y", padx=(10, 0))

        hotkey_panel = ttk.LabelFrame(main, text="단축키")
        hotkey_panel.pack(fill="x", pady=(0, 10))
        hp = ttk.Frame(hotkey_panel, padding=10)
        hp.pack(fill="x")

        ttk.Label(hp, text="시작/중지 단축키").pack(side="left")
        ttk.Entry(hp, textvariable=self.hotkey_var, width=10).pack(side="left", padx=(6, 10))
        ttk.Button(hp, text="적용", command=self.apply_hotkey).pack(side="left")
        ttk.Label(hp, text="기본값: F2", foreground="gray").pack(side="left", padx=(12, 0))

        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="+ 이동 추가", command=lambda: self.add_action({"type": "move", "x": 0, "y": 0, "duration_ms": 0})).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="+ 클릭 추가", command=lambda: self.add_action({"type": "click", "button": "left", "count": 1})).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="+ 딜레이 추가", command=lambda: self.add_action({"type": "delay", "ms": 500})).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="JSON 저장", command=self.save_json).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="JSON 불러오기", command=self.load_json).pack(side="left")

        action_panel = ttk.LabelFrame(main, text="매크로 액션")
        action_panel.pack(fill="both", expand=True)

        self.action_container = ttk.Frame(action_panel, padding=8)
        self.action_container.pack(fill="both", expand=True)

        self.action_editors = []
        self.add_action({"type": "move", "x": 100, "y": 200, "duration_ms": 200})
        self.add_action({"type": "click", "button": "left", "count": 1})
        self.add_action({"type": "delay", "ms": 500})

        self.refresh_preset_list()
        self.apply_hotkey()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def add_action(self, action):
        editor = MacroActionEditor(self, action)
        self.action_editors.append(editor)

    def remove_action_editor(self, editor):
        self.action_editors = [item for item in self.action_editors if item is not editor]

    def refresh_preset_list(self):
        if not hasattr(self, "preset_box"):
            return
        self.preset_box.delete(0, tk.END)
        preset_map = self.preset_list if isinstance(self.preset_list, dict) else {}
        for name in sorted(preset_map.keys()):
            self.preset_box.insert(tk.END, name)

    def load_presets(self):
        if not PRESET_FILE.exists():
            self.preset_list = {}
            return
        try:
            data = json.loads(PRESET_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.preset_list = data.get("presets", {}) if isinstance(data.get("presets", {}), dict) else {}
            else:
                self.preset_list = {}
        except Exception:
            self.preset_list = {}

    def save_presets(self):
        payload = {"presets": self.preset_list if isinstance(self.preset_list, dict) else {}}
        PRESET_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_preset(self):
        name = self.preset_name_var.get().strip()
        if not name:
            messagebox.showwarning("경고", "프리셋 이름을 입력해 주세요.")
            return
        self.preset_list[name] = {
            "repeat": max(1, int(self.repeat_var.get() or 1)),
            "actions": self.get_actions(),
        }
        self.save_presets()
        self.refresh_preset_list()
        self.status_var.set(f"프리셋 저장: {name}")

    def load_selected_preset(self):
        selected = self.preset_box.curselection()
        if not selected:
            messagebox.showwarning("경고", "불러올 프리셋을 선택해 주세요.")
            return
        name = self.preset_box.get(selected[0])
        preset = self.preset_list.get(name)
        if preset is None:
            messagebox.showwarning("경고", f"프리셋을 찾을 수 없습니다: {name}")
            return

        for editor in list(self.action_editors):
            editor.remove_self()

        self.repeat_var.set(str(preset.get("repeat", 1)))
        for action in preset.get("actions", []):
            self.add_action(action)
        self.preset_name_var.set(name)
        self.status_var.set(f"프리셋 불러오기: {name}")

    def delete_selected_preset(self):
        selected = self.preset_box.curselection()
        if not selected:
            messagebox.showwarning("경고", "삭제할 프리셋을 선택해 주세요.")
            return
        name = self.preset_box.get(selected[0])
        self.preset_list.pop(name, None)
        self.save_presets()
        self.refresh_preset_list()
        self.status_var.set(f"프리셋 삭제: {name}")

    def get_actions(self):
        return [editor.to_dict() for editor in self.action_editors]

    def capture_position_for_editor(self, editor):
        self.capture_editor = editor
        self.status_var.set("좌표 캡처 중: 화면에서 원하는 지점을 클릭하세요.")
        if self.capture_listener is not None:
            self.capture_listener.stop()
        self.capture_listener = mouse.Listener(on_click=self._on_capture_click)
        self.capture_listener.start()

    def _on_capture_click(self, x, y, button, pressed):
        if not pressed or self.capture_editor is None:
            return
        self.root.after(0, lambda: self._apply_captured_position(x, y))
        if self.capture_listener is not None:
            self.capture_listener.stop()
            self.capture_listener = None

    def _apply_captured_position(self, x, y):
        if self.capture_editor is not None:
            self.capture_editor.x_var.set(str(int(x)))
            self.capture_editor.y_var.set(str(int(y)))
            self.capture_editor = None
            self.status_var.set("좌표 설정 완료")

    def stop_capture_listener(self):
        if self.capture_listener is not None:
            self.capture_listener.stop()
            self.capture_listener = None
        self.capture_editor = None

    def _normalize_hotkey(self, key_name):
        value = (key_name or "").strip().upper()
        if not value:
            return "F2"
        if value.startswith("KEY."):
            value = value.replace("KEY.", "")
        return value

    def apply_hotkey(self):
        self.stop_hotkey_listener()
        hotkey = self._normalize_hotkey(self.hotkey_var.get())
        self.hotkey_var.set(hotkey)
        try:
            self.keyboard_listener = keyboard.Listener(on_press=self._on_hotkey_press)
            self.keyboard_listener.start()
            self.status_var.set(f"단축키 적용: {hotkey}")
        except Exception as exc:
            messagebox.showerror("오류", f"단축키 등록 실패: {exc}")

    def stop_hotkey_listener(self):
        if self.keyboard_listener is not None:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def _on_hotkey_press(self, key):
        try:
            key_name = key.char if hasattr(key, "char") and key.char else str(key).replace("'", "")
        except Exception:
            key_name = str(key).replace("'", "")
        target = self._normalize_hotkey(self.hotkey_var.get())
        if key_name.upper() == target:
            self.root.after(0, self.toggle_macro)
            return False
        return True

    def toggle_macro(self):
        if self.thread and self.thread.is_alive():
            self.stop_macro()
        else:
            self.start_macro()

    def start_macro(self):
        if self.thread and self.thread.is_alive():
            messagebox.showinfo("알림", "이미 매크로가 실행 중입니다.")
            return

        actions = self.get_actions()
        if not actions:
            messagebox.showwarning("경고", "액션이 하나 이상 있어야 합니다.")
            return

        try:
            repeat = max(1, int(self.repeat_var.get()))
            start_delay_ms = max(0, int(self.start_delay_var.get()))
        except ValueError:
            messagebox.showerror("오류", "반복 횟수와 시작 딜레이는 숫자여야 합니다.")
            return

        self.running.set()
        self.status_var.set("실행 중")
        self.thread = threading.Thread(
            target=self._run_macro,
            args=(actions, repeat, start_delay_ms),
            daemon=True,
        )
        self.thread.start()

    def stop_macro(self):
        self.running.clear()
        self.status_var.set("중지 요청")

    def _run_macro(self, actions, repeat, start_delay_ms):
        controller = mouse.Controller()
        try:
            if start_delay_ms > 0:
                time.sleep(start_delay_ms / 1000.0)

            for loop_index in range(1, repeat + 1):
                if not self.running.is_set():
                    self.status_var.set("중지됨")
                    return

                for action in actions:
                    if not self.running.is_set():
                        self.status_var.set("중지됨")
                        return

                    action_type = action["type"]
                    if action_type == "move":
                        controller.position = (int(action["x"]), int(action["y"]))
                        duration_ms = int(action.get("duration_ms", 0) or 0)
                        if duration_ms > 0:
                            time.sleep(duration_ms / 1000.0)
                    elif action_type == "click":
                        button_name = action.get("button", "left")
                        button = VALID_BUTTONS.get(str(button_name).lower(), mouse.Button.left)
                        count = max(1, int(action.get("count", 1) or 1))
                        controller.click(button, count=count)
                    elif action_type == "delay":
                        delay_ms = max(0, int(action.get("ms", 0) or 0))
                        if delay_ms > 0:
                            time.sleep(delay_ms / 1000.0)
                    else:
                        raise ValueError(f"지원하지 않는 액션: {action_type}")

                self.status_var.set(f"{loop_index}/{repeat} 반복 완료")

            self.status_var.set("완료")
        except Exception as exc:
            self.status_var.set(f"오류: {exc}")
            messagebox.showerror("매크로 오류", str(exc))
        finally:
            self.running.clear()

    def save_json(self):
        actions = self.get_actions()
        data = {"repeat": max(1, int(self.repeat_var.get() or 1)), "actions": actions}
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="macro.json",
            title="매크로 저장",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return
        Path(file_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo("저장 완료", f"저장됨: {file_path}")

    def load_json(self):
        file_path = filedialog.askopenfilename(
            title="매크로 불러오기",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            data = json.loads(Path(file_path).read_text(encoding="utf-8"))
            actions = data.get("actions", [])
            if not isinstance(actions, list):
                raise ValueError("actions는 배열이어야 합니다.")
            for editor in list(self.action_editors):
                editor.remove_self()
            self.repeat_var.set(str(data.get("repeat", 1)))
            for action in actions:
                self.add_action(action)
            self.status_var.set("불러오기 완료")
        except Exception as exc:
            messagebox.showerror("오류", f"불러오기 실패: {exc}")

    def on_close(self):
        self.stop_hotkey_listener()
        self.stop_capture_listener()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MouseMacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
