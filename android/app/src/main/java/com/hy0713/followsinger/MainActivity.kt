package com.hy0713.followsinger

import android.Manifest
import android.app.*
import android.content.*
import android.database.Cursor
import android.graphics.Color
import android.media.MediaMetadata
import android.media.session.*
import android.net.Uri
import android.os.*
import android.provider.OpenableColumns
import android.provider.Settings
import android.view.*
import android.webkit.*
import android.widget.FrameLayout
import androidx.webkit.WebViewAssetLoader
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import org.json.*
import java.io.ByteArrayInputStream
import java.net.HttpURLConnection
import java.net.URL
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.util.concurrent.Executors

class MainActivity : ComponentActivity() {
    private lateinit var web: WebView
    private val handler = Handler(Looper.getMainLooper())
    private val io = Executors.newFixedThreadPool(2)
    private var pageReady = false
    private var mode = "local"
    private var pickKind = "audio"
    private var remote: MediaController? = null
    private val clock = MediaClock()
    private var previousTrack = ""
    private var previousState = ""
    private var loopStart = -1L
    private var loopEnd = -1L
    private var loopPendingAt = 0L
    private val component by lazy { ComponentName(this, MusicAccessService::class.java) }
    private val manager by lazy { getSystemService(MediaSessionManager::class.java) }
    private val callback = object : MediaController.Callback() {
        override fun onSessionDestroyed() { detachRemote(); sendStatus("网易云播放会话已断开"); refreshRemote() }
    }
    private val sessionListener = MediaSessionManager.OnActiveSessionsChangedListener { refreshRemote() }
    private var listening = false
    private val tick = object : Runnable {
        override fun run() { if (pageReady) publishState(); handler.postDelayed(this, 80) }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = FrameLayout(this)
        root.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout() or WindowInsets.Type.ime())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            } else view.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, insets.systemWindowInsetBottom)
            insets
        }
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        web = WebView(this)
        root.addView(web, FrameLayout.LayoutParams(-1, -1)); setContentView(root)
        web.settings.apply {
            javaScriptEnabled = true; domStorageEnabled = true
            allowFileAccess = false; allowContentAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            mediaPlaybackRequiresUserGesture = true
        }
        val loader = WebViewAssetLoader.Builder().addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this)).build()
        web.addJavascriptInterface(Bridge(), "Android")
        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest): WebResourceResponse {
                val path = request.url.path.orEmpty()
                // AAPT auto-inflates and renames .gz assets. Store the original compressed
                // dictionary as .gz.bin, then serve the upstream requested .gz URL unchanged.
                val assetUrl = if (path.startsWith("/assets/web/vendor/kuromoji/dict/") && path.endsWith(".gz"))
                    request.url.buildUpon().path(path + ".bin").build() else request.url
                val response = loader.shouldInterceptRequest(assetUrl)
                if (response != null) {
                    // Older Android MIME tables don't recognize .mjs; module scripts require a JS MIME.
                    if (request.url.path.orEmpty().endsWith(".mjs") || request.url.path.orEmpty().endsWith(".js")) response.mimeType = "application/javascript"
                    if (request.url.path.orEmpty().endsWith(".json")) response.mimeType = "application/json"
                    return response
                }
                return WebResourceResponse("text/plain", "UTF-8", 403, "Blocked", emptyMap(), ByteArrayInputStream(byteArrayOf()))
            }
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest): Boolean {
                // Imported lyrics cannot navigate to content with access to the native bridge.
                return request.url.host != "appassets.androidplatform.net" || !request.url.path.orEmpty().startsWith("/assets/")
            }
            override fun onPageFinished(view: WebView?, url: String?) {
                if (url == "https://appassets.androidplatform.net/assets/web/index.html") pageReady = true
            }
        }
        web.loadUrl("https://appassets.androidplatform.net/assets/web/index.html")
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                web.evaluateJavascript("window.closeSheet && window.closeSheet()") { if (it != "true") finish() }
            }
        })
    }
    inner class Bridge {
        @JavascriptInterface fun postMessage(message: String) {
            if (message.length > 65536) return
            handler.post {
                runCatching { command(JSONObject(message)) }.onFailure { sendStatus("操作失败：${it.message ?: "请重试"}", true) }
            }
        }
    }
    private fun command(data: JSONObject) {
        when (data.optString("action")) {
            "ready" -> { pageReady = true; send(JSONObject().put("type", "platform").put("android", true)); publishState() }
            "pick" -> {
                pickKind = data.optString("kind", "audio")
                val type = if (pickKind == "audio") "audio/*" else "*/*"
                startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                    .setType(type).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION), 11)
            }
            "sample" -> loadSample(data.optString("language"))
            "mode" -> {
                clearLoop(); mode = if (data.optString("value") == "netease") "netease" else "local"
                if (mode == "netease") { PlaybackService.instance?.pause(); previousTrack = ""; refreshRemote() }
                else { detachRemote(); clock.clear() }
                previousState = ""; publishState()
            }
            "permission" -> {
                // Android's system UI is where the user grants this access.
                startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
            }
            "toggle" -> {
                if (mode == "local") {
                    PlaybackService.instance?.let {
                        startForegroundService(Intent(this, PlaybackService::class.java).setAction("toggle"))
                    }
                } else remote?.let {
                    val state = it.playbackState
                    val playing = state?.state == PlaybackState.STATE_PLAYING
                    if (playing && supports(PlaybackState.ACTION_PAUSE, state)) it.transportControls.pause()
                    else if (!playing && supports(PlaybackState.ACTION_PLAY, state)) it.transportControls.play()
                    else if (supports(PlaybackState.ACTION_PLAY_PAUSE, state)) {
                        it.dispatchMediaButtonEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, android.view.KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE))
                        it.dispatchMediaButtonEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_UP, android.view.KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE))
                    } else sendStatus("网易云未提供播放控制", true)
                }
            }
            "seek" -> {
                val value = data.optLong("position").coerceAtLeast(0)
                if (mode == "local") PlaybackService.instance?.seek(value)
                else if (supports(PlaybackState.ACTION_SEEK_TO, remote?.playbackState)) {
                    loopPendingAt = SystemClock.elapsedRealtime(); clock.allowSeek(value, loopPendingAt); remote?.transportControls?.seekTo(value)
                }
            }
            "rate" -> {
                val value = data.optDouble("value", 1.0).toFloat()
                if (value !in 0.5f..1.5f) return
                if (mode == "local") PlaybackService.instance?.setRate(value)
                else if (Build.VERSION.SDK_INT >= 31 && supports(PlaybackState.ACTION_SET_PLAYBACK_SPEED, remote?.playbackState)) remote?.transportControls?.setPlaybackSpeed(value)
                else sendStatus("网易云当前未开放倍速；本地播放支持倍速", true)
            }
            "loop" -> {
                clearLoop()
                val start = data.optLong("start", -1); val end = data.optLong("end", -1)
                if (mode == "local") PlaybackService.instance?.setLoop(start, end)
                else if (supports(PlaybackState.ACTION_SEEK_TO, remote?.playbackState) && start >= 0 && end - start >= 800) {
                    loopStart = start; loopEnd = end
                } else if (start >= 0) sendStatus("远端循环需要可定位时间轴，且句长至少 0.8 秒", true)
                previousState = ""
            }
            "search", "lyrics" -> {
                val action = data.optString("action"); val request = data.optInt("request")
                io.execute {
                    val result = runCatching { if (action == "search") search(data.optString("query")) else lyrics(data.optString("id")) }
                    handler.post {
                        result.onSuccess { send(it.put("request", request)) }
                            .onFailure { send(JSONObject().put("type", "error").put("request", request).put("message", it.message ?: "歌词获取失败")) }
                    }
                }
            }
            "theme" -> {
                val dark = data.optBoolean("dark")
                val color = runCatching { Color.parseColor(data.optString("background", "#ffffff")) }.getOrDefault(Color.WHITE)
                (web.parent as View).setBackgroundColor(color); web.setBackgroundColor(color)
                if (Build.VERSION.SDK_INT >= 30) window.insetsController?.setSystemBarsAppearance(
                    if (dark) 0 else WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS)
                else window.decorView.systemUiVisibility = if (dark) 0 else View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
                window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            }
        }
    }
    @Deprecated("Android activity-result callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 11 || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        if (pickKind == "audio") {
            if ((data.flags and Intent.FLAG_GRANT_READ_URI_PERMISSION) != 0)
                runCatching { contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION) }
            val name = displayName(uri)
            startAudio(uri.toString(), name)
            send(JSONObject().put("type", "audio").put("name", name))
        } else {
            val kind = pickKind
            io.execute {
                val result = runCatching { contentResolver.openInputStream(uri)!!.use { input ->
                    val bytes = input.readBytesLimited(2 * 1024 * 1024)
                    decodeText(bytes)
                } }
                handler.post { result.onSuccess { send(JSONObject().put("type", "import").put("kind", kind).put("name", displayName(uri)).put("text", it)) }
                    .onFailure { sendStatus(it.message ?: "歌词读取失败", true) } }
            }
        }
    }
    private fun java.io.InputStream.readBytesLimited(limit: Int): ByteArray {
        val out = java.io.ByteArrayOutputStream(); val buffer = ByteArray(8192)
        while (true) { val count = read(buffer); if (count < 0) break; if (out.size() + count > limit) error("歌词文件超过 2 MB"); out.write(buffer, 0, count) }
        return out.toByteArray()
    }
    private fun decodeText(bytes: ByteArray): String {
        if (bytes.size >= 2 && ((bytes[0] == 0xFF.toByte() && bytes[1] == 0xFE.toByte()) || (bytes[0] == 0xFE.toByte() && bytes[1] == 0xFF.toByte()))) return bytes.toString(Charsets.UTF_16)
        return runCatching { Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString().removePrefix("\uFEFF") }
            .getOrElse { bytes.toString(charset("GB18030")) }
    }
    private fun displayName(uri: Uri): String = runCatching {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor: Cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else "本地文件"
        } ?: "本地文件"
    }.getOrDefault("本地文件")
    private fun startAudio(uri: String, name: String) {
        mode = "local"; clearLoop(); detachRemote(); clock.clear()
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED)
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 12)
        startForegroundService(Intent(this, PlaybackService::class.java).setAction("open").putExtra("uri", uri).putExtra("title", name))
    }
    private fun loadSample(language: String) {
        if (language !in listOf("ja", "en", "fr", "ru", "ko")) return
        val audio = java.io.File(filesDir, "practice.wav")
        if (!audio.exists()) assets.open("samples/practice.wav").use { input -> audio.outputStream().use { input.copyTo(it) } }
        startAudio(Uri.fromFile(audio).toString(), "五语练习 · $language")
        send(JSONObject().put("type", "sample").put("language", language)
            .put("original", assets.open("samples/$language.lrc").bufferedReader().use { it.readText() })
            .put("translation", assets.open("samples/$language.zh.lrc").bufferedReader().use { it.readText() }))
    }
    private fun hasAccess(): Boolean = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        .orEmpty().split(':').any { ComponentName.unflattenFromString(it) == component }
    private fun refreshRemote() {
        if (mode != "netease") return
        if (!hasAccess()) { detachRemote(); sendStatus("请先开启通知使用权，用于读取网易云媒体会话"); return }
        runCatching {
            if (!listening) { manager.addOnActiveSessionsChangedListener(sessionListener, component, handler); listening = true }
            val candidates = manager.getActiveSessions(component).filter { it.packageName == "com.netease.cloudmusic" }
            val selected = candidates.firstOrNull { it.playbackState?.state == PlaybackState.STATE_PLAYING } ?: candidates.firstOrNull()
            if (selected?.sessionToken != remote?.sessionToken) {
                detachRemote(); remote = selected; clock.clear(); previousTrack = ""
                selected?.registerCallback(callback, handler)
            }
            if (selected == null) sendStatus("尚未发现网易云播放，请在网易云开始播放歌曲")
        }.onFailure { detachRemote(); sendStatus("媒体会话访问失败，请重新开启通知使用权", true) }
    }
    private fun detachRemote() { remote?.unregisterCallback(callback); remote = null; loopStart = -1; loopEnd = -1 }
    private fun clearLoop() { loopStart = -1; loopEnd = -1; PlaybackService.instance?.setLoop(-1, -1) }
    private fun supports(action: Long, state: PlaybackState?): Boolean = ((state?.actions ?: 0) and action) != 0L
    private fun publishState() {
        val json = JSONObject().put("type", "state").put("mode", mode)
        if (mode == "local") {
            val local = PlaybackService.instance
            json.put("position", local?.position ?: 0).put("duration", local?.duration ?: 0)
                .put("playing", local?.playing == true).put("ready", local?.ready == true)
                .put("canPlay", local?.ready == true).put("canSeek", local?.ready == true).put("canRate", local?.ready == true)
                .put("rate", local?.rate ?: 1f).put("loop", (local?.loopStart ?: -1) >= 0).put("title", local?.title ?: "选择一首歌，开始跟唱")
                .put("problem", local?.problem ?: "")
        } else {
            val state = remote?.playbackState; val meta = remote?.metadata
            val title = meta?.getString(MediaMetadata.METADATA_KEY_TITLE).orEmpty()
            val artist = meta?.getString(MediaMetadata.METADATA_KEY_ARTIST).orEmpty()
            val duration = meta?.getLong(MediaMetadata.METADATA_KEY_DURATION) ?: 0L
            val key = "$title|$artist|$duration"
            if (key != previousTrack) {
                clearLoop(); clock.clear(); previousTrack = key
                if (title.isNotBlank()) send(JSONObject().put("type", "track").put("title", title).put("artist", artist).put("duration", duration))
            }
            val running = state?.state == PlaybackState.STATE_PLAYING
            val now = SystemClock.elapsedRealtime()
            val position = if (state == null) -1 else clock.sample(state.position, state.lastPositionUpdateTime, running, state.playbackSpeed, now, duration)
            if (loopStart >= 0 && running && position >= loopEnd && now - loopPendingAt >= 1000) {
                clock.allowSeek(loopStart, now); remote?.transportControls?.seekTo(loopStart); loopPendingAt = now
            }
            json.put("position", position).put("duration", duration).put("playing", running).put("ready", remote != null)
                .put("canPlay", PlaybackCapabilities.canToggle(state?.actions ?: 0, running))
                .put("canSeek", position >= 0 && duration > 0 && supports(PlaybackState.ACTION_SEEK_TO, state))
                .put("canRate", Build.VERSION.SDK_INT >= 31 && supports(PlaybackState.ACTION_SET_PLAYBACK_SPEED, state))
                .put("rate", state?.playbackSpeed?.takeIf { it > 0 } ?: 1f).put("loop", loopStart >= 0)
                .put("title", title.ifBlank { "等待网易云播放" }).put("artist", artist).put("access", hasAccess())
        }
        val text = json.toString()
        if (text != previousState) { previousState = text; send(json) }
    }
    private fun api(endpoint: String, params: Map<String, String>): JSONObject {
        val query = params.entries.joinToString("&") { "${it.key}=${java.net.URLEncoder.encode(it.value, "UTF-8")}" }
        val connection = URL("https://music.163.com/api/$endpoint?$query").openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 8000; connection.readTimeout = 10000; connection.instanceFollowRedirects = false
            connection.setRequestProperty("User-Agent", "Mozilla/5.0 FollowSingerAndroid/0.1.0")
            connection.setRequestProperty("Referer", "https://music.163.com/")
            if (connection.responseCode != 200) error("网易云接口暂不可用，可导入本地 LRC")
            val json = JSONObject(connection.inputStream.use { decodeText(it.readBytesLimited(2 * 1024 * 1024)) })
            if (json.optInt("code") != 200) error("网易云接口暂不可用，可导入本地 LRC")
            return json
        } finally { connection.disconnect() }
    }
    private fun search(query: String): JSONObject {
        if (query.isBlank() || query.length > 200) error("请输入歌名或歌手")
        val songs = api("search/get", mapOf("s" to query, "type" to "1", "limit" to "12"))
            .optJSONObject("result")?.optJSONArray("songs") ?: JSONArray()
        val results = JSONArray()
        for (i in 0 until songs.length()) {
            val item = songs.getJSONObject(i); val artists = item.optJSONArray("artists") ?: JSONArray()
            results.put(JSONObject().put("id", item.getLong("id").toString()).put("title", item.optString("name"))
                .put("artist", (0 until artists.length()).joinToString(" / ") { artists.getJSONObject(it).optString("name") })
                .put("duration", item.optLong("duration")))
        }
        return JSONObject().put("type", "search").put("songs", results)
    }
    private fun lyrics(id: String): JSONObject {
        if (!id.matches(Regex("\\d{1,20}"))) error("无效歌曲 ID")
        val json = api("song/lyric", mapOf("id" to id, "lv" to "-1", "tv" to "-1", "yv" to "-1"))
        return JSONObject().put("type", "lyrics").put("id", id)
            .put("original", json.optJSONObject("lrc")?.optString("lyric").orEmpty())
            .put("yrc", json.optJSONObject("yrc")?.optString("lyric").orEmpty())
            .put("translation", json.optJSONObject("tlyric")?.optString("lyric").orEmpty())
    }
    private fun sendStatus(message: String, error: Boolean = false) = send(JSONObject().put("type", "status").put("message", message).put("error", error))
    private fun send(json: JSONObject) {
        if (pageReady && !isDestroyed) web.evaluateJavascript("window.receiveNative && window.receiveNative($json)", null)
    }
    override fun onResume() { super.onResume(); previousState = ""; refreshRemote(); handler.removeCallbacks(tick); handler.post(tick) }
    override fun onPause() { handler.removeCallbacks(tick); super.onPause() }
    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null); detachRemote()
        if (listening) runCatching { manager.removeOnActiveSessionsChangedListener(sessionListener) }
        io.shutdownNow(); web.removeJavascriptInterface("Android"); web.destroy(); super.onDestroy()
    }
}
