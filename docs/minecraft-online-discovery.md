# Minecraft server discovery on PS5

The user confirms the theme persists after Minecraft, louder sounds work, VRR
is reachable, Home trim/icon plates are removed, pack names are correct and F3
shows the selected 2560×1440. No additional UI/audio repair is made here.

All 20 current diagnostic files were read into `online-theme-analysis.json`.
Fresh sessions 4/5/6 are launcher, game and returned launcher. The public settings
snapshot confirms Ocean/Stable refresh, Microsoft mode with a signed-in account,
and the user's selected 7168 MiB heap. That budget is preserved. Game 5 logs
SRV and e4mc directory discovery failing in Windows GetAdaptersAddresses,
followed by an unknown-host result for bomba.bendermc.com. LAN interface discovery
also warns; internet discovery is the scope of this repair.

Read-only public DoH queries in `public-server-dns-probe.json` show hypixel.net
has website A records and `_minecraft._tcp.hypixel.net` redirects to
mc.hypixel.net:25565. The latter has an IPv4 A record and no SRV is needed.
bomba.bendermc.com and its Minecraft SRV name both returned NXDOMAIN; the user
confirmed it was a web search result and requested a valid test server.
No fabricated IP, permanent server-IP mapping or server-list rewrite is used.

Minecraft 26.2's actual ServerRedirectHandler calls InitialDirContext with the
standard DNS factory and default `dns:` URL. The native Windows provider tries
unsupported adapter enumeration. `Ps5DirectoryDns` installs the supported
[JNDI factory builder](https://docs.oracle.com/javase/8/docs/api/javax/naming/spi/NamingManager.html)
before Minecraft's class loader starts and supplies SRV/TXT/A attributes through
the existing verified HTTPS DNS transport. Only default DNS contexts use this
adapter. Explicit DNS-server URLs and other initial context factories delegate.
Case-insensitive attributes match the real client's `get("srv")`; mod TXT data
retains its DNS string form. Unimplemented directory operations fail explicitly.

`Ps5Dns` now supports the underscore-bearing DNS service names and validates
SRV port/priority/weight/target fields. NXDOMAIN/empty answers remain absent,
an explicit service-unavailable target remains absent, and truncated, oversized
or malformed replies fail. DNS HTTPS and destination TLS certificate checks
retain JVM defaults. [Cloudflare's JSON DoH contract](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/)
is the upstream transport reference.

Console launch arguments also set the hostname-provider flag before JVM agents
and early network initialization can select a resolver. Host launch arguments
are unchanged. The existing early modern resolver initialization remains.
Provider activation is logged. This addresses an initialization-order hazard;
the captured console logs prove the directory-discovery failure, not that every
hostname failure came from that timing hazard.

Java 17 predates the public hostname-resolver SPI. Its console launch receives
the narrowly scoped `java.base/java.net` opening and uses its bundled
InetAddress NameService hook; Java 18+ retains the public SPI. The actual Java
17 hostname, numeric/loopback and NXDOMAIN fixture passes. Host launches do not
receive the console DNS flag or reflective opening.

Tests execute the same InitialDirContext path with actual Java 8/17/21/25, verify
SRV/TXT, NXDOMAIN, malformed/oversized/truncated responses, idempotent setup,
other-factory delegation and console-only JVM arguments. A separate actual
Minecraft 26.2 fixture uses the original redirect and IPv4 resolver classes,
then completes a real TCP server-list handshake/status reply against a local
server without sending credentials or a login packet. These host fixtures do
not prove PS5 sockets or authenticated server join; both need console acceptance.

The recommended test is `mc.hypixel.net` using the installed Minecraft XBOX
1.21.11 instance with launcher OpenGL (Zink), rather than Minecraft's Vulkan
choice which that older client does not offer. Hypixel's
[official address instructions](https://support.hypixel.net/hc/en-us/articles/360019495360-How-to-Join-the-Hypixel-Server)
and [supported-version page](https://support.hypixel.net/hc/en-us/articles/360019634940-How-to-Change-Your-Game-Version-for-Hypixel)
list the address and 1.21 family. Acceptance of every newer 26.2 server/client
combination is not promised. Existing Microsoft account refresh, session-server
join, ownership and game blocklist handling are preserved.

The user subsequently confirms Minecraft 1.12.2 pings and reaches Hypixel,
which rejects that old client with an update-version message. This establishes
working discovery/connectivity for that Java 8 run; it does not negate the
captured newer-client directory-discovery failure or prove authenticated play
on every client version. The initial 78-test suite and Java-17-expanded suite
both pass; final combined Fresh & Smooth policy build is separately validated.
