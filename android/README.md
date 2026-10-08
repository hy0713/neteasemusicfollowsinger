# 跟唱伴学 Android 0.1.0

可安装的 Android APK，最低 Android 8.0（API 26）。界面采用手机竖屏布局；播放、文件选择和网易云媒体会话由 Kotlin 实现，歌词界面运行于应用内 WebView，不需要打开浏览器。请使用已更新的 Android System WebView / Chrome；离线音标引擎使用 WebAssembly 和 Web Worker。

## 安装与使用

从 [Android 0.1.0 发布页](https://github.com/hy0713/neteasemusicfollowsinger/releases/tag/android-v0.1.0) 下载 APK；同一页面提供对应源码 ZIP 与 SHA256 校验文件。

把 `FollowSinger-Android-0.1.0.apk` 传到手机，允许该文件来源安装应用，点击安装。当前为带调试签名的个人测试版，没有正式发布签名，也未上架应用商店。

1. 首次打开可点击「体验法语跟唱」，检查原文、IPA、译文和播放器。示例只有原创短句及合成提示音，不是原唱人声。
2. 「曲库 → 打开音频」选自己的 MP3 / M4A / WAV，再「导入歌词」选同曲 LRC。「导入中文译文 LRC」可添加中文翻译。文件通过系统选择器授权，不要求整个存储空间权限。歌词支持 UTF-8、UTF-16 BOM、GB18030，限制 2 MB。
3. 顶部选择日语、英语、俄语、法语、韩语或自动识别。日语支持假名／罗马音；英语和法语显示离线 IPA；俄语和韩语显示转写。顶部「新手」默认关闭，打开后额外显示汉字谐音。读音不是演唱语音识别，谐音不是翻译，不能代替听原唱。
4. 本地音频可播放／暂停、点击歌词定位、0.5–1.5 倍速、上一句／下一句和单句循环。在「设置」选择五种皮肤、歌词字号和歌词延迟。浏览歌词后点「回到当前句」恢复自动跟随。
5. 播放本地歌曲后可切到后台，通知栏提供播放／暂停与关闭。关闭最近任务会停止本地播放。耳机断开或失去音频焦点时暂停。歌词练习页保持屏幕常亮；暂停后仍可查看歌词。

## 网易云同步

「曲库 → 网易云同步 → 开启网易云播放同步」，在 Android 的通知使用权页面启用「跟唱伴学 · 网易云播放同步」，再去网易云播放歌曲，返回本程序。

- 仅连接包名 `com.netease.cloudmusic` 的媒体会话，不读取或保存聊天通知，不索取登录凭据或 Cookie。
- 从媒体会话获取标题、歌手和进度，自动搜索公开歌词。只有标题、歌手与时长明确匹配时自动选歌，匹配不明确时显示结果供选择。也可以手动搜索或输入网易云链接／歌曲 ID。
- 歌曲音频由网易云客户端播放。本应用不下载受保护音频。
- 播放、暂停、定位和倍速按钮根据媒体会话提供的动作启用；不支持时禁用。远端倍速需要 Android 12 以上且网易云会话明确提供该动作。本地倍速不受此限制。没有有效进度时间戳时不会虚构同步进度。
- 时间轴使用 Android 的单调时钟时间戳预测；重复样本不重置起点，小幅校正保持向前，较大的回退及明确定位可回到之前的句子。远端单句循环要求可定位且句长至少 0.8 秒；仅在跟唱页面处于前台时执行。
- 网易云版本、手机系统与后台策略会影响可用能力。本次尚未完成真机网易云联动验收，不能保证每个版本均开放定位和倍速。

## 离线词典与许可证

- `web/vendor/ephone/`：原版 ephone 1.0.2，eSpeak NG 的 WebAssembly 音标生成移植，GPL-3.0-or-later。[上游源码](https://github.com/sjmik/ephone-js/tree/v1.0.2)，固定标签提交 `4f6d246c1d3acf67a4d814e20da02fa3967bc92d`。使用完整离线语言包以包含韩语、俄语和法语。
- `web/vendor/kuromoji/`：原版 kuromoji.js 0.1.2 及 IPADIC 字典，Apache-2.0 / NAIST 许可。[上游项目](https://github.com/takuyaa/kuromoji.js)。其依赖许可证一并保存在 `app/src/main/assets/licenses/`。
- 本程序 GPL-3.0-only；法语鼻元音、连读，日语多音字，俄语重音和韩语音变仍可能与原唱不同。

## 构建

需要 JDK 17、Android SDK Platform 36、Build Tools 36.0.0。Gradle Wrapper 固定为 9.6.0，AGP 9.4.0。不需要 NDK、Python 或服务器来运行 APK。

```powershell
.\tools\build.ps1 -SdkPath 'C:\path\to\android-sdk' -JavaHome 'C:\path\to\jdk-17'
```

构建输出 `app/build/outputs/apk/debug/app-debug.apk`。构建脚本使用项目内 Gradle 缓存与 Android 配置目录，`local.properties` 不进入版本控制。沙箱 Windows 环境中的 AAPT2 链接可能异常退出，本次是在获准的沙箱外构建中成功完成。

音标、词典及规则表已经随源码提交，构建 APK 无需 npm。更新第三方前端包时：

```powershell
cd tools
npm ci --registry=https://registry.npmjs.org
node --test core.test.mjs
node ui.test.mjs
```

`ui.test.mjs` 的浏览器可执行路径目前指向 Windows 默认 Chrome 安装路径；换机器时应修改这个测试路径。`generate_reading_data.py` 是开发用的桌面规则表生成器，需要桌面版 Python 依赖；正常构建不需要重新生成。

## 本次验证

2026-10-07：APK 构建与签名校验成功。前端 10 项核心测试、27 项浏览器交互检查通过；安卓单元测试覆盖媒体时钟与控制能力。浏览器检查使用实际打包的词典与引擎，验证五语读音、法语 IPA、新手谐音、默认关闭、播放／暂停／0.75 倍速、日语切换不重建歌词、五皮肤、360×640 布局、重复进度不重复滚动以及导入文字不会执行 HTML。

浏览器验证不是 Android 真机验证。系统文件选择器、前台播放服务、通知使用权、硬件音频解码和网易云联动尚未在手机上验收。完整记录见 `BUILD_REPORT.md`。
