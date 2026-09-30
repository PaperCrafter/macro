# Mouse Macro

이 프로젝트는 마우스 이동, 클릭, 딜레이를 원하는 순서대로 배치하고, 반복 실행할 수 있는 실행형 매크로를 제공합니다.

## 설치

```bash
cd /Users/paper/Projects/mouse_macro
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 1) 예제 매크로 파일 생성

```bash
python3 mouse_macro.py create-template --output macro.json
```

생성되는 JSON 예시:

```json
{
  "repeat": 3,
  "actions": [
    {"type": "move", "x": 100, "y": 200, "duration_ms": 200},
    {"type": "click", "button": "left", "count": 1},
    {"type": "delay", "ms": 500},
    {"type": "move", "x": 400, "y": 300},
    {"type": "click", "button": "right", "count": 1},
    {"type": "delay", "ms": 1000}
  ]
}
```

## 2) 실행

```bash
python3 mouse_macro.py run --macro macro.json
```

반복 수를 JSON 값 대신 옵션으로 덮어쓰기:

```bash
python3 mouse_macro.py run --macro macro.json --loop 10
```

시작 전 대기:

```bash
python3 mouse_macro.py run --macro macro.json --start-delay-ms 2000
```

## 3) 액션 종류

- `move`: 좌표 이동
  - 예: `{ "type": "move", "x": 500, "y": 300 }`
- `click`: 클릭
  - 예: `{ "type": "click", "button": "left", "count": 1 }`
- `delay`: 대기
  - 예: `{ "type": "delay", "ms": 800 }`
- `move_relative`: 상대 이동
  - 예: `{ "type": "move_relative", "dx": 20, "dy": 30 }`

## 4) 루프 반복

`repeat` 값을 설정하면 해당 횟수만큼 매크로가 반복됩니다.

예:

```json
{
  "repeat": 5,
  "actions": [
    {"type": "move", "x": 100, "y": 100},
    {"type": "click", "button": "left", "count": 1},
    {"type": "delay", "ms": 300}
  ]
}
```

이 경우 5번 반복합니다.

## 참고

- macOS에서 동작하려면 Accessibility 권한이 켜져 있어야 할 수 있습니다.
- 자동 입력은 사용 환경에 따라 제한될 수 있으니 주의해서 사용하세요.
