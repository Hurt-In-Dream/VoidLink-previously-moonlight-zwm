import hashlib
import json
import plistlib
import re
import sys
import zipfile
from pathlib import Path


def verify_ipa(ipa_path: Path) -> None:
    app_path = "Payload/VoidLink.app/"
    with zipfile.ZipFile(ipa_path) as archive:
        corrupt_file = archive.testzip()
        if corrupt_file is not None:
            raise ValueError(f"IPA 文件校验失败：{corrupt_file}")

        info = plistlib.loads(archive.read(f"{app_path}Info.plist"))
        if "iPhoneOS" not in info["CFBundleSupportedPlatforms"]:
            raise ValueError("IPA 未面向 iOS 真机编译")
        if info["CFBundleIdentifier"] != "com.voidlink.tf.iOS":
            raise ValueError("IPA 的 Bundle ID 与 iOS Release 目标不一致")
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){0,2}", info["CFBundleVersion"]):
            raise ValueError("IPA 的构建版本号不符合安装要求")
        if not {1, 2}.issubset(info["UIDeviceFamily"]):
            raise ValueError("IPA 未同时支持 iPhone 和 iPad")

        executable = archive.getinfo(f"{app_path}{info['CFBundleExecutable']}")
        if executable.file_size == 0:
            raise ValueError("IPA 中的应用可执行文件为空")
        for name in archive.namelist():
            if name.startswith(app_path) and (
                "_CodeSignature" in Path(name).parts
                or name.endswith("/embedded.mobileprovision")
            ):
                raise ValueError(f"IPA 包含签名资料：{name}")

    digest = hashlib.sha256(ipa_path.read_bytes()).hexdigest()
    ipa_path.with_suffix(".ipa.sha256").write_text(
        f"{digest}  {ipa_path.name}\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "文件": ipa_path.name,
                "应用版本": info["CFBundleShortVersionString"],
                "构建编号": info["CFBundleVersion"],
                "Bundle ID": info["CFBundleIdentifier"],
                "最低 iOS 版本": info["MinimumOSVersion"],
                "大小": ipa_path.stat().st_size,
                "SHA256": digest,
                "签名状态": "未签名",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    verify_ipa(Path(sys.argv[1]))
