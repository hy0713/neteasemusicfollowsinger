package com.hy0713.followsinger

import org.junit.Assert.*
import org.junit.Test

class MediaClockTest {
    @Test fun repeatedPositionDoesNotResetAnchor() {
        val clock = MediaClock()
        assertEquals(950L, clock.sample(950, 1000, true, 1f, 1000, 30000))
        assertEquals(1050L, clock.sample(950, 1000, true, 1f, 1100, 30000))
        assertEquals(1130L, clock.sample(950, 1000, true, 1f, 1180, 30000))
    }
    @Test fun smallCorrectionsNeverRewindDuringPlayback() {
        val clock = MediaClock()
        assertEquals(1050L, clock.sample(950, 1000, true, 1f, 1100, 30000))
        assertEquals(1050L, clock.sample(1000, 1100, true, 1f, 1100, 30000))
        assertEquals(1080L, clock.sample(1000, 1100, true, 1f, 1180, 30000))
    }
    @Test fun oldSamplesDoNotReplaceNewAnchor() {
        val clock = MediaClock()
        clock.sample(2000, 2000, true, 1f, 2000, 30000)
        assertEquals(2100L, clock.sample(800, 1000, true, 1f, 2100, 30000))
    }
    @Test fun manualSmallSeekCanRewind() {
        val clock = MediaClock()
        clock.sample(1050, 1000, true, 1f, 1000, 30000)
        clock.allowSeek()
        assertEquals(900L, clock.sample(900, 1010, true, 1f, 1010, 30000))
    }
    @Test fun externallyReportedLargeSeekCanRewind() {
        val clock = MediaClock()
        clock.sample(12000, 1000, true, 1f, 1000, 30000)
        assertEquals(1000L, clock.sample(1000, 1010, true, 1f, 1010, 30000))
    }
    @Test fun seekAcknowledgementSurvivesDuplicateOldSamples() {
        val clock = MediaClock()
        clock.sample(1050, 1000, true, 1f, 1000, 30000)
        clock.allowSeek(900, 1000)
        assertEquals(1070L, clock.sample(1050, 1000, true, 1f, 1020, 30000))
        assertEquals(930L, clock.sample(930, 1030, true, 1f, 1030, 30000))
    }
    @Test fun lateOutOfOrderSampleCannotUndoSmallMonotonicCorrection() {
        val clock = MediaClock()
        clock.sample(1050, 1000, true, 1f, 1000, 30000)
        clock.sample(1000, 1010, true, 1f, 1010, 30000)
        assertEquals(1050L, clock.sample(800, 500, true, 1f, 1020, 30000))
    }
    @Test fun pauseFreezesAtAuthoritativePosition() {
        val clock = MediaClock()
        clock.sample(1000, 1000, true, 1f, 1200, 30000)
        assertEquals(1150L, clock.sample(1150, 1250, false, 1f, 9000, 30000))
    }
    @Test fun rateAndDurationAreApplied() {
        val clock = MediaClock()
        assertEquals(2500L, clock.sample(1000, 1000, true, 1.5f, 2000, 30000))
        assertEquals(30000L, clock.sample(1000, 1000, true, 1.5f, 99000, 30000))
    }
    @Test fun unknownPositionIsNotInvented() {
        assertEquals(-1L, MediaClock().sample(-1, 1000, true, 1f, 2000, 30000))
        assertEquals(-1L, MediaClock().sample(1000, 0, true, 1f, 2000, 30000))
    }
    @Test fun trackChangeClearsPreviousProgress() {
        val clock = MediaClock()
        clock.sample(20000, 1000, true, 1f, 1000, 30000)
        clock.clear()
        assertEquals(500L, clock.sample(500, 2000, true, 1f, 2000, 30000))
    }
}
