package com.derp.cleanram;

import android.app.ActivityManager;
import android.graphics.drawable.Icon;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;
import android.util.Log;
import android.widget.Toast;

/** QS tile: force-stop background-heavy user apps, same list as the Termux widget. */
public class CleanRamTile extends TileService {
    private static final String TAG = "CleanRamTile";

    // Must stay in sync with the on-device clear script. System packages excluded.
    private static final String[] PACKAGES = {
        "android.autoinstalls.config.Xiaomi.model",
        "au.com.auspost.android",
        "au.com.realestate.app",
        "com.UCMobile.intl",
        "com.adobe.reader",
        "com.adobe.scan.android",
        "com.amazon.kindle",
        "com.anthropic.claude",
        "com.brave.browser",
        "com.chess",
        "com.cpuid.cpu_z",
        "com.einnovation.temu",
        "com.facebook.katana",
        "com.facebook.orca",
        "com.google.android.apps.adm",
        "com.google.android.apps.authenticator2",
        "com.google.android.apps.books",
        "com.google.android.apps.chromecast.app",
        "com.google.android.apps.docs",
        "com.google.android.apps.docs.editors.docs",
        "com.google.android.apps.docs.editors.sheets",
        "com.google.android.apps.docs.editors.slides",
        "com.google.android.apps.magazines",
        "com.google.android.apps.maps",
        "com.google.android.apps.walletnfcrel",
        "com.google.android.contactkeys",
        "com.google.android.gm",
        "com.google.android.keep",
        "com.google.android.play.games",
        "com.google.android.youtube",
        "com.instagram.android",
        "com.instagram.barcelona",
        "com.kamagames.pokerist",
        "com.lemon.ccpadpro",
        "com.lemon.lvoverseas",
        "com.mi.global.shop",
        "com.microsoft.office.excel",
        "com.microsoft.office.outlook",
        "com.microsoft.office.powerpoint",
        "com.microsoft.skydrive",
        "com.microsoft.teams",
        "com.mxtech.videoplayer.ad",
        "com.openai.chatgpt",
        "com.rawcam.app",
        "com.sbs.ondemand.android",
        "com.shopify.arrive",
        "com.snapchat.android",
        "com.spotify.music",
        "com.superloop.app",
        "com.tplink.iot",
        "com.twitter.android",
        "com.waze",
        "com.whatsapp",
        "com.whatsapp.w4b",
        "org.localsend.localsend_app",
        "org.proninyaroslav.libretorrent",
        "org.readera",
        "org.telegram.messenger",
        "org.torproject.torbrowser",
        "org.videolan.vlc",
        "org.mozilla.firefox",
        "jp.nonbili.noutube",
        "org.smarttube.stable",
        "org.fdroid.fdroid",
        "com.android.chrome",
        "com.google.android.googlequicksearchbox",
    };

    @Override
    public void onClick() {
        super.onClick();
        Tile tile = getQsTile();
        if (tile != null) {
            tile.setState(Tile.STATE_ACTIVE);
            tile.updateTile();
        }
        new Thread(() -> {
            ActivityManager am = getSystemService(ActivityManager.class);
            int count = 0;
            if (am != null) {
                for (String pkg : PACKAGES) {
                    try {
                        am.forceStopPackage(pkg);
                        count++;
                    } catch (Exception e) {
                        Log.w(TAG, "force-stop failed: " + pkg, e);
                    }
                }
            }
            final int done = count;
            getMainHandler().post(() -> {
                Toast.makeText(CleanRamTile.this,
                        "Cleaned " + done + " apps", Toast.LENGTH_SHORT).show();
                Tile t = getQsTile();
                if (t != null) {
                    t.setState(Tile.STATE_INACTIVE);
                    t.updateTile();
                }
            });
        }, "CleanRamTile").start();
    }

    @Override
    public void onStartListening() {
        super.onStartListening();
        Tile tile = getQsTile();
        if (tile != null) {
            tile.setIcon(Icon.createWithResource(this, R.drawable.ic_clean));
            tile.setState(Tile.STATE_INACTIVE);
            tile.updateTile();
        }
    }
}
