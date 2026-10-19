"""The connection to the TV: pairing, tokens, commands, and keeping Hearth on screen."""
import json
import ssl
import threading
import time

import paho.mqtt.client as mqtt

from . import certs, events, network, protocol

FALLBACK_MAC = "02:00:00:00:00:01"


class TV:
    """One TV, reached over its MQTT remote-control broker.

    `state` is a JsonStore holding the session (ip, mac, client id, tokens, cached lists).
    `settings` provides own_home. `home_url` is a callable returning the TV home page address.
    """

    def __init__(self, state, settings, home_url, cert_dir=None):
        self.store = state
        self.settings = settings
        self.home_url = home_url
        self.cert_dir = cert_dir
        self.client = None
        self.connected = False
        self.paired = bool(state.get("access_token"))
        self.needs_pairing = False
        self.last_error = ""
        self.state = {}             # what the TV is showing right now
        self.volume = None
        self.apps = state.get("apps_cache", [])
        self.sources = state.get("sources_cache", [])
        self.info = {}
        self.asleep = False
        self.was_off = False
        self.last_ready = 0.0
        self._last_guard = 0.0
        self._lock = threading.Lock()
        self._connecting = threading.Lock()   # only one connect() at a time
        self._vol_cond = threading.Condition()
        self._vol_seq = 0

    # ---- addresses ---------------------------------------------------
    @property
    def ip(self):
        return self.store.get("ip", "")

    @property
    def cid(self):
        return self.store.get("client_id", "")

    def _topic(self, service, kind, action):
        return protocol.tv_topic(self.cid, service, kind, action)

    # ---- connecting --------------------------------------------------
    def _open(self, ip, user, password, cert, key):
        """One MQTT session; returns (client, None) or (None, reason)."""
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.cid, protocol=mqtt.MQTTv311, clean_session=True)
        c.username_pw_set(user, password)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE   # the TV's certificate is self-signed
        ctx.load_cert_chain(cert, key)
        c.tls_set_context(ctx)
        done, result = threading.Event(), {}

        def on_connect(_c, _u, _flags, rc, _props=None):
            result["rc"] = rc
            done.set()

        c.on_connect = on_connect
        c.on_message = self._on_message
        try:
            c.connect(ip, network.TV_PORT, keepalive=10)
        except OSError as e:
            return None, f"{type(e).__name__}: {e}"
        c.loop_start()
        if done.wait(6) and not result["rc"].is_failure:
            c.on_disconnect = self._on_disconnect
            return c, None
        c.loop_stop()
        c.disconnect()
        return None, str(result.get("rc", "no answer"))

    @property
    def connecting(self):
        return self._connecting.locked()

    def connect(self, ip):
        """Reconnect with the saved token (refreshing it if needed), or start pairing.

        Two sessions with the same client id knock each other off the TV, so a connect
        that starts while another is running just waits for it instead.
        """
        if not self._connecting.acquire(blocking=False):
            with self._connecting:
                return self.connected
        try:
            return self._connect(ip)
        finally:
            self._connecting.release()

    def _connect(self, ip):
        self.disconnect()
        self.last_error = ""
        cert, key = certs.find(self.cert_dir) if self.cert_dir else certs.find()
        if not cert:
            self.last_error = "No VIDAA client certificate in the certs folder. See the README."
            return False
        if ip != self.ip:   # a different TV: start a fresh session
            self.store.replace({"ip": ip})
        if not self.store.get("mac"):
            self.store.update(mac=network.mac_for(ip))
        self.store.update(client_id=protocol.client_id(self.store.get("mac") or FALLBACK_MAC))

        if not network.port_open(ip):
            self.last_error = "TV is off or not on this network."
            self.was_off = True
            return False

        if self.store.get("access_token"):
            for attempt in ("saved", "refreshed"):
                if attempt == "refreshed" and not self._refresh_token(ip, cert, key):
                    break
                c, _ = self._open(ip, self.store.get("username"), self.store.get("access_token"), cert, key)
                if c:
                    self._ready(c, paired=True)
                    return True

        timestamp = network.tv_clock(ip)
        errors = []
        for profile in protocol.PROFILES:
            user, password = protocol.login(timestamp, profile)
            c, why = self._open(ip, user, password, cert, key)
            if c:
                self.store.update(username=user, profile=profile)
                self._ready(c, paired=False)
                self.request_pin()
                return True
            errors.append(f"{profile}: {why}")
        self.last_error = "; ".join(errors)
        return False

    def _refresh_token(self, ip, cert, key):
        """Trade the 30-day refresh token for a new access token (no PIN needed)."""
        refresh, user = self.store.get("refresh_token"), self.store.get("username")
        if not (refresh and user):
            return False
        c, _ = self._open(ip, user, refresh, cert, key)
        if not c:
            return False
        got = threading.Event()

        def on_message(_c, _u, msg):
            try:
                data = json.loads(msg.payload.decode())
            except ValueError:
                return
            if isinstance(data, dict) and data.get("accesstoken"):
                self.store.update(access_token=str(data["accesstoken"]),
                                  refresh_token=str(data.get("refreshtoken") or refresh),
                                  token_time=int(time.time()))
                got.set()

        c.on_message = on_message
        c.on_disconnect = None
        c.subscribe(f"/remoteapp/mobile/{self.cid}/platform_service/data/tokenissuance", 0)
        time.sleep(0.5)
        c.publish(self._topic("platform_service", "data", "gettoken"), json.dumps({"refreshtoken": refresh}))
        ok = got.wait(10)
        c.loop_stop()
        c.disconnect()
        events.add("tv", "token refreshed" if ok else "token refresh failed")
        return ok

    def _ready(self, client, paired):
        if paired and self.was_off and self.settings.get("own_home"):
            threading.Timer(0.3, self.open_home).start()   # the TV has just been switched on
        self.was_off = False
        self.client, self.connected, self.paired, self.needs_pairing = client, True, paired, not paired
        for topic in protocol.subscriptions(self.cid):
            client.subscribe(topic, 0)   # one at a time, so one refused topic can't sink the rest
        if paired:
            self.refresh()

    def disconnect(self):
        client, self.client, self.connected = self.client, None, False
        if client:
            client.on_disconnect = None
            client.disconnect()
            client.loop_stop()

    def _on_disconnect(self, client, *_args, **_kwargs):
        if client is not self.client:   # a session we've already replaced
            return
        self.connected = False
        events.add("tv", "disconnected")

    # ---- messages from the TV ----------------------------------------
    def _on_message(self, _client, _userdata, msg):
        topic = msg.topic
        raw = msg.payload.decode(errors="ignore")
        try:
            data = json.loads(raw or "null")
        except ValueError:
            data = raw
        with self._lock:
            self._handle(topic, data)

    def _handle(self, topic, data):
        if topic.endswith("/authentication"):
            self.needs_pairing = True
        elif topic.endswith("/authenticationcode"):
            if isinstance(data, dict) and str(data.get("result")) == "1":
                if self.store.get("profile") == "legacy":
                    self._paired_ok()
                else:
                    self.publish(self._topic("platform_service", "data", "gettoken"), '{"refreshtoken": ""}')
                    self.publish(self._topic("ui_service", "actions", "authenticationcodeclose"))
            else:
                self.last_error = "The TV rejected that PIN. Try again."
        elif topic.endswith("/authenticationcodeclose"):
            self.last_error = "The pairing code closed on the TV."
        elif topic.endswith("/tokenissuance") and isinstance(data, dict):
            self.store.update(access_token=str(data.get("accesstoken", "")),
                              refresh_token=str(data.get("refreshtoken", "")),
                              token_time=int(time.time()))
            self._paired_ok()
        elif topic.endswith("/sourcelist") and isinstance(data, list):
            self.sources = data
            if self.store.get("sources_cache") != data:
                self.store.update(sources_cache=data)
        elif topic.endswith("/applist") and isinstance(data, list):
            # The icons inside are locked to the TV, so drop them.
            self.apps = [{k: v for k, v in a.items() if k != "httpIcon"} for a in data if isinstance(a, dict)]
            if self.store.get("apps_cache") != self.apps:
                self.store.update(apps_cache=self.apps)
        elif ("volumechange" in topic or topic.endswith("/getvolume")) and isinstance(data, dict):
            self._set_volume_seen(data.get("volume_value"))
        elif topic.endswith("/tvsleep"):
            self.asleep = True
        elif topic.endswith(("/getdeviceinfo", "/gettvinfo")) and isinstance(data, dict):
            self.info.update(data)
        elif topic.endswith(("/state", "/gettvstate")) and isinstance(data, dict):
            self._state_changed(data)

    def _state_changed(self, data):
        if data != self.state:
            events.add("tv", "showing " + json.dumps(data)[:90])
        kind = str(data.get("statetype", ""))
        was_asleep = self.asleep or self.state.get("statetype") == "fake_sleep_0"
        self.state = data
        if kind == "fake_sleep_0":                       # switched off into network standby
            self.asleep = True
        elif kind.startswith("fake_sleep"):              # waking up; wait for what comes next
            pass
        elif was_asleep:
            self.asleep = False
            if self.settings.get("own_home") and data.get("name") != "home":
                self._last_guard = time.time()
                events.add("hearth", f"woke into {kind}, opening home")
                threading.Thread(target=self.open_home, daemon=True).start()
        else:
            self._guard_home()

    def _guard_home(self):
        """VIDAA's launcher can't be removed, so whenever it shows, switch straight back to Hearth."""
        if not self.settings.get("own_home") or self.state.get("statetype") != "remote_launcher":
            return
        now = time.time()
        if now - self._last_guard < 4:
            return
        self._last_guard = now
        events.add("hearth", "launcher seen, opening home")
        threading.Thread(target=self.open_home, daemon=True).start()

    def _paired_ok(self):
        self.paired, self.needs_pairing, self.last_error = True, False, ""
        # The pairing session doesn't answer queries; a token session does.
        threading.Thread(target=self.connect, args=(self.ip,), daemon=True).start()

    def _set_volume_seen(self, value):
        if value is None or value == self.volume:
            return
        with self._vol_cond:
            self.volume = value
            self._vol_seq += 1
            self._vol_cond.notify_all()

    def wait_volume(self, seq, timeout=25):
        """Long-poll for the TV page: returns as soon as the volume changes."""
        with self._vol_cond:
            if seq == self._vol_seq:
                self._vol_cond.wait(timeout)
            return {"seq": self._vol_seq, "volume": self.volume}

    # ---- commands ----------------------------------------------------
    def publish(self, topic, payload=""):
        if not self.client:
            raise RuntimeError("not connected to the TV")
        self.client.publish(topic, payload if isinstance(payload, str) else json.dumps(payload))

    def refresh(self):
        for service, action in (("ui_service", "gettvstate"), ("platform_service", "getvolume"),
                                ("ui_service", "sourcelist"), ("ui_service", "applist"),
                                ("platform_service", "getdeviceinfo"), ("platform_service", "gettvinfo")):
            self.publish(self._topic(service, "actions", action))

    def poll_state(self):
        self.publish(self._topic("ui_service", "actions", "gettvstate"))

    def request_pin(self):
        self.publish(self._topic("ui_service", "actions", "vidaa_app_connect"),
                     '{"app_version":2,"connect_result":0,"device_type":"Mobile App"}')

    def pair(self, code):
        self.last_error = ""
        self.publish(self._topic("ui_service", "actions", "authenticationcode"), {"authNum": int(code)})

    def key(self, name):
        self.publish(self._topic("remote_service", "actions", "sendkey"), name)

    def set_volume(self, value):
        self.publish(self._topic("platform_service", "actions", "changevolume"), str(int(value)))

    def source(self, sourceid, sourcename):
        self.publish(self._topic("ui_service", "actions", "changesource"), {"sourceid": sourceid, "sourcename": sourcename})

    def launch(self, app):
        name, url = app.get("name"), app.get("url")
        self.publish(self._topic("ui_service", "actions", "launchapp"),
                     {"appId": app.get("appId"), "name": name, "url": url, "urlType": 37, "appName": name, "appUrl": url})

    def wake(self):
        network.wake_on_lan(self.store.get("mac", ""))

    # ---- keeping Hearth on screen ------------------------------------
    def open_home(self, url=None):
        already_open = self.state.get("name") == "home"
        opened = time.time()
        self.launch({"appId": "hearth", "name": "Home", "url": url or self.home_url()})
        if not already_open:   # the TV doesn't reload a page that's already showing, so only check fresh opens
            threading.Timer(7, self._check_loaded, args=(opened, url is None)).start()

    def page_ready(self):
        self.last_ready = time.time()

    def _check_loaded(self, opened_at, retry):
        """If the home page hasn't reported in, reload it from a fresh address."""
        if self.last_ready >= opened_at or self.state.get("name") != "home":
            return
        events.add("hearth", "home page didn't finish loading, reloading")
        if retry:
            self.open_home(f"{self.home_url()}?r={int(time.time())}")
