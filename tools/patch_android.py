"""Patch the generated Flutter project so flet-android-notifications can build (EXPERIMENTAL notifications build only).

Run after a first `flet build apk` has generated build/flutter (that first build may fail in Gradle - that is expected):

    python tools/patch_android.py

1. enables core library desugaring in build/flutter/android/app/build.gradle.kts
2. adds the scheduled-notification receivers to AndroidManifest.xml
Both edits are idempotent.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "build" / "flutter" / "android" / "app"
GRADLE = ROOT / "build.gradle.kts"
MANIFEST = ROOT / "src" / "main" / "AndroidManifest.xml"

RECEIVERS = """
        <receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver" />
        <receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationBootReceiver">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />
                <action android:name="android.intent.action.QUICKBOOT_POWERON" />
                <action android:name="com.htc.intent.action.QUICKBOOT_POWERON" />
            </intent-filter>
        </receiver>
"""


def patch_gradle() -> None:
    text = GRADLE.read_text(encoding="utf-8")
    if "isCoreLibraryDesugaringEnabled" not in text:
        new, n = re.subn(r"(compileOptions\s*\{)", r"\1\n        isCoreLibraryDesugaringEnabled = true", text, count=1)
        if n == 0:
            sys.exit("compileOptions block not found in build.gradle.kts - patch it by hand (see the plugin's README)")
        text = new
    if "desugar_jdk_libs" not in text:
        text += '\n\ndependencies {\n    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")\n}\n'
    GRADLE.write_text(text, encoding="utf-8")
    print("patched", GRADLE)


def patch_manifest() -> None:
    text = MANIFEST.read_text(encoding="utf-8")
    if "ScheduledNotificationReceiver" not in text:
        if "</application>" not in text:
            sys.exit("</application> not found in AndroidManifest.xml")
        text = text.replace("</application>", RECEIVERS + "    </application>", 1)
    MANIFEST.write_text(text, encoding="utf-8")
    print("patched", MANIFEST)


if __name__ == "__main__":
    if not GRADLE.is_file() or not MANIFEST.is_file():
        sys.exit("build/flutter was not generated yet - run `flet build apk` once first")
    patch_gradle()
    patch_manifest()
