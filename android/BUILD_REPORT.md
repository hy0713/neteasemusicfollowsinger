# Android 0.1.0 验证记录

日期：2026-10-07（香港时区）。工程：`neteasemusicfollowsinger/android`。

## 交付

- 应用名：跟唱伴学；包名：`com.hy0713.followsinger`。
- 最低 Android 8.0 / API 26；compile / target SDK 36。
- 个人测试用 debug APK，已签名；安装包与对应源码 ZIP 位于 `dist/android/0.1.0/`，附 SHA256SUMS。
- Android 页面截图为本地 Chrome 390×844 / 360×640 预览，不能当作手机真机截图。

## 通过的检查

| 检查 | 结果 | 验证内容 |
| --- | --- | --- |
| `:app:assembleDebug` | 通过 | Kotlin、Android 资源、清单、DEX、离线资产和 APK 打包 |
| `:app:testDebugUnitTest` | 15 项通过，0 失败 | 媒体时钟 11 项；播放控制能力 4 项 |
| `:app:lintDebug` | 0 错误、6 警告 | 已修复 Android 16 返回手势、URI 授权和远端倍速 API 门槛 |
| `node --test tools/core.test.mjs` | 10 项通过 | LRC/YRC、翻译对齐、80 ms 行边界、五语检测、网易云链接与匹配、循环、汉字谐音、假名转写 |
| `node tools/ui.test.mjs` | 27 项通过 | 实际离线 ephone 与 kuromoji 加载、五语读音及新手谐音、法语 IPA、默认关闭新手、播放／暂停／0.75 倍速、切换假名不换 DOM、重复状态不重复滚动、五皮肤、紧凑布局和文本注入防护 |
| `apksigner verify --verbose` | 通过 | APK v2 签名校验；1 位签名者 |
| APK 资产核对 | 打包脚本强制检查 | 对每一个应用资产比较最终 APK 内字节与当前源码资产，包括词典、规则表、许可和示例 |
| 网易云公开歌词接口 | HTTP / code 200，取得 LRC | Windows 发起真实 HTTPS 请求，核对响应结构；不等同于手机网络或同步联动验收 |

媒体时钟测试包括：重复样本不重置预测锚点，小幅校正不回退，乱序样本不盖过新锚点，手动小幅定位、大幅外部定位、定位请求期间旧样本、暂停、倍速、时长上限、未知进度和换歌清空。控制测试防止把“仅支持播放”的会话当作可暂停，或把“仅支持暂停”的会话当作可播放。

## 仍需真机验收

没有安装到用户手机，没有截取或传输用户手机屏幕，也没有在用户设备上运行探针。以下不是当前测试已证明的结果：

- 系统文件选择器与通知权限页面的真实流程。
- 厂商 Android WebView 的 WebAssembly / Worker 执行与内存占用。
- 前台媒体服务、锁屏通知、音频焦点、蓝牙耳机和实际解码器的倍速行为。
- 手机网易云会话的真实进度精度、媒体动作、歌曲匹配和连续快速歌曲切句。
- 手机上的音频时延、耗电、全曲后台稳定性和各种厂商系统兼容性。

浏览器播放验证使用同一界面与打包的合成 WAV，但媒体实现是浏览器 Audio；APK 则使用 Android MediaPlayer，所以它不等同于安卓播放器实机测试。

## 构建环境与注意事项

JDK 17、Gradle 9.6.0、AGP 9.4.0、Android SDK / Build Tools 36。Gradle 缓存保存在项目内。沙箱内 AAPT2 在资源链接时异常退出；标准版本和 SDK 内 AAPT2 都出现相同问题。获准的沙箱外 Gradle 构建成功，未修改 SDK 或禁用 lint。

6 项 lint 警告为依赖／SDK 新版本提示、内嵌 JavaScript 开启提示和新版备份规则建议；不包含编译或 API 兼容错误。WebView 只加载 APK 自带资产，外部请求被拒绝；歌词通过 textContent 显示，并有 CSP；JavaScript 为 UI 和离线转换必需。

APK 资产核对发现 AAPT 会自动解压并移除词典文件的 `.gz` 后缀。已经把原版压缩字典以 `.gz.bin` 保存，原生资源处理器把 kuromoji 请求的 `.gz` 路径映射到对应 `.gz.bin`，字节不变；浏览器测试也使用同一映射。对 `.mjs` 明确返回 JavaScript MIME 类型，避免旧系统 MIME 表不识别模块脚本。

源码、源码 ZIP 和 Git 工作区排除本地缓存、运行数据、构建输出、`local.properties`、签名密钥和 node_modules。GPL 音标引擎的原版许可及固定版本对应源码随源码 ZIP 提供。
