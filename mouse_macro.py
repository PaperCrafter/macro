#!/usr/bin/env python3
import argparse
import json
import sys
import time
from pathlib import Path

from pynput import mouse


VALID_BUTTONS = {
    "left": mouse.Button.left,
    "right": mouse.Button.right,
    "middle": mouse.Button.middle,
}


def _button_from_name(button_name):
    if button_name is None:
        return mouse.Button.left
    name = str(button_name).strip().lower()
    if name in VALID_BUTTONS:
        return VALID_BUTTONS[name]
    if hasattr(mouse.Button, name):
        return getattr(mouse.Button, name)
    raise ValueError(f"지원하지 않는 버튼: {button_name}")


def _delay_ms(value, action_name):
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{action_name}의 딜레이 값이 올바르지 않습니다: {value}") from exc


def _load_macro(path: str | Path):
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"매크로 파일을 찾을 수 없습니다: {file_path}")

    data = json.loads(file_path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        actions = data
        repeat = 1
    elif isinstance(data, dict):
        actions = data.get("actions")
        if actions is None:
            raise ValueError("매크로 JSON에 'actions' 배열이 없습니다.")
        repeat = int(data.get("repeat", 1))
    else:
        raise ValueError("매크로 형식이 올바르지 않습니다. JSON 배열 또는 객체를 사용하세요.")

    if not isinstance(actions, list):
        raise ValueError("actions는 배열이어야 합니다.")

    return {"repeat": max(1, repeat), "actions": actions}


def _run_action(controller, action: dict):
    action_type = str(action.get("type", "")).lower()

    if action_type in {"sleep", "delay"}:
        ms = _delay_ms(action.get("ms", action.get("delay_ms", 0)), "delay")
        if ms > 0:
            time.sleep(ms / 1000.0)
        return

    if action_type == "move":
        x = int(action["x"])
        y = int(action["y"])
        duration_ms = _delay_ms(action.get("duration_ms", action.get("duration", 0)), "move")
        controller.position = (x, y)
        if duration_ms > 0:
            time.sleep(duration_ms / 1000.0)
        return

    if action_type == "click":
        button_name = action.get("button", "left")
        count = max(1, int(action.get("count", 1)))
        button = _button_from_name(button_name)
        controller.click(button, count=count)
        return

    if action_type == "press":
        button_name = action.get("button", "left")
        controller.press(_button_from_name(button_name))
        return

    if action_type == "release":
        button_name = action.get("button", "left")
        controller.release(_button_from_name(button_name))
        return

    if action_type == "move_relative":
        dx = int(action.get("dx", 0))
        dy = int(action.get("dy", 0))
        current_x, current_y = controller.position
        controller.position = (current_x + dx, current_y + dy)
        return

    raise ValueError(f"지원하지 않는 액션 타입: {action_type}")


def run_macro(path: str | Path, repeat_override: int | None = None, start_delay_ms: int = 0):
    macro = _load_macro(path)
    repeat = repeat_override if repeat_override is not None else macro["repeat"]
    repeat = max(1, repeat)

    if start_delay_ms > 0:
        print(f"시작 전 대기: {start_delay_ms}ms")
        time.sleep(start_delay_ms / 1000.0)

    controller = mouse.Controller()
    total_steps = len(macro["actions"]) * repeat
    print(f"매크로 실행 시작: {path}")
    print(f"반복 횟수: {repeat}회 | 액션 수: {len(macro['actions'])} | 총 단계: {total_steps}")

    for loop_index in range(1, repeat + 1):
        print(f"[{loop_index}/{repeat}] 반복 중")
        for action_index, action in enumerate(macro["actions"], start=1):
            print(f"  - {action_index}. {action.get('type', 'unknown')} -> {action}")
            _run_action(controller, action)

    print("매크로 실행 완료")


def create_example_template(path: str | Path):
    template = {
        "repeat": 3,
        "actions": [
            {"type": "move", "x": 100, "y": 200, "duration_ms": 200},
            {"type": "click", "button": "left", "count": 1},
            {"type": "delay", "ms": 500},
            {"type": "move", "x": 400, "y": 300},
            {"type": "click", "button": "right", "count": 1},
            {"type": "delay", "ms": 1000},
        ],
    }

    file_path = Path(path)
    file_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"템플릿 생성 완료: {file_path}")
    print("예시:")
    print(json.dumps(template, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="실행형 마우스 매크로: 이동, 클릭, 딜레이를 순서대로 배치하고 반복합니다.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="매크로 실행")
    run_parser.add_argument("--macro", required=True, help="매크로 JSON 파일 경로")
    run_parser.add_argument("--loop", type=int, default=None, help="JSON repeat를 덮어쓰고 지정 횟수만큼 반복합니다")
    run_parser.add_argument("--start-delay-ms", type=int, default=0, help="시작 전 딜레이 (밀리초)")

    template_parser = subparsers.add_parser("create-template", help="예제 매크로 JSON 파일 생성")
    template_parser.add_argument("--output", default="macro.json", help="생성할 파일 경로")

    args = parser.parse_args()

    if args.command == "run":
        run_macro(args.macro, repeat_override=args.loop, start_delay_ms=args.start_delay_ms)
        return 0

    if args.command == "create-template":
        create_example_template(args.output)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n사용자가 중단했습니다.")
        raise SystemExit(0)
    except Exception as exc:  # pragma: no cover
        print(f"오류: {exc}", file=sys.stderr)
        raise SystemExit(1)
