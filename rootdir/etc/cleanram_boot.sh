#!/system/bin/sh
# Pipa first-boot/background defaults: opaque notification rows + restrict
# background-heavy apps (standby buckets are runtime state, re-applied each boot).
# Tile package must stay in sync: packages/apps/CleanRamTile.

# Opaque notification rows + no window blurs (GPU saver on 144Hz panel).
# (No SettingsProvider overlay on crDroid pipa, so applied at boot.)
settings put global disable_window_blurs 1
settings put secure notification_row_transparency 0
settings put secure notification_row_transparency_lockscreen 0

for p in \
    android.autoinstalls.config.Xiaomi.model \
    au.com.auspost.android \
    au.com.realestate.app \
    com.UCMobile.intl \
    com.adobe.reader \
    com.adobe.scan.android \
    com.amazon.kindle \
    com.anthropic.claude \
    com.brave.browser \
    com.chess \
    com.cpuid.cpu_z \
    com.einnovation.temu \
    com.facebook.katana \
    com.facebook.orca \
    com.google.android.apps.adm \
    com.google.android.apps.authenticator2 \
    com.google.android.apps.books \
    com.google.android.apps.chromecast.app \
    com.google.android.apps.docs \
    com.google.android.apps.docs.editors.docs \
    com.google.android.apps.docs.editors.sheets \
    com.google.android.apps.docs.editors.slides \
    com.google.android.apps.magazines \
    com.google.android.apps.maps \
    com.google.android.apps.walletnfcrel \
    com.google.android.contactkeys \
    com.google.android.gm \
    com.google.android.keep \
    com.google.android.play.games \
    com.google.android.youtube \
    com.instagram.android \
    com.instagram.barcelona \
    com.kamagames.pokerist \
    com.lemon.ccpadpro \
    com.lemon.lvoverseas \
    com.mi.global.shop \
    com.microsoft.office.excel \
    com.microsoft.office.outlook \
    com.microsoft.office.powerpoint \
    com.microsoft.skydrive \
    com.microsoft.teams \
    com.mxtech.videoplayer.ad \
    com.openai.chatgpt \
    com.rawcam.app \
    com.sbs.ondemand.android \
    com.shopify.arrive \
    com.snapchat.android \
    com.spotify.music \
    com.superloop.app \
    com.tplink.iot \
    com.twitter.android \
    com.waze \
    com.whatsapp \
    com.whatsapp.w4b \
    org.localsend.localsend_app \
    org.proninyaroslav.libretorrent \
    org.readera \
    org.telegram.messenger \
    org.torproject.torbrowser \
    org.videolan.vlc \
    org.mozilla.firefox \
    jp.nonbili.noutube \
    org.smarttube.stable \
    org.fdroid.fdroid \
    com.android.chrome \
    com.google.android.googlequicksearchbox \
    ; do
    am set-standby-bucket --user 0 "$p" restricted
    am set-bg-restriction-level --user 0 "$p" restricted_bucket
    cmd deviceidle whitelist -"$p"
done
