package com.hy0713.followsinger

import android.media.session.PlaybackState

object PlaybackCapabilities {
    fun supports(actions: Long, action: Long) = (actions and action) != 0L
    fun canToggle(actions: Long, playing: Boolean): Boolean = supports(actions, PlaybackState.ACTION_PLAY_PAUSE) ||
        supports(actions, if (playing) PlaybackState.ACTION_PAUSE else PlaybackState.ACTION_PLAY)
}
