#!/bin/bash
# macOS Mouse Macro 앱 빌드 스크립트

set -e

echo "🔨 Mouse Macro 앱 빌드 중..."

# 기존 빌드 디렉토리 정리
rm -rf dist build build_env

# .app 디렉토리 구조 생성
mkdir -p dist/Mouse\ Macro.app/Contents/{MacOS,Resources}

# launcher 스크립트 생성
cat > dist/Mouse\ Macro.app/Contents/MacOS/launcher << 'EOF'
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON="/usr/bin/python3"
SCRIPT="$DIR/../Resources/macro_app.py"
exec $PYTHON "$SCRIPT" "$@"
EOF

# launcher 실행 권한 설정
chmod +x dist/Mouse\ Macro.app/Contents/MacOS/launcher

# 소스 파일 복사
cp macro_app.py dist/Mouse\ Macro.app/Contents/Resources/

# Info.plist 생성
cat > dist/Mouse\ Macro.app/Contents/Info.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>en</string>
	<key>CFBundleExecutable</key>
	<string>launcher</string>
	<key>CFBundleIdentifier</key>
	<string>com.local.mousemacro</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>Mouse Macro</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0</string>
	<key>CFBundleVersion</key>
	<string>1</string>
	<key>NSPrincipalClass</key>
	<string>NSApplication</string>
</dict>
</plist>
EOF

echo "✅ 빌드 완료!"
echo ""
echo "실행 방법:"
echo "  open dist/Mouse\ Macro.app"
echo ""
echo "또는 Applications 폴더로 복사:"
echo "  cp -r dist/Mouse\ Macro.app ~/Applications/"
