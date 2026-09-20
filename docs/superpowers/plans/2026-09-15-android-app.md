# CampusMeet Android App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a release-signed Android APK that presents the production CampusMeet experience as an installable mobile app.

**Architecture:** A dependency-light Java WebView application loads the production web frontend and delegates identity and data to the existing backend. A PowerShell build script provisions repository-local Android tools and signing material, then verifies and exports the APK.

**Tech Stack:** Java, Android SDK 36, Android Gradle Plugin 9.0.1, Gradle 9.1.0, PowerShell.

**Spec:** `docs/superpowers/specs/2026-09-15-android-app-design.md`

## Global Constraints

- Application ID: `cn.campusmeet.app`.
- Minimum Android version: API 26 (Android 8.0).
- Production URL: `https://campusmate-web.onrender.com`.
- No credentials or API tokens may be embedded in the APK.
- Signing secrets and downloaded SDK files must remain outside Git.

---

### Task 1: Native Android Shell

**Files:**
- Create: `apps/mobile/settings.gradle`
- Create: `apps/mobile/build.gradle`
- Create: `apps/mobile/app/build.gradle`
- Create: `apps/mobile/app/src/main/AndroidManifest.xml`
- Create: `apps/mobile/app/src/main/java/cn/campusmeet/app/MainActivity.java`
- Create: `apps/mobile/app/src/main/res/values/*.xml`
- Create: `apps/mobile/app/src/main/res/drawable/*.xml`
- Create: `apps/mobile/app/src/test/java/cn/campusmeet/app/NavigationPolicyTest.java`

**Interfaces:**
- Consumes: `https://campusmate-web.onrender.com`.
- Produces: Android application module `:app` and `NavigationPolicy.isInternal(Uri)`.

- [ ] **Step 1:** Add a failing unit test for internal versus external URL routing.
- [ ] **Step 2:** Implement `NavigationPolicy` and the WebView activity.
- [ ] **Step 3:** Add manifest, theme, icon, splash, and network configuration.
- [ ] **Step 4:** Run the JVM unit test and Android lint.

### Task 2: Reproducible Signed APK Build

**Files:**
- Create: `apps/mobile/scripts/build-android-apk.ps1`
- Create: `apps/mobile/README.md`
- Create: `apps/mobile/.gitignore`
- Modify: `apps/web/package.json`

**Interfaces:**
- Consumes: Google Android command-line tools, SDK packages, Gradle distribution, local JDK.
- Produces: `apps/mobile/output/CampusMeet-1.0.0-android.apk` and ignored signing material.

- [ ] **Step 1:** Download and checksum the command-line tools.
- [ ] **Step 2:** Install platform 36, build-tools 36.0.0, and platform-tools.
- [ ] **Step 3:** Create or reuse the local signing key and build the release APK.
- [ ] **Step 4:** Verify package metadata and APK signature.
- [ ] **Step 5:** Copy the final APK to the shared workspace output directory.
