package com.hy0713.followsinger

/** Android supplies a monotonic sample timestamp. Repeated samples keep that anchor. */
class MediaClock {
    private var stamp = -1L
    private var position = -1L
    private var playing = false
    private var speed = 1f
    private var last = -1L
    private var reset = true
    private var seekStamp = -2L
    private var seekTarget = -1L
    private var seekIssued = 0L
    fun clear() { stamp = -1; position = -1; last = -1; reset = true; seekStamp = -2 }
    fun allowSeek(target: Long = -1, now: Long = 0) { seekStamp = stamp; seekTarget = target; seekIssued = now }
    fun sample(at: Long, time: Long, running: Boolean, rate: Float, now: Long, duration: Long): Long {
        if (at < 0 || time <= 0) { clear(); return -1 }
        if (time < stamp) {
            last = if (playing && last >= 0) maxOf(last, value(now, duration)) else value(now, duration)
            return last
        }
        if (seekStamp != -2L && seekIssued > 0 && now - seekIssued > 2000) seekStamp = -2
        if (time != stamp || at != position || running != playing || rate != speed) {
            val predicted = value(now, duration)
            val fresh = at + if (running) ((now - time).coerceAtLeast(0) * rate).toLong() else 0
            if (!running || (predicted >= 0 && fresh < predicted - 500)) reset = true
            // Keep the explicit seek pending across duplicate pre-seek samples.
            // Clear it only when a newer sample acknowledges the requested position.
            if (seekStamp != -2L && time > seekStamp &&
                (seekTarget < 0 || kotlin.math.abs(fresh - seekTarget - if (running && seekIssued > 0) ((now - seekIssued) * rate).toLong() else 0) < 600)) {
                reset = true; seekStamp = -2
            }
            stamp = time; position = at; playing = running; speed = rate
        }
        val raw = value(now, duration)
        last = if (reset || last < 0 || !running) raw else maxOf(last, raw)
        if (duration > 0) last = last.coerceAtMost(duration)
        reset = false
        return last
    }
    private fun value(now: Long, duration: Long): Long {
        if (stamp < 0 || position < 0) return -1
        val result = position + if (playing) ((now - stamp).coerceAtLeast(0) * speed).toLong() else 0
        return if (duration > 0) result.coerceIn(0, duration) else result.coerceAtLeast(0)
    }
}
