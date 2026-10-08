package com.hy0713.followsinger

import android.service.notification.NotificationListenerService

// The system grants media-session access only while this listener is enabled.
// Notification contents are deliberately not inspected or persisted.
class MusicAccessService : NotificationListenerService()
