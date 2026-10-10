# CurseForge modpacks

**Add Instance → CurseForge** uses the [official REST API](https://docs.curseforge.com/rest-api/)
to search Minecraft modpacks, show release files and resolve a pack's pinned
project/file IDs. This API requires an `x-api-key`; ProsperoMC does not ship a
borrowed launcher key.

Request API access through [CurseForge for Studios](https://console.curseforge.com/).
Keep your key in `/data/ProsperoMC/private/curseforge.properties`:

```properties
apiKey=YOUR_OWN_API_KEY
```

This file is private configuration, separate from the public settings and
account display. Do not commit it or include it in bug reports. You can also
set or clear it using the launcher's `settings` command and the
`curseforgeApiKey` request property; the value is stored only in the private
file. The native UI never displays the key.

CurseForge downloads verify file length and the API's SHA1/MD5 hashes before
copying files into an instance. A blocked or unavailable `downloadUrl` is an
explicit failure, following CurseForge's [publisher distribution setting](https://support.curseforge.com/support/solutions/articles/9000207877).
ProsperoMC does not derive hidden URLs to bypass that setting. A missing API
key, rejected key or blocked project produces a clear launcher message.

An exported CurseForge ZIP can be placed in `/data/ProsperoMC/imports` and
selected with **Add Instance → Import Pack**. Its `manifest.json` is imported
through the same pinned-file API, and its overrides are copied into the
instance after verifying the downloads. Fabric, Quilt, vanilla and Forge for
Minecraft 1.12.2 are supported. Modern Forge and NeoForge processor installation
is not implemented yet; those packs fail clearly before creating a playable
instance.

The host integration tests cover key privacy, missing access, search/release
selection, pinned manifest file downloads, SHA1/MD5 checks, resume behavior,
publisher restrictions, external download URLs and archive path traversal.
Live CurseForge browsing still needs a user-owned key and console verification.
