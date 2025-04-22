plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.jetbrains.kotlin.android)
}

android {
    namespace = "com.projetosae5g.app_5g_layout"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.projetosae5g.app_5g_layout"
        // Se estiver desenvolvendo para Wear OS 3+, use minSdk = 30
        minSdk = 30
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }

    // Configurações de compilação em Java 17 para código Java e Kotlin
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}

dependencies {
    // Dependências do seu libs.versions.toml
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.activity)

    // Testes
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)

    // Se usar Wear OS
    implementation(libs.androidx.wear)
    implementation(libs.play.services.wearable)

    // Se usar Health Services (p/ batimentos cardíacos etc.)
    implementation(libs.androidx.health.services)
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-guava:1.6.0")

}
