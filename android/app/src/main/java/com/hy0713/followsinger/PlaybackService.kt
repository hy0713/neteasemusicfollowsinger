package com.hy0713.followsinger

import android.app.*
import android.content.*
import android.media.*
import android.media.session.*
import android.net.Uri
import android.os.*

class PlaybackService : Service() {
    companion object { var instance: PlaybackService? = null; private set }
    private var player: MediaPlayer? = null
    private lateinit var session: MediaSession
    private lateinit var audio: AudioManager
    private lateinit var focus: AudioFocusRequest
    var title = "本地音频"; private set
    var ready = false; private set
    var problem = ""; private set
    var rate = 1f; private set
    var loopStart = -1L; private set
    private var loopEnd = -1L
    private val handler = Handler(Looper.getMainLooper())
    private val noisy = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) { pause() }
    }
    private val loopTick = object : Runnable {
        override fun run() {
            if (ready && playing && loopStart >= 0 && position >= loopEnd) seek(loopStart)
            handler.postDelayed(this, 40)
        }
    }
    val position: Long get() = if (ready) runCatching { player?.currentPosition?.toLong() ?: 0 }.getOrDefault(0) else 0
    val duration: Long get() = if (ready) runCatching { player?.duration?.toLong() ?: 0 }.getOrDefault(0) else 0
    val playing: Boolean get() = ready && runCatching { player?.isPlaying == true }.getOrDefault(false)
    override fun onCreate() {
        super.onCreate(); instance = this
        audio = getSystemService(AudioManager::class.java)
        focus = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
            .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).build())
            .setOnAudioFocusChangeListener { if (it <= 0) pause() }.build()
        session = MediaSession(this, "FollowSinger")
        session.setCallback(object : MediaSession.Callback() {
            override fun onPlay() { play() }
            override fun onPause() { pause() }
            override fun onSeekTo(pos: Long) { seek(pos) }
            override fun onStop() { pause(); stopSelf() }
            override fun onSetPlaybackSpeed(speed: Float) { setRate(speed) }
        })
        session.isActive = true
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel("playback", "跟唱播放", NotificationManager.IMPORTANCE_LOW))
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(noisy, IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY), RECEIVER_NOT_EXPORTED)
        else registerReceiver(noisy, IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY))
        handler.post(loopTick)
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Foreground promotion happens immediately, before asynchronous media preparation.
        startForeground(1, notification())
        when (intent?.action) {
            "open" -> open(intent.getStringExtra("uri") ?: "", intent.getStringExtra("title") ?: "本地音频")
            "toggle" -> if (playing) pause() else play()
            "play" -> play()
            "pause" -> pause()
            "stop" -> { pause(); stopSelf() }
        }
        return START_NOT_STICKY
    }
    private fun open(uri: String, name: String) {
        player?.release(); ready = false; problem = ""; title = name; loopStart = -1
        val next = MediaPlayer(); player = next
        next.setAudioAttributes(AudioAttributes.Builder().setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
            .setUsage(AudioAttributes.USAGE_MEDIA).build())
        next.setWakeMode(this, PowerManager.PARTIAL_WAKE_LOCK)
        next.setOnPreparedListener {
            if (player !== it) return@setOnPreparedListener
            ready = true; updateSession(); updateNotification()
        }
        next.setOnCompletionListener {
            if (loopStart >= 0) { seek(loopStart); play() }
            else { audio.abandonAudioFocusRequest(focus); updateSession(); updateNotification() }
        }
        next.setOnErrorListener { _, _, _ ->
            problem = "无法解码此音频，请尝试 MP3、M4A 或 WAV"; ready = false
            updateSession(); stopForeground(STOP_FOREGROUND_REMOVE); true
        }
        try { next.setDataSource(this, Uri.parse(uri)); next.prepareAsync() }
        catch (_: Exception) { problem = "无法打开音频，请重新选择文件"; next.release(); player = null; stopSelf() }
    }
    fun play() {
        if (!ready || audio.requestAudioFocus(focus) != AudioManager.AUDIOFOCUS_REQUEST_GRANTED) return
        runCatching {
            if (position >= duration && duration > 0) player?.seekTo(0)
            player?.playbackParams = PlaybackParams().setSpeed(rate).setPitch(1f)
            player?.start()
        }.onFailure { problem = "播放器暂时无法播放此文件" }
        updateSession(); updateNotification()
    }
    fun pause() {
        if (playing) runCatching { player?.pause() }
        audio.abandonAudioFocusRequest(focus); updateSession(); updateNotification()
    }
    fun seek(ms: Long) { if (ready) { player?.seekTo(ms.coerceIn(0, duration), MediaPlayer.SEEK_CLOSEST); updateSession() } }
    fun setRate(value: Float) {
        if (value !in 0.5f..1.5f) return
        val wasPlaying = playing
        if (ready) runCatching {
            player?.playbackParams = PlaybackParams().setSpeed(value).setPitch(1f)
            if (!wasPlaying) player?.pause()
            rate = value
        }.onFailure { problem = "此音频解码器不支持倍速" }
        else rate = value
        updateSession()
    }
    fun setLoop(start: Long, end: Long) {
        if (end - start < 100 || start < 0 || end > duration) { loopStart = -1; loopEnd = -1 }
        else { loopStart = start; loopEnd = end }
    }
    private fun updateSession() {
        session.setMetadata(MediaMetadata.Builder().putString(MediaMetadata.METADATA_KEY_TITLE, title)
            .putLong(MediaMetadata.METADATA_KEY_DURATION, duration).build())
        val actions = PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE or PlaybackState.ACTION_SEEK_TO
        session.setPlaybackState(PlaybackState.Builder().setActions(actions or if (Build.VERSION.SDK_INT >= 31) PlaybackState.ACTION_SET_PLAYBACK_SPEED else 0)
            .setState(if (playing) PlaybackState.STATE_PLAYING else PlaybackState.STATE_PAUSED, position, rate).build())
    }
    private fun notification(): Notification {
        val content = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val toggle = PendingIntent.getService(this, 1, Intent(this, PlaybackService::class.java).setAction("toggle"), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val stop = PendingIntent.getService(this, 2, Intent(this, PlaybackService::class.java).setAction("stop"), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        return Notification.Builder(this, "playback").setSmallIcon(R.drawable.ic_launcher).setContentTitle(title)
            .setContentText(if (playing) "跟唱伴学 · 正在播放" else "跟唱伴学 · 已暂停").setContentIntent(content)
            .addAction(Notification.Action.Builder(android.R.drawable.ic_media_play, if (playing) "暂停" else "播放", toggle).build())
            .addAction(Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel, "关闭", stop).build())
            .setStyle(Notification.MediaStyle().setMediaSession(session.sessionToken).setShowActionsInCompactView(0))
            .setOngoing(playing).setVisibility(Notification.VISIBILITY_PUBLIC).build()
    }
    private fun updateNotification() { getSystemService(NotificationManager::class.java).notify(1, notification()) }
    override fun onBind(intent: Intent?) = null
    override fun onTaskRemoved(rootIntent: Intent?) { stopSelf() }
    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null); unregisterReceiver(noisy)
        audio.abandonAudioFocusRequest(focus); player?.release(); session.release(); instance = null
        super.onDestroy()
    }
}
