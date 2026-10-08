plugins { id("com.android.application") }
android {
    namespace = "com.hy0713.followsinger"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.hy0713.followsinger"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
dependencies {
    implementation("androidx.webkit:webkit:1.14.0")
    implementation("androidx.activity:activity:1.13.0")
    testImplementation("junit:junit:4.13.2")
}
