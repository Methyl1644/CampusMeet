# CampusMeet Android App Design

## Goal

Produce a directly installable Android APK for course review while keeping the existing React and FastAPI system as the single product implementation.

## Architecture

The Android app is a small native Java WebView shell with package name `cn.campusmeet.app`. It loads `https://campusmate-web.onrender.com`, keeps cookies and local storage, opens non-CampusMeet links externally, supports file selection, and uses Android back navigation before exiting. A branded offline screen is shown when the initial page cannot load.

The APK is built with Android Gradle Plugin 9.0.1, Gradle 9.1.0, compile/target SDK 36, and minimum SDK 26. To avoid Windows path-length failures, the build script downloads command-line tools into the short local cache `C:\Users\Public\CampusMeetAndroid`, installs only the required SDK packages, creates a local release signing key if absent, and copies the signed APK to `apps/mobile/output/`.

## Security And Boundaries

- Only HTTPS production URLs are loaded inside the WebView.
- JavaScript bridges and native privileged interfaces are not exposed.
- The release keystore and passwords are excluded from Git.
- Authentication remains server-issued; the APK does not embed passwords, API tokens, or reviewer credentials.
- The app requires network connectivity and inherits the availability of Render and Coze services.

## Acceptance Criteria

- A release-signed universal APK is produced.
- Package name is `cn.campusmeet.app` and minimum SDK is 26.
- Launcher icon and splash screen use the CampusMeet brand.
- Back navigation, file upload, external links, and offline handling are implemented.
- The APK signature and manifest are verified with Android build tools.
