package com.hy0713.followsinger

import android.media.session.PlaybackState
import org.junit.Assert.*
import org.junit.Test

class PlaybackCapabilitiesTest {
    @Test fun playOnlySessionCannotPretendToPause() {
        assertTrue(PlaybackCapabilities.canToggle(PlaybackState.ACTION_PLAY, false))
        assertFalse(PlaybackCapabilities.canToggle(PlaybackState.ACTION_PLAY, true))
    }
    @Test fun pauseOnlySessionCannotPretendToPlay() {
        assertTrue(PlaybackCapabilities.canToggle(PlaybackState.ACTION_PAUSE, true))
        assertFalse(PlaybackCapabilities.canToggle(PlaybackState.ACTION_PAUSE, false))
    }
    @Test fun combinedToggleWorksInBothStates() {
        assertTrue(PlaybackCapabilities.canToggle(PlaybackState.ACTION_PLAY_PAUSE, true))
        assertTrue(PlaybackCapabilities.canToggle(PlaybackState.ACTION_PLAY_PAUSE, false))
    }
    @Test fun unsupportedSpeedAndSeekAreNotAdvertised() {
        assertFalse(PlaybackCapabilities.supports(PlaybackState.ACTION_PLAY, PlaybackState.ACTION_SEEK_TO))
        assertFalse(PlaybackCapabilities.supports(PlaybackState.ACTION_PLAY, PlaybackState.ACTION_SET_PLAYBACK_SPEED))
    }
}
