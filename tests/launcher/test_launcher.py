"""Integration tests against the real Java 8-targeted backend and HTTP fixtures."""
import contextlib
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct
import tempfile
import threading
import time
import unittest
import urllib.parse
import zipfile

REPO = Path(__file__).resolve().parents[2]
JDK = Path(os.environ.get("JAVA_HOME", str(REPO / ".deps/host-jdk/jdk-21.0.8+9")))
JAVA = Path(os.environ["JAVA"]) if "JAVA" in os.environ else next(
    (p for p in (JDK / "bin/java.exe", JDK / "bin/java") if p.is_file()),
    Path(shutil.which("java") or "java"))
JAVAC = next((p for p in (JDK / "bin/javac.exe", JDK / "bin/javac") if p.is_file()),
             Path(shutil.which("javac") or "javac"))
JAR = REPO / "artifacts/launcher/prosperomc-launcher.jar"


def zipped(entries):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, content in entries.items():
            z.writestr(name, content)
    return out.getvalue()


def pe64(machine=0x8664):
    """Minimal PE header fixture; never executes as a host program."""
    data = bytearray(512)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 60, 64)
    data[64:68] = b"PE\0\0"
    struct.pack_into("<H", data, 68, machine)
    struct.pack_into("<H", data, 84, 240)
    struct.pack_into("<H", data, 88, 0x20B)
    return bytes(data)


def props(path):
    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#"))


