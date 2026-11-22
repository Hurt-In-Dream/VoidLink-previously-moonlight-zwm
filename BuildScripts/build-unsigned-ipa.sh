#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
build_dir="$PWD/build"
build_number="${GITHUB_RUN_NUMBER:?缺少 GitHub Actions 构建编号}"
mkdir -p "$build_dir"

git rev-parse HEAD
xcodebuild archive \
  -project VoidLink.xcodeproj \
  -scheme VoidLink \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -derivedDataPath "$build_dir/DerivedData" \
  -archivePath "$build_dir/VoidLink.xcarchive" \
  -resultBundlePath "$build_dir/Archive.xcresult" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY='' \
  CODE_SIGN_ENTITLEMENTS='' \
  DEVELOPMENT_TEAM='' \
  CURRENT_PROJECT_VERSION="$build_number" \
  2>&1 | tee "$build_dir/xcodebuild.log"

app="$build_dir/VoidLink.xcarchive/Products/Applications/VoidLink.app"
plutil -lint "$app/Info.plist"
executable=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$app/Info.plist")
xcrun lipo "$app/$executable" -verify_arch arm64
if codesign -d "$app" >/dev/null 2>&1; then
  printf '%s\n' '应用包含代码签名，无法作为未签名 IPA 交付。' >&2
  exit 1
fi

mkdir -p "$build_dir/ipa/Payload"
ditto "$app" "$build_dir/ipa/Payload/VoidLink.app"
ditto -c -k --keepParent --norsrc "$build_dir/ipa/Payload" "$build_dir/VoidLink-unsigned.ipa"
python3 BuildScripts/verify-ipa.py "$build_dir/VoidLink-unsigned.ipa"