class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert JAVA.is_file(), "Build dependencies missing; run scripts/fetch-dependencies first"
        assert JAR.is_file(), "Build launcher before running tests"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=REPO / "artifacts")
        self.base = Path(self.temp.name)
        self.root = self.base / "data"
        self.root.mkdir()
        self.blobs = {}
        self.hits = []
        self.codes = {}
        blobs = self.blobs
        hits = self.hits
        codes = self.codes

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(handler):
                hits.append(handler.path)
                if handler.path in blobs:
                    handler.send_response(codes.get(handler.path,200))
                    handler.end_headers()
                    handler.wfile.write(blobs[handler.path])
                else:
                    handler.send_response(404)
                    handler.end_headers()
            def log_message(*args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%d" % self.server.server_port
        self.client = zipped({"fixture/Main.class": b"fixture"})
        self.library = zipped({"fixture/Library.class": b"fixture"})
        self.native = zipped({"lwjgl64.dll": b"native", "META-INF/MANIFEST.MF": b"skip"})
        self.asset = b"asset content"
        self.log = b"<Configuration/>"
        self.asset_hash = hashlib.sha1(self.asset).hexdigest()
        self.version = {
            "id": "1.12.2", "mainClass": "fixture.Main",
            "javaVersion": {"majorVersion": 8},
            "minecraftArguments": "--username ${auth_player_name} --token ${auth_access_token} --version ${version_name} --gameDir ${game_directory}",
            "downloads": {"client": self.blob("/client.jar", self.client)},
            "libraries": [
                {"name": "fixture:lib:1", "downloads": {"artifact": self.blob("/lib.jar", self.library, "fixture/lib/1/lib-1.jar")}},
                {"name": "fixture:linux:1", "rules": [{"action": "allow", "os": {"name": "linux"}}],
                 "downloads": {"artifact": {"path": "linux.jar", "url": self.url + "/MUST-NOT-DOWNLOAD"}}},
                {"name": "fixture:native:1", "natives": {"windows": "natives-windows-${arch}"},
                 "downloads": {"classifiers": {"natives-windows-64": self.blob("/native.jar", self.native, "fixture/native/1/native-win.jar")}}},
            ],
            "logging": {"client": {"argument": "-Dlog4j.configurationFile=${path}",
                                    "file": dict(self.blob("/log.xml", self.log), id="client-1.12.xml")}},
        }
        index = {"objects": {"sound/test.ogg": {"hash": self.asset_hash, "size": len(self.asset)}}, "virtual": True}
        self.version["assetIndex"] = dict(self.blob("/index.json", json.dumps(index).encode()), id="test-assets")
        self.blobs["/assets/" + self.asset_hash[:2] + "/" + self.asset_hash] = self.asset
        self.publish_version()
        self.java_fixture()
        self.request(command="settings", manifestUrl=self.url + "/manifest.json", assetsUrl=self.url + "/assets", accountMode="offline")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def blob(self, name, data, rel=None):
        self.blobs[name] = data
        result = {"url": self.url + name, "sha1": hashlib.sha1(data).hexdigest(), "size": len(data)}
        if rel:
            result["path"] = rel
        return result

    def publish_version(self):
        meta = json.dumps(self.version).encode()
        manifest = {"versions": [dict(self.blob("/version.json", meta), id=self.version["id"], type="release")]}
        self.blobs["/manifest.json"] = json.dumps(manifest).encode()

    def request(self, ok=True, **values):
        request = self.base / "request.properties"
        request.write_text("".join("%s=%s\n" % pair for pair in values.items()), encoding="utf-8")
        p = subprocess.run([str(JAVA), "-jar", str(JAR), "--root", str(self.root), "--request", str(request)], capture_output=True, text=True, timeout=40)
        response = props(self.root / "response.properties")
        self.assertEqual(response["ok"], "true" if ok else "false", p.stdout + p.stderr)
        self.assertEqual(p.returncode, 0 if ok else 1, p.stdout + p.stderr)
        return response

    def install(self, loader="vanilla"):
        self.request(command="create", id="fixture", name="Fixture", version="1.12.2", loader=loader)
        return self.request(command="install", id="fixture")

    def java_fixture(self, major=8):
        runtime = self.root / ("runtimes/java%d" % major)
        (runtime / "bin/server").mkdir(parents=True, exist_ok=True)
        (runtime / "bin/java.exe").write_bytes(pe64())
        (runtime / "bin/server/jvm.dll").write_bytes(pe64())
        (runtime / "release").write_text('JAVA_VERSION="%s.0.1"\nOS_NAME="Windows"\nOS_ARCH="amd64"\n' % ("1.8" if major == 8 else major))
        (self.root / "launcher").mkdir(exist_ok=True)
        shutil.copyfile(JAR, self.root / "launcher/prosperomc-launcher.jar")

    def publish_java(self, major, checksum=None, architecture="x64", release_arch="amd64", pe_machine=0x8664, include_jvm=True, kind="jre"):
        release = 'JAVA_VERSION="%s.0.1"\nOS_NAME="Windows"\nOS_ARCH="%s"\n' % ("1.8" if major == 8 else major, release_arch)
        files = {"jdk-test/release": release, "jdk-test/bin/java.exe": pe64(pe_machine)}
        if include_jvm:
            files["jdk-test/bin/server/jvm.dll"] = pe64(pe_machine)
        archive = zipped(files)
        self.blobs["/java%d.zip" % major] = archive
        binary = {"architecture": architecture, "os": "windows", "image_type": kind,
                  "package": {"link": self.url + "/java%d.zip" % major, "size": len(archive),
                              "checksum": checksum or hashlib.sha256(archive).hexdigest()}}
        key = "/java/assets/latest/%d/hotspot?architecture=x64&image_type=%s&os=windows&vendor=eclipse" % (major, kind)
        self.blobs[key] = json.dumps([{"binary": binary}]).encode()
        self.request(command="settings", javaApi=self.url + "/java")
        return key

    def remove_runtime(self, major):
        target = self.root / ("runtimes/java%d" % major)
        self.assertTrue(target.resolve().is_relative_to(self.root.resolve()))
        if target.exists():
            shutil.rmtree(target)

    def test_catalog_install_assets_rules_natives_logging(self):
        self.request(command="catalog")
        self.install()
        self.assertEqual((self.root / "assets/objects" / self.asset_hash[:2] / self.asset_hash).read_bytes(), self.asset)
        self.assertEqual((self.root / "assets/virtual/test-assets/sound/test.ogg").read_bytes(), self.asset)
        self.assertEqual((self.root / "instances/fixture/natives/lwjgl64.dll").read_bytes(), b"native")
        self.assertFalse((self.root / "instances/fixture/natives/META-INF").exists())
        self.assertFalse((self.root / "libraries/linux.jar").exists())
        self.assertEqual((self.root / "assets/log_configs/client-1.12.xml").read_bytes(), self.log)
        self.assertEqual(props(self.root / "instances/fixture/instance.properties")["installed"], "true")

    def test_integrity_failure_and_cache_repair(self):
        self.version["downloads"]["client"]["sha1"] = "0" * 40
        self.publish_version()
        self.request(command="create", id="fixture", version="1.12.2")
        error = self.request(ok=False, command="install", id="fixture")
        self.assertIn("integrity", error["message"])
        self.assertFalse((self.root / "versions/1.12.2/1.12.2.jar").exists())
        self.assertFalse(list(self.root.rglob("*.part")))

    def test_existing_corrupt_library_repaired(self):
        self.install()
        lib = self.root / "libraries/fixture/lib/1/lib-1.jar"
        lib.write_bytes(b"corrupt")
        self.request(command="install", id="fixture")
        self.assertEqual(lib.read_bytes(), self.library)

    def test_removed_empty_mojang_zip_reconstructed_exactly(self):
        empty = b"PK\x05\x06" + b"\0" * 18
        self.version["libraries"].append({"name": "org.lwjgl.lwjgl:lwjgl-platform:2.9.4-nightly-20150209", "downloads": {"artifact": {"path": "lwjgl-platform-empty.jar", "url": self.url + "/gone.jar", "sha1": hashlib.sha1(empty).hexdigest(), "size": 22}}})
        self.publish_version()
        self.install()
        self.assertEqual((self.root / "libraries/lwjgl-platform-empty.jar").read_bytes(), empty)
        self.version["libraries"][-1]["downloads"]["artifact"]["sha1"] = "f" * 40
        (self.root / "versions/1.12.2/1.12.2.json").unlink()
        self.publish_version()
        self.request(command="catalog")
        self.request(ok=False, command="install", id="fixture")

    def test_quilt_profile_and_ordered_rules(self):
        self.version["libraries"][1]["rules"] = [{"action": "allow"}, {"action": "disallow", "os": {"name": "windows"}}]
        self.version["libraries"].append({"name": "fixture:feature:1", "rules": [{"action": "allow", "features": {"is_demo_user": True}}], "downloads": {"artifact": {"path": "feature.jar", "url": self.url + "/MUST-NOT-DOWNLOAD"}}})
        self.publish_version()
        self.blobs["/quilt/versions/loader/1.12.2"] = json.dumps([{"loader": {"version": "0.26.0"}}]).encode()
        self.blobs["/quilt/versions/loader/1.12.2/0.26.0/profile/json"] = json.dumps({"mainClass": "org.quiltmc.loader.impl.launch.knot.KnotClient", "libraries": []}).encode()
        self.request(command="settings", quiltApi=self.url + "/quilt")
        self.install("quilt")
        self.assertFalse((self.root / "libraries/linux.jar").exists())
        self.assertFalse((self.root / "libraries/feature.jar").exists())

    def test_native_archive_traversal_refused(self):
        self.native = zipped({"../../escape.dll": b"bad"})
        self.version["libraries"][2]["downloads"]["classifiers"]["natives-windows-64"] = self.blob("/native.jar", self.native, "fixture/native/1/native-win.jar")
        self.publish_version()
        self.request(command="create", id="fixture", version="1.12.2")
        result = self.request(ok=False, command="install", id="fixture")
        self.assertIn("escapes", result["message"])
        self.assertFalse((self.root / "instances/escape.dll").exists())

    def test_library_path_traversal_refused(self):
        self.version["libraries"][0]["downloads"]["artifact"]["path"] = "../../escape.jar"
        self.publish_version()
        self.request(command="create", id="fixture", version="1.12.2")
        self.request(ok=False, command="install", id="fixture")
        self.assertFalse((self.base / "escape.jar").exists())

    def test_invalid_id_unknown_command_and_loader_fail_explicitly(self):
        self.request(ok=False, command="create", id="../evil", version="1.12.2")
        result = self.request(ok=False, command="create", id="forge", version="1.20.1", loader="forge")
        self.assertIn("Forge support", result["message"])
        self.request(ok=False, command="anything")
        self.request(ok=False, command="auth-poll")

    def test_fabric_mods_clone_and_export_import(self):
        profile = {"mainClass": "net.fabricmc.loader.impl.launch.knot.KnotClient", "libraries": []}
        self.blobs["/fabric/versions/loader/1.12.2"] = json.dumps([{"loader": {"version": "0.16.0", "stable": True}}]).encode()
        self.blobs["/fabric/versions/loader/1.12.2/0.16.0/profile/json"] = json.dumps(profile).encode()
        self.request(command="settings", fabricApi=self.url + "/fabric")
        self.install("fabric")
        source = self.base / "testmod.jar"
        source.write_bytes(zipped({"fabric.mod.json": b"{}"}))
        self.request(command="mod-add", id="fixture", source=source)
        self.request(command="mod-toggle", id="fixture", mod="testmod.jar", enabled="false")
        self.assertTrue((self.root / "instances/fixture/.minecraft/mods/testmod.jar.disabled").exists())
        self.request(command="mod-toggle", id="fixture", mod="testmod.jar.disabled", enabled="true")
        self.request(command="clone", id="fixture")
        self.assertTrue((self.root / "instances/fixture-copy/instance.properties").exists())
        game = self.root / "instances/fixture/.minecraft"
        (game / "launcher_accounts.json").write_text("DO NOT COPY SECRET")
        self.request(command="export", id="fixture")
        exported = self.root / "exports/fixture.zip"
        with zipfile.ZipFile(exported) as z:
            self.assertIn("mmc-pack.json", z.namelist())
            self.assertNotIn(".minecraft/launcher_accounts.json", z.namelist())
            pack = json.loads(z.read("mmc-pack.json"))
            self.assertEqual(pack["components"][1]["version"], "0.16.0")
        self.request(command="import-pack", id="imported", source=exported)
        self.assertEqual(props(self.root / "instances/imported/instance.properties")["loader"], "fabric")
        self.request(command="install", id="imported")

    def test_modrinth_pack_overrides_and_client_environment(self):
        pack = self.base / "sample.mrpack"
        manifest = {"formatVersion": 1, "game": "minecraft", "name": "Client Pack",
                    "dependencies": {"minecraft": "1.12.2", "forge": "14.23.5.2859"},
                    "files": [{"path": "mods/server-only.jar", "env": {"client": "unsupported"}}]}
        pack.write_bytes(zipped({"modrinth.index.json": json.dumps(manifest),
                                 "overrides/config/test.cfg": b"base",
                                 "client-overrides/config/test.cfg": b"client",
                                 "server-overrides/config/test.cfg": b"server",
                                 "overrides/launcher_accounts.json": b"PRIVATE"}))
        self.request(command="import-pack", id="pack", source=pack)
        game = self.root / "instances/pack/.minecraft"
        self.assertEqual((game / "config/test.cfg").read_bytes(), b"client")
        self.assertFalse((game / "mods/server-only.jar").exists())
        self.assertFalse((game / "launcher_accounts.json").exists())
        self.assertEqual(props(game.parent / "instance.properties")["loader"], "forge")

    def test_modrinth_pack_rejects_bad_paths_hashes_and_unknown_loaders(self):
        pack = self.base / "invalid.mrpack"
        manifest = {"formatVersion": 1, "game": "minecraft", "name": "Bad Pack",
                    "dependencies": {"minecraft": "1.12.2"},
                    "files": [{"path": "../outside.jar"}]}
        for entry in ({"path": "../outside.jar"}, {"path": "mods/bad.jar", "hashes": {"sha1": "bad"}}):
            manifest["files"] = [entry]
            pack.write_bytes(zipped({"modrinth.index.json": json.dumps(manifest)}))
            self.request(ok=False, command="import-pack", id="bad", source=pack)
            self.assertFalse((self.root / "instances/bad").exists())
        manifest["dependencies"]["neoforge"] = "1.0"
        manifest["files"] = []
        pack.write_bytes(zipped({"modrinth.index.json": json.dumps(manifest)}))
        self.request(ok=False, command="import-pack", id="bad", source=pack)
        self.assertFalse((self.root / "instances/bad").exists())

    def remote_pack_fixture(self):
        self.request(command="settings", modrinthApi=self.url + "/modrinth")
        archive=zipped({"modrinth.index.json":json.dumps({"formatVersion":1,"game":"minecraft",
            "name":"Remote Pack","dependencies":{"minecraft":"1.12.2"},"files":[]}),
            "overrides/config/test.cfg":b"pack config"})
        cache=self.root / "imports/project-release.mrpack"
        cache.parent.mkdir(exist_ok=True)
        cache.write_bytes(archive)
        file={"filename":"pack.mrpack","primary":True,"url":"https://cdn.modrinth.com/data/project/versions/release/pack.mrpack",
              "size":len(archive),"hashes":{"sha1":hashlib.sha1(archive).hexdigest(),"sha512":hashlib.sha512(archive).hexdigest()}}
        metadata={"id":"release","project_id":"project","name":"Remote Pack release",
                  "game_versions":["1.12.2"],"loaders":["minecraft"],"files":[file]}
        self.blobs["/modrinth/version/release"]=json.dumps(metadata).encode()
        self.blobs["/modrinth/project/project/version"]=json.dumps([metadata]).encode()
        return metadata

    def test_remote_modpack_search_pagination_and_release_selection(self):
        self.remote_pack_fixture()
        query="Fabulously Optimized"
        suffix="?limit=24&offset=24&index=relevance&facets="+urllib.parse.quote_plus('[["project_type:modpack"]]')+"&query="+urllib.parse.quote_plus(query)
        self.blobs["/modrinth/search"+suffix]=json.dumps({"total_hits":25,"hits":[
            {"project_type":"modpack","project_id":"project","title":"Pack","description":"Description\nline"}]}).encode()
        self.request(command="pack-search",query=query,offset="24")
        view=props(self.root / "launcher-view.properties")
        self.assertEqual(view["remote.pack.0.id"],"project")
        self.assertEqual(view["remote.offset"],"24")
        self.assertEqual(view["remote.pack.0.description"],"Description line")
        self.request(command="pack-versions",projectId="project")
        self.assertEqual(props(self.root / "launcher-view.properties")["remote.version.0.id"],"release")
        self.request(ok=False,command="pack-versions",projectId="missing")
        self.assertEqual(props(self.root / "launcher-view.properties")["remote.version.count"],"0")

    def test_remote_pack_installs_game_runtime_and_resumes_failed_install(self):
        self.remote_pack_fixture()
        self.remove_runtime(8);self.publish_java(8)
        client=self.blobs.pop("/client.jar")
        self.request(ok=False,command="pack-download",projectId="project",packVersion="release")
        folder=self.root / "instances/modrinth-project-release"
        self.assertEqual(props(folder / "instance.properties")["installed"],"false")
        self.assertEqual((folder / ".minecraft/config/test.cfg").read_bytes(),b"pack config")
        self.blobs["/client.jar"]=client
        self.request(command="pack-download",projectId="project",packVersion="release")
        self.assertEqual(props(folder / "instance.properties")["installed"],"true")
        self.assertTrue((self.root / "runtimes/java8/bin/server/jvm.dll").exists())
        self.assertTrue((folder / "natives/lwjgl64.dll").exists())
        self.assertTrue((self.root / "assets/objects" / self.asset_hash[:2] / self.asset_hash).exists())
        before=len(self.hits)
        self.request(command="pack-download",projectId="project",packVersion="release")
        self.assertEqual(self.hits[before:],["/modrinth/version/release"])

    def test_remote_pack_rejects_archive_hash_and_project_mismatch(self):
        metadata=self.remote_pack_fixture()
        self.request(ok=False,command="pack-download",projectId="other",packVersion="release")
        metadata["files"][0]["hashes"]["sha512"]="0"*128
        self.blobs["/modrinth/version/release"]=json.dumps(metadata).encode()
        response=self.request(ok=False,command="pack-download",projectId="project",packVersion="release")
        self.assertIn("SHA512 mismatch",response["message"])
        self.assertFalse((self.root / "instances/modrinth-project-release").exists())

    def test_pack_zip_traversal_and_unsupported_components(self):
        pack = self.base / "evil.zip"
        pack.write_bytes(zipped({"../../escape.txt": b"BAD"}))
        self.request(ok=False, command="import-pack", id="evil", source=pack)
        self.assertFalse((self.root / "escape.txt").exists())
        pack.write_bytes(zipped({"mmc-pack.json": json.dumps({"components": [{"uid": "net.minecraft", "version": "1.12.2"}, {"uid": "net.neoforged", "version": "1.0"}]})}))
        result = self.request(ok=False, command="import-pack", id="evil", source=pack)
        self.assertIn("Forge", result["message"])
        self.assertFalse((self.root / "instances/evil").exists())

    def test_local_import_excludes_credentials_and_checks_client(self):
        source = self.base / "local/.minecraft"
        version = source / "versions/1.12.2"
        version.mkdir(parents=True)
        (version / "1.12.2.json").write_text(json.dumps(self.version))
        (version / "1.12.2.jar").write_bytes(self.client)
        (source / "launcher_accounts.json").write_text("PRIVATE")
        self.request(command="import", id="local", version="1.12.2", source=source)
        self.assertFalse(list(self.root.rglob("launcher_accounts.json")))
        (version / "1.12.2.jar").write_bytes(b"tampered")
        self.request(ok=False, command="import", id="corrupt", version="1.12.2", source=source)
        self.assertFalse((self.root / "instances/corrupt").exists())

    def test_microsoft_provider_default_and_custom_id(self):
        self.request(command="settings", microsoftClientId="")
        self.assertEqual(props(self.root / "launcher-view.properties")["auth.provider"], "PolyMC")
        custom="12345678-1234-1234-1234-123456789abc"
        self.request(command="settings", microsoftClientId=custom)
        self.assertEqual(props(self.root / "settings.properties")["microsoftClientId"],custom)
        self.assertEqual(props(self.root / "launcher-view.properties")["auth.provider"], "Custom application")

    def test_account_display_name_and_completed_check(self):
        private=self.root / "private"
        private.mkdir()
        (private / "account.json").write_text(json.dumps({"name":"OwnedPlayer","uuid":"a"*32,"accessToken":"PRIVATE-TOKEN"}))
        self.request(command="settings",accountMode="microsoft",username="OfflineName")
        view=props(self.root / "launcher-view.properties")
        self.assertEqual(view["auth.username"],"OwnedPlayer")
        self.assertEqual(view["settings.username"],"OfflineName")
        self.assertNotIn("PRIVATE-TOKEN",(self.root / "launcher-view.properties").read_text())
        response=self.request(command="auth-poll")
        self.assertIn("already signed in",response["message"])
        self.request(command="settings",accountMode="offline")
        self.assertEqual(props(self.root / "launcher-view.properties")["settings.username"],"OfflineName")

    def test_prepare_jvm_exact_logging_dynamic_java_and_no_secrets(self):
        self.version["javaVersion"]["majorVersion"] = 25
        self.version["arguments"] = {"jvm": ["-Djava.library.path=${natives_directory}", "-cp", "${classpath}", {"rules": [{"action": "allow", "os": {"name": "windows"}}], "value": "-Dos.name=Windows 10"}], "game": ["--accessToken", "${auth_access_token}", "--username", "${auth_player_name}"]}
        self.publish_version()
        self.java_fixture(25)
        self.install()
        self.java_fixture(25)
        account = self.root / "private/account.json"
        account.parent.mkdir()
        account.write_text(json.dumps({"name": "OwnedPlayer", "uuid": "a" * 32, "accessToken": "DO-NOT-EXPOSE", "expiresAt": int(time.time() * 1000) + 99999999}))
        self.request(command="settings", resolution="1920x1080")
        self.request(command="prepare-launch", id="fixture", accountMode="microsoft")
        profile = (self.root / "profiles/launch.profile").read_text()
        plan = (self.root / "profiles/launch-plan.json").read_text()
        self.assertIn("java25", profile)
        self.assertIn("-XX:+UseParallelGC", profile)
        self.assertIn("desktop=1920x1080", profile)
        arguments=json.loads(plan)["arguments"]
        self.assertEqual(arguments[arguments.index("--width")+1], "1920")
        self.assertEqual(arguments[arguments.index("--height")+1], "1080")
        self.assertIn("settings.resolution=1920x1080", (self.root / "launcher-view.properties").read_text())
        self.request(ok=False, command="settings", resolution="wrong")
        self.assertIn("-Dlog4j.configurationFile=", profile)
        self.assertIn("client-1.12.xml", profile)
        self.assertIn("org.prosperomc.Main", profile)
        self.assertIn("--execute-plan", profile)
        self.assertIn("${auth_access_token}", plan)
        for file in ("profiles/launch.profile", "profiles/launch-plan.json", "launcher-view.properties", "response.properties", "progress.properties"):
            self.assertNotIn("DO-NOT-EXPOSE", (self.root / file).read_text())

    def test_resolution_presets_persist_into_game_and_desktop(self):
        self.install()
        self.java_fixture()
        for resolution in ("1280x720", "1920x1080", "2560x1440", "3840x2160"):
            self.request(command="settings", resolution=resolution)
            self.request(command="prepare-launch", id="fixture")
            profile=(self.root / "profiles/launch.profile").read_text()
            args=json.loads((self.root / "profiles/launch-plan.json").read_text())["arguments"]
            width,height=resolution.split("x")
            self.assertIn("desktop="+resolution,profile)
            self.assertEqual(args[args.index("--width")+1],width)
            self.assertEqual(args[args.index("--height")+1],height)
            self.assertEqual(props(self.root / "settings.properties")["resolution"],resolution)

    def test_prepare_corrupt_client_and_java_mismatch_fail(self):
        self.install()
        self.java_fixture()
        self.request(command="prepare-launch", id="fixture")
        (self.root / "versions/1.12.2/1.12.2.jar").write_bytes(b"wrong")
        self.request(ok=False, command="prepare-launch", id="fixture")
        self.assertFalse((self.root / "profiles/launch.profile").exists())
        (self.root / "runtimes/java8/release").write_text('JAVA_VERSION="17.0.1"\nOS_ARCH="amd64"')
        result = self.request(ok=False, command="prepare-launch", id="fixture")
        self.assertIn("required Java", result["message"])

    def test_actual_same_jvm_entrypoint_resolves_secret_in_memory(self):
        self.install()
        self.java_fixture()
        self.request(command="prepare-launch", id="fixture")
        source = self.base / "fixture/Main.java"
        source.parent.mkdir()
        source.write_text('package fixture; public class Main { public static void main(String[] a) { System.out.println("FIXTURE-" + a[3]); } }')
        subprocess.run([str(JAVAC), "--release", "8", "-d", str(self.base / "classes"), str(source)], check=True, capture_output=True)
        process = subprocess.run([str(JAVA), "-cp", str(JAR) + os.pathsep + str(self.base / "classes"), "org.prosperomc.Main", "--root", str(self.root), "--execute-plan", str(self.root / "profiles/launch-plan.json")], capture_output=True, text=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("FIXTURE-0", process.stdout)

    def test_modrinth_pinned_required_dependency(self):
        self.blobs["/fabric/versions/loader/1.12.2"] = json.dumps([{"loader": {"version": "0.16.0"}}]).encode()
        self.blobs["/fabric/versions/loader/1.12.2/0.16.0/profile/json"] = json.dumps({"mainClass": "fixture.Main", "libraries": []}).encode()
        self.request(command="settings", fabricApi=self.url + "/fabric", modrinthApi=self.url + "/modrinth")
        self.install("fabric")
        main_mod = zipped({"fabric.mod.json": b"{}"})
        required_old = zipped({"version": b"pinned version"})
        required_new = zipped({"version": b"newest incompatible with main mod"})
        def file(name, body):
            spec = self.blob("/" + name, body)
            return {"filename": name, "url": spec["url"], "size": len(body), "hashes": {"sha1": spec["sha1"]}, "primary": True}
        query = "?loaders=" + urllib.parse.quote('["fabric"]', safe="") + "&game_versions=" + urllib.parse.quote('["1.12.2"]', safe="")
        self.blobs["/modrinth/project/main/version" + query] = json.dumps([{"id": "main-v1", "files": [file("main.jar", main_mod)], "dependencies": [{"dependency_type": "required", "project_id": "dep", "version_id": "dep-old"}]}]).encode()
        self.blobs["/modrinth/project/dep/version" + query] = json.dumps([{"id": "dep-new", "files": [file("dep-new.jar", required_new)]}, {"id": "dep-old", "files": [file("dep-old.jar", required_old)]}]).encode()
        self.request(command="mod-download", id="fixture", projectId="main")
        mods = self.root / "instances/fixture/.minecraft/mods"
        self.assertTrue((mods / "main.jar").exists())
        self.assertEqual((mods / "dep-old.jar").read_bytes(), required_old)
        self.assertFalse((mods / "dep-new.jar").exists())

    def test_metadata_cycle_and_duplicate_keys_fail(self):
        self.version["inheritsFrom"] = "parent"
        self.publish_version()
        parent = self.root / "versions/parent/parent.json"
        parent.parent.mkdir(parents=True)
        parent.write_text(json.dumps({"id": "parent", "inheritsFrom": "1.12.2"}))
        self.request(command="create", id="cycle", version="1.12.2")
        error = self.request(ok=False, command="install", id="cycle")
        self.assertIn("inheritance", error["message"])
        (self.root / "versions/1.12.2/1.12.2.json").write_text('{"id":"1.12.2","id":"1.12.2"}')
        error = self.request(ok=False, command="install", id="cycle")
        self.assertIn("duplicate", error["message"])

    def test_native_exclusion_and_state_reader_interference(self):
        self.native = zipped({"lwjgl64.dll": b"native", "excluded/note.txt": b"skip"})
        self.version["libraries"][2]["extract"] = {"exclude": ["excluded/"]}
        self.version["libraries"][2]["downloads"]["classifiers"]["natives-windows-64"] = self.blob("/native.jar", self.native, "fixture/native/1/native-win.jar")
        self.publish_version()
        self.install()
        self.assertFalse((self.root / "instances/fixture/natives/excluded").exists())
        handle = open(self.root / "progress.properties", "r")
        timer = threading.Timer(0.4, handle.close)
        timer.start()
        try:
            self.request(command="view")
        finally:
            timer.join()
            handle.close()

    def test_device_view_preserves_public_code_without_secret(self):
        pending = self.root / "private/auth-pending.json"
        pending.parent.mkdir()
        pending.write_text(json.dumps({"user_code": "PUBLIC-CODE", "verification_uri": "https://microsoft.com/link", "device_code": "PRIVATE-DEVICE-CODE", "interval": 5, "expiresAt": int(time.time()*1000)+100000, "nextPollAt": int(time.time()*1000)+100000}))
        self.request(command="view")
        view = props(self.root / "launcher-view.properties")
        self.assertEqual(view["auth.userCode"], "PUBLIC-CODE")
        self.assertNotIn("PRIVATE-DEVICE-CODE", (self.root / "launcher-view.properties").read_text())

    def test_device_poll_clock_and_automatic_checks(self):
        classes=self.base / "auth-classes"
        classes.mkdir()
        subprocess.run([str(JAVAC),"--release","8","-cp",str(JAR),"-d",str(classes),
                        str(REPO / "tests/runtime/AuthSmoke.java")],check=True,capture_output=True)
        run=subprocess.run([str(JAVA),"-cp",str(classes)+os.pathsep+str(JAR),
                            "org.prosperomc.AuthSmoke",str(self.root)],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertIn("PASS:",run.stdout)

    def test_dynamic_catalog_search_and_unadvertised_library_hash(self):
        self.request(command="catalog")
        self.blobs["/manifest.json"] = json.dumps({"versions": [{"id": "new-version", "type": "release"}]}).encode()
        self.request(command="catalog")
        self.assertEqual(props(self.root / "launcher-view.properties")["version.0.id"], "new-version")
        for query in ("first", "second"):
            self.blobs["/modrinth/search?limit=20&query=" + query] = json.dumps({"hits": [{"project_id": query, "title": query, "description": "result"}]}).encode()
        self.request(command="settings", modrinthApi=self.url + "/modrinth")
        self.request(command="mod-search", query="first")
        self.request(command="mod-search", query="second")
        self.assertEqual(props(self.root / "launcher-view.properties")["search.0.id"], "second")
        lib = zipped({"library": b"verified sidecar"})
        self.blobs["/fixture/sidecar/1/sidecar-1.jar"] = lib
        self.blobs["/fixture/sidecar/1/sidecar-1.jar.sha1"] = hashlib.sha1(lib).hexdigest().encode()
        self.version["libraries"].append({"name": "fixture:sidecar:1", "url": self.url + "/"})
        self.publish_version()
        self.request(command="catalog")
        self.install()
        installed = json.loads((self.root / "instances/fixture/installed.json").read_text())
        self.assertEqual(installed["libraries"][-1]["downloads"]["artifact"]["sha1"], hashlib.sha1(lib).hexdigest())
        self.java_fixture()
        self.request(command="prepare-launch", id="fixture")
        (self.root / "libraries/fixture/sidecar/1/sidecar-1.jar").write_bytes(b"tampered")
        result = self.request(ok=False, command="prepare-launch", id="fixture")
        self.assertIn("corrupt library", result["message"])

    def test_all_catalog_entries_reachable_beyond_old_cap(self):
        versions = [{"id": "snapshot-%d" % n, "type": "snapshot"} for n in range(600)]
        versions.append({"id": "1.12.2", "type": "release"})
        self.blobs["/manifest.json"] = json.dumps({"versions": versions}).encode()
        self.request(command="catalog")
        view = props(self.root / "launcher-view.properties")
        self.assertEqual(view["version.count"], "601")
        self.assertEqual(view["version.600.id"], "1.12.2")
        self.assertEqual(view["version.600.java"], "0")

    def test_auto_java_provisioning_selected_versions_8_17_21_25(self):
        for major in (8, 17, 21, 25):
            with self.subTest(major=major):
                self.remove_runtime(major)
                self.publish_java(major)
                self.version["id"] = "mc-java%d" % major
                self.version["javaVersion"]["majorVersion"] = major
                self.publish_version()
                self.request(command="catalog")
                self.request(command="create-install", id="instance%d" % major,
                             version=self.version["id"], name="Selected version")
                runtime = self.root / ("runtimes/java%d" % major)
                self.assertTrue((runtime / "bin/java.exe").is_file())
                self.assertTrue((runtime / "bin/server/jvm.dll").is_file())
                self.assertEqual(props(self.root / ("instances/instance%d/instance.properties" % major))["installed"], "true")
        self.request(command="detect-java")
        view = props(self.root / "launcher-view.properties")
        self.assertEqual(view["java.count"], "4")
        self.assertEqual([view["java.%d.major" % n] for n in range(4)], ["8", "17", "21", "25"])
        self.assertTrue(all(view["java.%d.valid" % n] == "true" for n in range(4)))

    def test_valid_java_reused_without_api_or_archive_download(self):
        self.request(command="settings", javaApi=self.url + "/unavailable-java")
        self.install()
        self.request(command="install-java", major="8")
        self.request(command="prepare-launch", id="fixture")
        self.assertFalse(any("/assets/latest/" in hit or "java8.zip" in hit for hit in self.hits))

    def test_prepare_provisions_required_java_after_runtime_removed(self):
        self.install()
        self.remove_runtime(8)
        self.publish_java(8)
        self.request(command="prepare-launch", id="fixture")
        self.assertTrue((self.root / "runtimes/java8/bin/server/jvm.dll").is_file())
        self.assertIn("java8", (self.root / "profiles/launch.profile").read_text())

    def test_java_bad_checksum_does_not_publish_runtime(self):
        self.remove_runtime(8)
        self.publish_java(8, checksum="0" * 64)
        result = self.request(ok=False, command="create-install", id="bad-java", version="1.12.2")
        self.assertIn("SHA256 mismatch", result["message"])
        self.assertFalse((self.root / "runtimes/java8").exists())
        self.assertFalse((self.root / "cache/java8.zip").exists())
        self.assertEqual(props(self.root / "instances/bad-java/instance.properties")["installed"], "false")

    def test_java_provider_and_release_wrong_architecture_rejected(self):
        self.remove_runtime(8)
        key = self.publish_java(8, architecture="aarch64")
        result = self.request(ok=False, command="install-java", major="8")
        self.assertIn("wrong architecture", result["message"])
        self.assertFalse((self.root / "runtimes/java8").exists())
        self.publish_java(8, release_arch="x86")
        result = self.request(ok=False, command="install-java", major="8")
        self.assertIn("Windows x64", result["message"])
        self.assertFalse((self.root / "runtimes/java8").exists())
        self.publish_java(8, pe_machine=0x14C)
        result = self.request(ok=False, command="install-java", major="8")
        self.assertIn("PE32+", result["message"])
        self.assertFalse((self.root / "runtimes/java8").exists())

    def test_missing_jvm_reported_and_explicit_repair_preserves_old_files(self):
        (self.root / "runtimes/java8/bin/server/jvm.dll").unlink()
        self.request(command="detect-java")
        view = props(self.root / "launcher-view.properties")
        self.assertEqual(view["java.0.valid"], "false")
        self.assertIn("jvm.dll", view["java.0.detail"])
        self.publish_java(8)
        result = self.request(ok=False, command="install-java", major="8")
        self.assertIn("repair=true", result["message"])
        self.request(command="install-java", major="8", repair="true")
        self.assertTrue((self.root / "runtimes/java8/bin/server/jvm.dll").is_file())
        self.assertEqual(len(list((self.root / "cache").glob("java8-invalid-*"))), 1)

    def test_java16_jre_unavailable_falls_back_to_matching_jdk(self):
        self.publish_java(16, kind="jdk")
        self.blobs["/java/assets/latest/16/hotspot?architecture=x64&image_type=jre&os=windows&vendor=eclipse"] = b"[]"
        self.request(command="install-java", major="16")
        self.assertTrue((self.root / "runtimes/java16/bin/java.exe").is_file())
        self.assertEqual(props(self.root / "launcher-view.properties")["java.1.major"], "16")

    def test_java_api_failure_uses_official_release_asset_and_hash(self):
        key=self.publish_java(17)
        self.codes[key]=503
        archive=self.blobs["/java17.zip"]
        asset={"name":"OpenJDK17U-jre_x64_windows_hotspot_17.0.0_1.zip","size":len(archive),
               "browser_download_url":self.url+"/java17.zip","digest":"sha256:"+hashlib.sha256(archive).hexdigest()}
        self.blobs["/github/repos/adoptium/temurin17-binaries/releases/latest"]=json.dumps({"assets":[asset]}).encode()
        self.request(command="settings",javaGithubApi=self.url+"/github")
        self.request(command="install-java",major="17")
        self.assertTrue((self.root / "runtimes/java17/bin/server/jvm.dll").is_file())
        self.remove_runtime(17)
        asset["digest"]="sha256:"+"0"*64
        self.blobs["/github/repos/adoptium/temurin17-binaries/releases/latest"]=json.dumps({"assets":[asset]}).encode()
        response=self.request(ok=False,command="install-java",major="17")
        self.assertIn("SHA256 mismatch",response["message"])
        self.assertFalse((self.root / "runtimes/java17").exists())

    def test_java_no_jre_or_jdk_descriptive_error(self):
        self.request(command="settings", javaApi=self.url + "/java")
        result = self.request(ok=False, command="install-java", major="16")
        self.assertIn("No Windows x64 Java 16 JRE or JDK", result["message"])
        self.assertFalse((self.root / "runtimes/java16").exists())

    def test_class_files_target_java8(self):
        with zipfile.ZipFile(JAR) as z:
            for n in z.namelist():
                if n.endswith(".class"):
                    data = z.read(n)
                    expected=62 if n.startswith("org/prosperomc/Ps5ResolverProvider") else 52
                    self.assertEqual(int.from_bytes(data[6:8], "big"), expected, n)

    def test_persistent_worker_handles_failure_then_settings_without_restart(self):
        process = subprocess.Popen([str(JAVA), "-jar", str(JAR), "--root", str(self.root), "--serve"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def wait_for(path):
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if path.is_file():
                    return
                self.assertIsNone(process.poll(), "Worker unexpectedly exited")
                time.sleep(.02)
            self.fail("Worker response timed out")
        def submit(content):
            response = self.root / "response.properties"
            response.unlink(missing_ok=True)
            temporary = self.root / "request.properties.tmp"
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(self.root / "request.properties")
            wait_for(response)
            result = props(response)
            deadline = time.monotonic() + 5
            while (self.root / "request.inflight.properties").exists() and time.monotonic() < deadline:
                time.sleep(.01)
            return result
        try:
            wait_for(self.root / "backend-ready.properties")
            pid = process.pid
            self.assertEqual(submit("command=invalid-command\n")["ok"], "false")
            self.assertEqual(submit("command=settings\nmemoryMb=4096\naccountMode=offline\n")["ok"], "true")
            self.assertEqual(props(self.root / "settings.properties")["memoryMb"], "4096")
            self.assertEqual(submit("command=settings\naccountMode=microsoft\n")["ok"], "true")
            self.assertEqual(props(self.root / "launcher-view.properties")["settings.accountMode"], "microsoft")
            self.assertEqual(process.pid, pid)
            self.assertIsNone(process.poll())
            self.install()
            self.assertEqual(submit("command=prepare-launch\nid=fixture\naccountMode=offline\nusername=Player\n")["ok"], "true")
            self.assertEqual(process.wait(timeout=10), 0)
            self.assertTrue((self.root / "profiles/launch.profile").is_file())
        finally:
            process.terminate()
            process.communicate(timeout=10)


if __name__ == "__main__":
    unittest.main()
