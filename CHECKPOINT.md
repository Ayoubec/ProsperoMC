# ProsperoMC checkpoint — 2026-10-08

## User requirements
Minecraft Java-only PS5 app based on prospero-win runtime, native frontend visually inspired by ProsperoEden, PolyMC-like version/instance/mod management. 1.12.2 is TEST ONLY: main flow chooses and downloads other releases/snapshots and automatically detects/downloads required Java. User authorized limited necessary FTP to192.168.1.111:2121. No changes to other titles.

## Frozen implementation
- Native title/data: dist/PPSA99888 and dist/data/prosperomc. STAGE-REPORT structurallyComplete=true, consoleValidated=false, readyToPlay=false.
- EBOOT SHA256ce2c6f5f3fc786059f245a1918d39bfcc80dbdc902bf18a2d7124f376e965991.
- JAR SHA2563e9d0f7bb75b32d4751b63d800279847ba4fed13add345cbecbac12deefc1cba. Source/title/data JARs consistent after final restage; scripts/deploy-ps5.py --validate-only PASS.
- Native Home/Library/Versions/Mods/Settings/Accounts. Versions sends one create-install, Java major detection/provision automatic. Settings download/verify/repair8/17/21/25 and browse all detected majors.
- Java8backend SHA downloads, assets+natives+logging, isolated instances, Fabric/Quilt, legacyForge1.12.2, localmodmanagement/Modrinth commands, PolyMCpacks, configurable Microsoftdeviceflow and localoffline mode.
- Native bridge rejects generic applications; only internalJava profiles. Wine/OpenGL/input/audio runtime release verified. MatchingTitlePPSA99888Lapy helper compiled+manifestverified.
- SuppliedJava8 and vanilla1.12.2 actualhost install+prepare PASS. SeparateForge14.23.5.2864 actualinstall+prepare PASS. Two testinstances, full918-entryversioncatalog; minimalMinecraftpayload excludes unrelatedversions.
- Actual officialJava17 download+SHA256+PE64inspection+detectJava PASS; java.exe -version PASS. This stays artifacts/java-download-smoke and is not uploaded unnecessarily.
- Backend29fixturetests PASS inclautomatic8/17/21/25 provisioning, reuse, SHA256/wrongOS/arch/major/missingJVM/repair/JDKfallback. Forge7fixturetests PASS. Parent reran nativefrontend and nativebridge+4stagingtests after finalJavaABI: PASS.
- Actualnative previews artifacts/frontend/actual-versions.png and actual-java-settings.png.

## Remaining
- FTP upload active unifiedexec session96123. First attempt refusedconnection (zero writes). User restartedFTP then second authorizedupload started. Poll tools.write_stdin(session_id96123). Do not start duplicateupload. Script uploads data first then title, temporaryfiles+sizechecks+rename, manifests skip unchangedfiles, no othertitles touched.
- After success, ask user to launch ProsperoMC through homebrewloader. Capture UI/storage/data grant/Java startup/1.12.2world evidence. No PS5 gameplay pass yet.
- HostWine10 registrytemplate differs from runtimeWine11.17 (exactreleaseDLLsoverlaid). Actualconsolecompatibility still unverified.
- FullPolyMCparity is not achieved: modernForge/NeoForgeprocessors, CurseForge/Modrinthpackmanifests, advancededitors and consolemodsearch/filebrowser unavailable. See docs/feature-audit.md.
- Previousprobe/source/tooling archived in artifacts/previous-*.zip. Work uncommitted; noGitpush/PR requested.

## Tools / continuation
BundledPython C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe. BarePython aliases fail. WSLUbuntu/nativecompile and network require toolrequire_escalated. Useralready authorized scopedupload; do not ask again. FTPsupportsLIST notNLST. Deployment script refuses staleJAR/EBOOT/runtime hashes. NevermarkreadyToPlaytrue based on structuralpackaging. ReadGATES.md,gates/java.md and finalagentreports.
Uploadsession96123 ended with localtransientDLLreaderror before anyremote changes; boundedreadretry+all4982fileshashcheckPASS. CurrentauthorizedFTPuploader session22630 is progressing (first100fileslogged). Do notretryduplicate while22630runs.

## Deployment update
Minecraft/Java data transfercompleted3215files withownmanifest. SignedruntimeFTPsizecheck found kernelSELF-to-ELF representation: all13differences confined tonon-loadableSCEversionrecords. Derived15comparisonviews withnativepublictool; compareraccepts expectedmetadata changes and rejects alteredexecutablebytes. Currentuploader session79193 resumes/skips3215unchangeddatafiles and verifies signedELFviews beforepublishing. Do not use previoussession22630 (endedatsizecheck). Sourcepackagehashesunchanged.

## Deployment complete
Authorized scopedupload COMPLETE:3215datafiles and1767titlefiles. Currentcompletedexec79193. All15signedmoduleELFviews verified, ebootpublishedbeforeparam.jsonlast. Criticalmetadata/titleJAR/dataJARFTPreadbackhashes verified in artifacts/console-deployment.json. Remote/data/homebrew/PPSA99888 and/data/prosperomc only. No othertitles touched. User now asked tolaunchProsperoMC throughhomebrewloader, AccountsOffline→LibraryMinecraft1.12.2→Play. Awaitexactresult/error; noPS5Java/worldpass untilreply/logevidence.

## Console startup repair — uploaded
User screenshot confirms real PS5 native frontend rendering and both test instances. UI reported missing launcher JAR. FTP verified both package/data JAR copies exist; logs/profiles are app-private UID1 directories and FTP cannot read them. Approval review rejected broadening log permissions; no such changes were made. Native repair now reuses byte-identical staged JAR (avoids replacement), adds /data/homebrew/PPSA99888 as package/runtime/restart fallback, and reports initialization errno/data root on failure. Regression tests reuse/upgrade/missing source PASS; bridge plus4staging tests PASS; actual PS5 cross-compile PASS. New EBOOT SHA2568cf6b5b35228d18146491a5dc21d1d4ed1f1fac6143d13beaf249a6694498913; ELF6a745563d5e328e607c63c0d720d9b30e3aa8da2658a64004f2defb51eb4a570. Updated signed ELF views and both local stage reports. New scripts/deploy-ps5-patch.py sent only executable, two stage reports, two manifests; no Java/Minecraft reupload. Explicit chmod777 in initial patch script was rejected before execution; removed and upload succeeded without chmod. Verified remote EBOOT ELF content and report hashes; evidence artifacts/console-startup-repair.json. Await user close/reopen app from loader (refresh mount if cached), then AccountsOffline and LibraryMinecraft1.12.2Play. Runtime/gameplay still unverified. If new failure visible, exact errno/status will guide next step; don't assume missing files.

## Latest console interaction repair — deployed, supersedes startup-only repair
User reports per-selection black refresh, Mods refresh, ineffective memory/account save and visible errno13. Also requested actual triangle controller icon. User explicitly APPROVED temporary FTP access only to ProsperoMC private diagnostic logs followed by permission restoration. Retrieved8native logs into artifacts/console-errno13. Restored every original file mode and directory700 in finally, successful replies for all. Logs show original mount check skips helper on /data visibility, per-action title reexec, Wine dies during server_init_process before Java starts. Native grant check now requires geteuid0 before reusing /data access, invoking the existing bundled matching-title helper when required; logs include uid/euid/reuse.
Native local settings save preserves other keys, validates memory/account mode, updates UI immediately and overlays authoritative settings on snapshots; account mode/username missing snapshot keys fixed. Native local Mods browse/refresh/toggle and traversal/symlink/collision guards avoid Java/reexec. Startup initializes consistent memory/account defaults. UI draws a real lime outlined triangle (preview artifacts/frontend/controller-triangle-detail.png).
Java Main --serve persistent JVM processes atomic request queue, survives failed commands, publishes response/progress/view and stays alive. Native UI stays visible while background Java runs; no per-action title restart. Backend bounded -Xms32M -Xmx256M codecache64M. Native response queue clears old response before publish; pending Minecraft marker written before request publish to avoid exit race. Successful prepare-launch exits worker and reexecs selected Minecraft JVM; unexpected exit marks backend-failed to prevent restart loops and preserve local UI. Explicit operation can retry backend. Verified staged data JAR can initialize even when loader does not expose package extras.
All30 Java integration tests PASS after fixing repeated transient Windows directory-promotion sharing errors with FilesUtil.atomic retries. Includes persistent-worker failure recovery, consecutive settings updates, successful prepare response/profile and worker exit0. Native bridge tests local save/persistence/config preservation/mods toggles/traversal plus4stage tests PASS; frontend navigation/framebuffer guards PASS; real native cross-compile PASS.
FINAL EBOOTd89c1f8481d8b3fe01cb7b6eb9138f424fe71c67a11b34ad6f43f25a78fb6ec0; ELFe3f4eceed3184a0091c1582ff5f48ed5d076ea92993ddc53a8429ff903e6096c; JAR9658a423d0e59543545aa9f0d8af6a543ae17d0074a5ef0ee24fee11803ad8f3. Source/title/data JARs match. Complete4982-file package validation PASS, refreshed15signedELF views. Limited patch COMPLETE via scripts/deploy-ps5-patch.py: only EBOOT,twoJARs,twoStageReports,twoManifests. JAR/report readback hashes and EBOOT ELF bytes verified. No chmod commands in patch. Evidence artifacts/console-interaction-repair.json.
Await user CLOSE app completely, refresh loader mount if needed, reopen, verify Memory save persists, account toggle works, Mods/Refresh/toggle no black screens, then catalog request and Minecraft1.12.2Play. The helper behavior, background Java startup and gameplay on PS5 remain UNVERIFIED until new screenshot/logs. If worker dies, inspect only own logs (temporary-read permission authorization persists with restoration). Do not claim console/world pass. All child agents finished; root owns integration. No Git commit/push/PR requested.

## Latest drive-table repair and user-selected folder — uploaded
User reports all Java-dependent actions fail/restart twice and triangle style mismatches. Old logs were UID1/private and fresh UID0 process could not write them. Preserved old profiles/imports/logs as *-before-uid0-* backups and created same-named UID0 private700 replacements (approved scoped repair). Evidence artifacts/console-private-folder-migration.json. User retried Java and fresh logs now capture actual Wine startup; stored artifacts/console-worker-failure/fresh-session-*.log. Filesystem helper WORKS: reused0 uid0 euid0; fd capture WORKS; Wine server connects successfully. Fatal error: could not resolve current cwd and failed to open Z:\data\prosperomc\runtimes\java8\bin\java.exe.
Exact cause confirmed: staged dosdevices/.pw-symlinks used Windows CRLF via Python write_text. Upstream virtual-link parser does NOT strip CR, so Z drive target becomes /<CR> and C target ../drive_c<CR>. Correct bytes must be b'c:\t../drive_c\nz:\t/\n' (19bytes). Real native symlink calls are FORBIDDEN on PS5; an intermediate local prototype was replaced BEFORE deployment. Final code uses only the supported virtual mapping table, repairs CRLF in binary mode, reuses exact valid table and rejects unexpected targets. Stage script now write_bytes, fixture asserts rawbytes (read_text had hidden CRLF); deployment checks SHA256 plus exact19bytes. Native bridge and4staging checks PASS, frontend navigation/guards PASS, real native compile PASS. Java JAR unchanged9658a423d0e59543545aa9f0d8af6a543ae17d0074a5ef0ee24fee11803ad8f3; previous30backendtests still relevant.
Cross/Circle/Triangle/Square now share TEXTcolor,26canvas,2pxstroke,4x4antialiasing. Visually verified artifacts/frontend/consistent-controller-icons.png. Backend retry now preserves queued action across the retry restart instead of dropping user's requested download/clone/export.
User requested one folder then EXPLICITLY chose /data/ProsperoMC for all Java/instances/mods/downloads/config/logs, with loader package alone /data/homebrew/PPSA99888. Remote existing data was renamed without recopy/delete; finaldataRoot/data/ProsperoMC, all private backups preserved inside. Evidence artifacts/console-single-folder-migration.json. Host package data now dist/PPSA99888/prosperomc (one distribution folder), defaultstage updated; deploy tool excludes nested data from title upload and sends it once to chosen dataRoot. Native root is exactly/data/ProsperoMC, no sandbox fallback tree. README/architecture/build deployment docs updated.
FINAL EBOOTe3bb22eb4ac266a326e5a09cd08978144cf5a8219fea0bea661473c5cbfdff9e; ELF705274f1a2467c9033af5beed722a3ecc832341fba77f66498ce43f6d6008af9. Full package hash validation1767title+3215data PASS; signed15ELFviews refreshed. Patch uploaded LFtable, twoJARcopies, EBOOT,twoStageReports and manifests. All table/JAR/report hashes and EBOOT ELF verified. FTP DELE success is226, not250; ftplib.delete threw despite successful deletion of stalebackend-failed. Changed cleanup to sendcmd and completed stale runtime-notice deletion. All actualpayloads are uploaded and verified; evidence artifacts/console-drive-table-repair.json. No other titles touched.
PENDING: user asked fully CLOSE and REOPEN updatedapp, then select Java17Download once. Async options Downloadprogress / backenderror / appfail. Wait for response, then READ /data/ProsperoMC/logs directly (now UID0 private dirs/files readable by FTP UID0; no chmod needed). Also check /data/ProsperoMC/backend-ready.properties, progress.properties,response.properties. Main--serve createsbackendready before waiting; its existence is actual JVM proof, but process could laterexit so correlatelogs. Java/Minecraft PS5 success still NOT claimed. Do not use old /data/prosperomc or /data/homebrew/PPSA99888/prosperomc on console. No activebuild/upload sessions. Allchildagentsfinished. No commit/push/PR requested.

## Current blocker: measured HotSpot crash and Wine FP context fix
User latest retest still Working -> Issue. Fresh logs under artifacts/console-drive-retest prove drive-table fix works: Java exe plus jvm.dll/java.dll/zip.dll load. Native helper grants UID0 successfully. JVM dies before Main --serve with EXCEPTION_FLT_INEXACT_RESULT 0xc000008f at cvttsd2si; no backend-ready/progress/response file. Upstream patch 0501 (latest prospero-win b510, missing installed v0.1.1 8086243) corrects PS5 saved FPU offset288->320 and XSTATE header832. OpenJDK CPU probe deliberately raises a signal even with UseAVX=0, so reset/flag workarounds insufficient.
Building ONLY ntdll with exact release Wine490f6d5 + release patch series + upstream0501. Keep original win32u/OpenGL and all other runtime modules. Verified Wine tar.gz SHA c40c03637f90ede4fe60ffc4162473870038dc2324cd1d67d186ad72212a70d5, release808 archive SHA9bc865efd9c4f6e5d159c61b64838c25e49682fff55fcd845e800305f688f5b4, PRX foundation305 archive SHA9afcf7314e52af65b2a84848e396b908a0e74c3d4bc179fc6d18560e96a94ac0. scripts/prepare-wine-fpfix.py adapts upstream recipe for archives/minimal ntdll; scripts/build-wine-fpfix.sh builds host Wine tools, module-capable foundation305 tool then PS5 ntdll. Old9c host tool lacks module export generation, DO NOT use it to publish PRX.
Current exec session62352 active. WSL /tmp/prosperomc-wine-fpfix appears ephemeral after WSL stops, so wrapper copies final binaries/report/log to artifacts/wine-fpfix before exit. Monitor build; on failure capture logs into artifacts before WSL stops. No new module uploaded yet. Console play/download still unverified. No user confirmation needed for authorized fix/upload; request actual console retry after verified module deployment.

Build continuation update: session62352 ended after host tools due editing a running shell script (do not edit scripts while their bash process is executing). Restarted full stable wrapper session58463, ACTIVE: host tools finished, module tool305 finished, FreeType compiled, all73patches applied successfully, PS5 cross-configure still running. WSL /tmp is lost when its processes stop; trap now copies build/configure/make/link logs on exit and wrapper copies final PRX/ELFs/report to artifacts/wine-fpfix before exit. Do not stop/restart just for slow configure.
New scripts/stage-wine-fpfix.py validates exact73patch set, source revision, module SHA, no unresolved/unbound/data-import/raw-syscall violations; preserves original ntdll and updates both reports and source notices. scripts/deploy-ps5-patch.py --wine-fpfix sends only ntdll+0501patch+WINE_SOURCES+twoStageReports+manifests and clears stale worker-failure notice. Signed PRXs use verified ELF views rather than raw SHA readback; regenerate scripts/build-ftp-views.py with module-capable tool after staging. Existing deployment unchanged so far. FTP still reachable at192.168.1.111:2121; latest logsession5 confirmed size18966B. No chmod needed. WINE_PS5_OPENGL preprocessor flag affects win32u only, absent in ntdll; existing embedded-GL win32u remains byte-identical. Fingerprint0501patch24b8a254c01dd65cec187b08b44e830663b677a21410fb5ea5476924f4ea9a19.

## Wine floating-point repair BUILT and UPLOADED (2026-10-09)
Stable build58463 finished while paused. artifacts/wine-fpfix contains PRX, original ELF/shared ELF, build/configure/make/link logs and report. Exact73patches validated (original72release patches + upstream0501); no undefined PRX symbols, no libkernel_sys/WebKit-only imports and no raw syscalls. Four data imports are SYSTEM imports (__isthreaded/__stderrp/__stdoutp from libSceLibcInternal, environ from libkernel), verified via SDK exports. Corrected overly broad stager rejection: app-PRX data imports forbidden, these system imports are supported. ntdllPRX SHA1c86a5eab801b5a2246f17543b5b7a938d3825b64e618fa9f58cb2f129906bd8; ELF SHA04230aa7d23a4375578e679c1e9291f07c79ed9b56057d6593dbaeb5e954823d. Original release ntdll preserved artifacts/wine-fpfix/ntdll-v0.1.1-original.prx. Other runtime modules and native executable/JAR unchanged.
scripts/stage-wine-fpfix.py completed and bothreports updated; patch/source notice staged. build-ftp-views.py now supports --file for incremental updates and prunes data/PE scans, uses atomic record replacement. Exactnewntdll comparison view refreshed, all15records retained. scripts/deploy-ps5-patch.py --host192.168.1.111 --wine-fpfix completed: ONLY ntdll,module sourcepatch,WINE_SOURCES,twoStageReports and manifests. FTP ELF content and plainfile readback SHA verified. Stale backend-failed/runtime-notice cleared without chmod. Evidence artifacts/console-wine-fpfix.json. The new module is actually deployed.
User instructed via async question fully CLOSE ProsperoMC, refreshloader mount ifcached, reopen and Java17Download once. Await reply and correlate scripts/read-ps5-status.py --host192.168.1.111 (bounded own statusfiles/latest2logs, read-only; output artifacts/console-fpfix-retest). No Java/Main/world pass claimed yet. Main --serve backend-ready.properties is proof Main starts, but correlate backend-failed plus freshlog to ensure it staysalive. No build sessions active; old sessions62352/58463 invalid; all agents finished. Userscope continuesfixing download/launch/clone/export, keep all appdata/data/ProsperoMC. Do not switchdatapaths or reuploadunchangedJava/Minecraft.

## Priority: actual Minecraft1.12.2 (user instruction 2026-10-09)
User confirms download and launch stillfail afterFPfix; priority now runningMinecraft, avoidoverengineering. Fresh artifacts/console-fpfix-failed/logs_session-6.log proves0501 DID remove previous floating-point exception: newfatal EXCEPTION_ACCESS_VIOLATION writing0xf000000c inJVM, heapbase0xf0000000, compressedOops32bit, beforeVM initialized. Simplechosenfix: disable UseCompressedOops and UseCompressedClassPointers for bothnativebootstrapprofile and Main.prepare generatedgameJVMargs. No additionalWine rebuild. SuppliedJava8 acceptsflags and runs-version. Nativebridge+4stagechecks PASS; targetedprepare/provisioning andpersistentworker tests PASS withrequire_escalated loopbacknetwork (firstsandboxattemptwasblockedPermissiondeniedgetsockopt,notimplementationfailure). RealPS5nativecrosscompilePASS.
NEW EBOOT5b12f77082d2e74f0eab075ba5d452c68148d95157d88b54acae0a3f9d0bbf77; ELF d2f9e9495d7a146668c0e10b75d57a6341a6bdc9899049c7cfdf471e7c98b773; JARd35c4fcdd664ed39ba598f174f772882b4f724c1bcdcd0e8c838eb46f136c360. BothstagedJARs/reports updated, FPpatchedntdllunchanged1c86a5eab801b5a2246f17543b5b7a938d3825b64e618fa9f58cb2f129906bd8. IncrementalEbootELFviewupdated15records. PatchuploadCOMPLETEandverifiedonly2JARcopies,Eboot,driveLFtable,twoReports,manifests; stalebackend-failed/runtime-noticecleared. Userasyncquestion: fullyclose/reopen, installed VANILLA1.12.2Play, reportopens/differenterror/samebackendstopped. Awaitrealconsoleproof; stillnoplayableclaim.
OnlineprimaryupstreamWINE_PS5_BUILD docs confirm currentreleaseWinsock shim has NO DNS (numeric/localhost only), so laterJava/version internetdownloads mayneedseparateDNSsupport; deferthatwhile userpriorityofflineinstalledMinecraft. Source https://github.com/mpereiraesaa/prospero-win/blob/main/docs/WINE_PS5_BUILD.md. Do not misdiagnoseDNSascurrentheapcrash.

## Minecraft initialization reached; current compatibility fixes (2026-10-09)
Heap flags SUCCESS on actualPS5: backend-ready.properties=readytrue, worker surviveserrors, prepare-launch responseoktrue, title restarts intoMinecraft Java8. User seesloading thenreturns. Freshgameexception was hidden by Main.execute catch; nowprints fullcause stack withauth_access_token/session redacted. perform logs cause TYPES andframes withoutmessages/request values. DiagnosticJAR2e5d681ab5f80f3414a6b5e878bb3f4df855c4e52c4d5ccec50790195c17cc31 deployed.
CRITICAL: native diagnosticlogs rotate8slots. read-ps5-status.py nowreads logs/next.txt andactual newest2mod8; numericmax hadreturnedolder sessions afterwrap! Alwaysuserepairedreader. Newactualtrace artifacts/console-minecraft-exception/logs_session-4.log: java.lang.Error:IPHelperLibraryGetIfTablefunctionfailed -> NetworkInterface.getAll -> Log4jNetUtils.getLocalHostname -> LoggerContext -> bib.<clinit>. Noactualgame.logyet becauseloggerfailsbeforecreation. Userconfirmedappclosed; scripts/repair-prefix-hostname.py changedonly2ownprefixregistryComputerName/Hostname values tolocalhost, preservedoriginal artifacts/console-prefix-hostname/system-before.reg, updatedlocalcopy/manifest/reports. Source stage-ps5.py normalizeshostnameonfreshstage. ConsoleverifiedregstilllocalhostAFTERretest, butnativegetLocalHostfailedregardless: registryfix alone insufficient.
Added12line Ps5Compat.localAddress compatibility, ONLYwhenrootZ:/data/ProsperoMC +Java specification1.8: preferIPv4Stack; setOpenJDKInetAddress.cachedLocalHost to127.0.0.1/localhost withnonexpiringexpiry. ActualsuppliedJava8smoketest passedafter5.5secondscacheexpirywindow. Hostsmokesourceartifacts/LocalAddressSmoke.java; removedclassfromartifact/launcher/classes toavoidshippingfuturetestclass. JAR ef019a7c9c120c93d71fad6a818efc73aa409667f3f1f71431ab585c410cf9d9 deployedusingnew --launcher-only (only2JARs+2reports+manifests;EBOOT/Java/Minecraftunchanged).
LOOPBACKFIXSUCCESS: artifacts/console-loopback-retest/logs_session-2.log nowloads LWJGL64nativeandadvancesMain.main fromSourceFile38 to123. Nextactualerror SAMEGetIfTable via sun.security.provider.SeedGenerator.addNetworkAdapterInfo -> SecureRandom.SeederHolder ->UUID.randomUUID ->ul.init ->bib.init. SSLrefreshcatalog ALSOsameSeedGeneratorGetIfTable, confirmeddiagnostictypetracesinlogs_session-3. ThusrandomseedingfixneededforbothgameandSSL; notguessinglibraryreplace.
CURRENT DEPLOYED JAR 96b9ca4d70660df5f96299c11efac8496d6ad14dacef5844c83beadd4debafde. Ps5Compat nowpublicclass (soProviderSPIclassinstantiable), KernelRandom publicstaticSecureRandomSpi readsFULLbytesfromZ:\dev\urandom thenZ:\dev\random viaFileInputStream, throwsexplicitProviderExceptionifbothunavailable; nofixedseed/clockfallback/noTLSverificationdisabled. Probe32bytesbeforeSecurity.insertProviderAt(PS5Kernel,1); defaultSecureRandom usesrealOSkernelentropy andbypassesunsupportedWindowsseeder/interfaceenumeration. engineSetSeed ignoredbecausekernelmanagesseed, likeWindowsPRNG. Thisnewentropydeviceprobe HASNOTYETbeenconsolevalidated. BuildPASS; minimalJAR-onlyuploadverified. Main appliesonlybundledJava8+PS5root; gameJava17+compatcurrentlyunimplemented, deferwhile1.12.2priority.
Userasyncquestionpending: fullyclose/reopenthenVanilla1.12.2Play; outcomesMinecraftstays/returnlauncher/backendstopped. Needreadfresh rotatinglogs/markers. Devicefilemightunavailable: explicitprobeerrorwillrevealit; don'tclaimcryptokernelfixvalidatedyet. Noactivebuild/upload. EBOOT5b12f77082d2e74f0eab075ba5d452c68148d95157d88b54acae0a3f9d0bbf77 andFPntdll1c86a5eab801b5a2246f17543b5b7a938d3825b64e618fa9f58cb2f129906bd8 remain. OthermodulesoriginalOpenGLrelease. Allappdata/data/ProsperoMC. ActualplayableworldstillNOTclaimed; goalMinecraftofflineworkingfirst.

## Minecraft stays running; graphics test pending (2026-10-09)
KernelRandom SUCCESS on actual PS5: user confirms game stays open and Minecraft music plays; screenshot shows only a white-to-black gradient with Gallium HUD fps16.70. Current JAR96b9ca4d70660df5f96299c11efac8496d6ad14dacef5844c83beadd4debafde unchanged. This proves Java/game loop/audio, NOT visible menu or playable world.
Fresh artifacts/console-gradient/logs_session-5.log repeatedly rejects sampler view target2/2 format105/105 levels0..0/0 layers0..0/1 and software-blits256x256. Need exact Mesa format identification if simplest settings test fails. Current win32u remains original release7298fc50097fbe06980a6e2c8482675dcff7fc3c679456bad34945042d2a674d.
User explicitly CLOSED running game before options change. scripts/set-test-graphics.py uploaded ONLY /data/ProsperoMC/instances/minecraft-1.12.2/.minecraft/options.txt, preserves all other keys and backup artifacts/console-test-graphics/options-before.txt. Set fboEnable:false,useVbo:false,mipmapLevels:0. FTP readback verified SHA5afb8f15d4de5517d2950a6a86de51611d5f28d02f41c607bd17e28c52decf6c. Ask user reopen/play and compare menu vs gradient; async question now pending. No app rebuild for settings test, no unrelated folders touched. G7 still pending actual world/gameplay. Do not claim complete.

## BGRA driver repair in progress
User tested options and still sees gradient. Fresh actual session7 confirms sampler-view reject format105 continues. Mesa26.2.0 generated vertex enumeration maps105=B8G8R8A8_UNORM,84=R8G8B8A8_UNORM. Downloaded official Mesa archive pinned SHAefd4bb08cdb7c365a812cd4e6c9202ab55b2f22cdcd13c7d6c4f9647b799a4ef; headers/generator saved artifacts/graphics-source. Exact bundled GL source b696cd39d63a4e346da3c680a31238b41ae359a8 has erroneous CORE_RENDER sampler capability allowing BGRA, while sampler-view creation rejects BGRA. New official GL SDK1.0.1 includes explicit BGRA sampler rejection so Mesa converts uploads to supported RGBA. Official SDK downloaded .deps/archives/ps5-opengl-sdk-1.0.1.tar.gz226MB SHAaaa2e8957f55e1fc0b654dcb35a36e585f7e635d63952da40a28be7f64fde741; extracted .deps/graphics-sdk-1.0.1. Source commitdb752da4c89380af228497b5b6852163a4e61069, manifest52b6b82f32aec7c983680858c50c25c926266d58f7660d79d44fc1c4505d05bc, actual runtimearchivee4e1bf1fd5e1e7f5a13f97c1e1f27fbd970481aab064186c5d1b4e2a88593a08. libPS5OpenGL.a is483B GNUlinkerscript, actual runtime libps5_opengl_core33.a. Real compiled ps5_is_format_supported host check PASS: BGRA sample false, BGRA render true, RGBA sample/render true; scripts/check-graphics-capabilities.sh and evidence artifacts/graphics-source/capabilities-check.log. Stub unused MSAA util_format_description aborts if invoked, sample1 tests noMSAA. SDK source has fix and runtimeflags confirm2160dynamic120 despiteprovenance displayprofile1080/60.
ACTIVE build session89598: WSL scripts/build-wine-graphics.sh prepares only win32u, original73Winepatchset and exact saved ntdll.shared.elf import artifact. Hosttools built; PS5configure inprogress under/tmp/prosperomc-wine-graphics. Script trapslogs toartifacts/wine-graphics onexit and copies outputprx/elf/shared/report whencomplete. WSL/tmp disappears onWSLshutdown, don'tinterruptbuild or editrunningfile. Added scripts/prepare-wine-graphics.py adapter, stage-wine-graphics.py validators/backups(notrununtilbuilddone), deploy-ps5-patch.py --graphics-only. No consolemodulechanged yet. Need awaitbuild, reviewreport allunresolved/errors/titleunbound/WebKit/rawsyscalls empty, stage, incrementalFTPviewswin32u, askuserclosegame, upload ONLYwin32u+WINE_SOURCES+2reports/manifests. User gamecurrentlymayrunninggradient; don'tassumeclosed. G7stillpending visiblemenu/playableworld. Java/JAR/EBOOT/ntdll unchanged. Readonlylogs nowtailbounded512KB supportsgrowinglogviaSIZE/REST andlast512KBretain. Do notclaimrepaircompletebeforeactualmenuandworldevidence.
User confirms Minecraft and ProsperoMC CLOSED for graphics module replacement (async reply call_bc7f0cbb91604c73b218570abee66924). Keep closed until verified win32u-only upload. No need to ask close again. Build session89598 still active.

## BGRA graphics module repair BUILT and DEPLOYED (2026-10-09)
Build session89598 completed; all final outputs and logs copied to artifacts/wine-graphics before WSL/tmp disappeared. New win32u.prx SHA f606e54c51c71716756a916e90e10a7e87c319596e1a02f1acc6d08a941df207 (25579587B). Buildreport prxstatus0,builttrue, unresolved/errors/title_unbound/WebKit/rawsyscalls ALL EMPTY. Needed ntdll.prx,libSceAgc.prx,libSceAgcDriver.prx,libSceVideoOut.sprx,libkernel.sprx,libSceSystemService.sprx,libSceLibcInternal.sprx. System dataimports __isthreaded/__stderrp/__stdinp/__stdoutp; __stdinp explicitly verified OBJECT export from systemlibC before deployment. Stager systemimport allowlist updated, no appPRXdataimports. Originalgraphics module backup artifacts/wine-graphics/win32u-v0.1.1-original.prx. stage-wine-graphics.py COMPLETE; current2reports updatedwine.graphicsFix SDK1.0.1 correctsourcecommitdb752da; WINE_SOURCES describesmodifiedmodule. Older buildreport sources.ps5_opengl mistakenly captured workspaceancestorGit2f672... ratherthanSDKsource; originalreportretained, actualverifiedSDKsourceprovenance in2stages andWINE_SOURCES correctdb752da. Reproductionadapter fixed to explicitPROSPEROMC_OPENGL_REVISION forfuturebuilds.
Incremental build-ftp-views.py --filewin32u refreshed15records. User hadconfirmed CLOSED; authorized minimal --graphics-only upload COMPLETE: ONLY win32u.prx,WINE_SOURCES,title+dataStageReports,andmanifests. Module actualFTP executableELFview/readback verified; no permissionchanges, nootherconsolefolders/files. CurrentJAR96b9ca4d70660df5f96299c11efac8496d6ad14dacef5844c83beadd4debafde,EBOOT5b12f77082d2e74f0eab075ba5d452c68148d95157d88b54acae0a3f9d0bbf77,ntdll1c86a5eab801b5a2246f17543b5b7a938d3825b64e618fa9f58cb2f129906bd8 allunchanged. Vanillaoptions remainfboEnable:false,useVbo:false,mipmapLevels:0.
Userasyncquestionpending call asking reopenProsperoMCPlayVanilla1.12.2 menuvsgradientvsreturn; refreshloader mountifcached. NeedACTUALconsolevisiblemenuandworldbeforeG7pass. Ifvisiblemenuaskcreateworldtestmovement/audio/save; iffailsreadrepairedringreaderfreshscope. Noactivebuild. Finalpublishedverify script scripts/verify-graphics-upload.py readsfinalmodule/reports andstoresartifacts/console-graphics-repair.json; sessionoutputpending/likelyfinished. Freshmoduleimportschecks+compiledformatfunction proofPASS butconsolegraphicsstillunverified.

## New graphics result: solid changing colors, NOT menu
User reports afternewmodule: onecolorat time blue/white, mousecursoralsoinvisible. Do NOTmarkgameworking. Fresh logs artifacts/console-solid-colors/logs_session-1.log show no sampler-view reject, texturesatlas1024x512 created, framescontinue/GPU submissionsfailures0. NewSDK profiling enabledgpu-present/multidraw/deferredbatch1; no runtimeenvswitch existsinactualsource (onlyPS5_GLTHREAD,PS5_COMPUTE_SYNC,PS5_TESS_GS_PATH). Shader/texture/framebuffer batchrejectioncounts0 exceptreject-input many (fallbackregularrender), notfatalerrors. Currentoptions stillfboEnablefalse (fromearlierdiagnostictest), useVbofalse,mipmap0.
ChosenNEXTSIMPLETEST re-enableONLYnormalfboEnabletrue beforeanotherdriverchange. AskeduserCLOSEgame+app; awaitreply, DON'Tmodifyoptionswhilegameopen. scripts/set-test-graphics.py now --framebuffer true/false changesONLYfboEnable andpreservesotherkeys; protectsinitialbackup. UserpreviousCLOSED state no longer valid afterthisretest. Onceclosed, runscript --host192.168.1.111 --framebuffer true thenaskreopenPlay. Ifstillbad investigateWGLblit/framebuffer, notguessbatchdriverbinarypatch. Graphicsupdatealreadyinstalled/current25MBwin32u f606...; oldmodulebackupretained. Noactivebuild; WSL/tmpgone. Receipt artifacts/console-graphics-repair.json verifiespublishedmoduleELF+2reports, consoleMenu/Worldfalse. Keepcheckpoint/gatespending.
User confirms Minecraft CLOSED. Applied --framebuffer true to ONLY fboEnable; verified FTP readback. Existing useVbo:false,mipmapLevels:0 and other options preserved; backup options-before-framebuffer-test.txt. Next user test reopenProsperoMCPlayvanilla1.12.2 menuvscolorsvscrash; currentmodulef606... and allJavafixes unchanged. Still no visiblemenu/world proof.

## Framebuffer test failed; graphics error diagnostic uploaded
User FBOtrue test: still solid changing colors+music; oldGalliumFPSHUD nowabsent. User explicitly Minecraft CLOSED again. Logs artifacts/console-framebuffer-retest show texture/shaderGLLayer successandnoexceptions, largebatchfallbackreject-inputbutnotfatal (oldb696source ALSOdefaultsGPU/deferredbatch1, so don'tassumebatchonlynewdriverdifference). OriginalWine0723renderscursoratfinalOpenGLpresent; absencecursor+HUD pointsfinaldrawingpath butNOTconfirmedcause.
Nextdiagnosticminimalnativechange: vendor/prospero-win/native/wine64_main.c fixedenvcount6->7 and MESA_DEBUG=1 (MesaGLerrors). Actualnativebuild PASS, EBOOT SHA bc674bc4326aa0383cf90f96593d5b8d6d5c440d069d15411b1fb9730c1d4484, ELF e7b5447be3c3279db331658b6ef98457a697fc8fab725c984f7040e101342e2a. BothStageReports updatedebootSHA+graphicsDiagnostics, unchangedJAR96b9/ntdll1c86/win32uf606. IncrementalEbootELFview refreshed. deploy-ps5-patch.py --native-only (added) uploadedONLYeboot+2reports/manifests; actualFTP executablecontent/readback verified. Userclosedbeforewrite. Noactivebuild. Asyncquestionpending: reopenPlayvanilla1.12.2 leave20secondsreplytested, thenretrievefreshrotatinglogs scopeconsole-mesa-errors. LookforMesa GL_INVALID_OPERATION/INVALID_VALUE etc toidentifyactualdrawfailure; avoidanotherblindoptionsorSDKchange. fboEnable:true,useVbo:false,mipmap0. Visiblemenu/worldnotverifiedG7pending. CurrentdiagnosticMESAflagmustremoveafterfixwhenappropriate. Root ownswork; don'tspawnagentsunlessexplicitauthorizationnewrules.

## EXACT upstream legacy rendering fixes FOUND (user linked repo 2026-10-09)
Mesaerror diagnostic tested: artifacts/console-mesa-errors/session5 has NOGLerrors, shadercompiles0/GPUsubmits0fail, textureatlasloads; solidcolorspersist. User linked blackbearreloaded/ps5-opengl. FetchedLATESTAPIcommits: installedofficialSDK1.0.1 isOct4db752, whereasOct7 THREEFIXESexactlysymptoms: 6e56016513c7 maps legacygl_Color/gl_TexCoord varyings toPSBCsemantics (beforetheyweredropped=>solidcolors); 386c0211e8e6 acceptsnonindexedhas_user_indices leftbyMesa clientarraytranslation (beforelast_draw_status-2=>nothingdrawn); 75d40042933e runsGalliumHUDonEGLpresentation (priorSDK noHUD). OfficialcommitJSONandpatches artifacts/graphics-source/{sha}.json, actions/recentcommits saved. NOTguessbatchformat, theseactualsourcefixesabsentSDK1.0.1.
FoundsuccessfulofficialSDKCIBuild37710162111 Oct8 head738f94cbdf6ff1de0376dc1cd4ce1229fd640730 containsALL3fixes. GitHubartifact11521757116 officialdigest7ef042e1cb6259b12f124890c9d30edd51f4bae5f126e1dbff5f3bd7d07b64d2. AnonymousGitHubdownloadAPI401; publicnightly.link transportdownload succeededandEXACTarchiveSHA matchedofficialGitHubdigest beforeextract (noauthkeys). .deps/archives/ps5-opengl-ci-738f94c.zip245MB, extracted .deps/graphics-sdk-ci-738f94c/ containsSDKtar+sidecarandSHOWCASEzip(doNOTuploadshowcaseotherapp). scripts/fetch-legacy-graphics-sdk.py provenancechecks. SDKprefixextracted .deps/graphics-sdk-ci-738f94c/extracted/sdk, versionci-738f94cbdf6f-37710162111-1, sourcecommit738f, manifestec96253ae019c50c9ddfe31bf2f7a38eaca029c631fcfa54f7dde57f565d8b69, runtimearchive2ca8a6c30412d8f273c023bd5032e9c67a2950d1e68ef9c4ab5127a0b4e14088, PSBCarchive32699de1cdd3f51e879d9c54ed3b750a76832f7c3435578812c3098b654b6c57. BGRAfixpresentalso. Source/provenancetarhash651cb7d2eab40cf95cdd3c2b1fdedf93e6c22cef9f0cfc04578553dbee0d1f6a.
CURRENTACTIVE build newWinegraphicsCI sessionreturnedtoolIDnextoutput: scripts/build-wine-graphics.sh now supports PROSPEROMC_GRAPHICS_OUTPUT=/mnt/c/.../artifacts/wine-graphics-ci and GRAPHICS_SDK=/mnt/c/.../.deps/graphics-sdk-ci-738f94c/extracted/sdk, OPENGL_REVISION=738f... . It copiespayloadSDKandgraphicsSDKto/tmp/prosperomc-wine-graphics forfastlocalheaders/tools (priorWindowsSDKcompileconfigure took~15min; thisshouldfaster). SourceWine490f+same73patches, ntdll.shared.elf unchangedimport. Scriptcapturesalllogs/outputstoartifacts/wine-graphics-ci onexit; WSLtmpvanisheswhenallprocessesexit. DoNOTeditrunningscript. Lastscriptadapter regeneratedwithexplicitOpenGLrevision(correctnearestGitancestorbug).
Needfinishbuild inspectreport unresolved/errors/titleunbound/WebKit/rawsyscalls empty. stage-wine-graphics.py CURRENTLYhardcodedOLDartifacts/wine-graphics and .deps/graphics-sdk-1.0.1; MUSTadaptargsforCIbuild/sdk anddynamicversion/commit/archiveproof BEFOREstage newmodule. Preserveoldf606 modulebackup toallowrollback, original7298backupalreadyexistsunderoldartifacts. compiledcapabilitychecker alsocurrentlyhardcodedoldSDK; adaptinputprefix/artifactandrerunnewSDKBGRAcheck. AddCIlegacyfixverification sourceactualmodule doesclientdraw/varyings; metadataofficialdigestprovesCIidentity, upstreamtestlegacyvarying sourcecanextractandrunwithbundledPSBCsourceifneeded. IncrementalFTPviewnewwin32u thenuserCLOSEconfirmationrequired becauseuserplayeddiagnosticafterpreviousclosedstate. Prepareconcretemodulebeforeaskclose; upload --graphics-only+2reports/notices/manifests. CurrentremotegraphicsSTILLf606(oldSDK1.0.1), nativeEBOOTbc674 diagnosticsMESADEBUG1, JAR96b9andntdll1c86unchanged. fboEnabletrue,useVbofalse,mipmap0. StillNOTvisiblemenu/worldG7pending. Usernowawaitingofficialfixintegration, keep<=60secmeaningfulupdates. NootherprojectfoldersorPS5titlesmodified.
CI graphics build ACTIVE unified exec session73795, copying public payload SDK into /tmp/prosperomc-wine-graphics/sdk after hosttools ready. User NOW CONFIRMED Minecraft+ProsperoMC CLOSED for this CI update. Do not ask close again before upload. stage-wine-graphics.py now accepts --build artifacts/wine-graphics-ci --sdk .deps/graphics-sdk-ci-738f94c/extracted with dynamic provenance; oldmodulebackup win32u-before-update.prx. Fixed conditional source-notice concatenation SyntaxWarning; py_compile PASS. NewSDK compiled BGRA capability check PASS. --graphics-only uploader ready. Poll73795; do not edit running build script. Sourcefix sem mapping+client-array lowering are exact documented Oct7 changes, not speculative batching.
CI build73795 nowPS5configuration aftercopycomplete: payloadSDK34MB andgraphicsSDK162MB under/tmp. Locallookups speedchecks; sameWine73patches/workingntdllimport. LatestuserCLOSED authorization remainsvalid(no laterconsolelaunch). Needuploadafteractualbuild. CompilerAPIreturning0yetnoGLerrorsnotworldproof; exactOct7upstreamfixes nowintegratedSDK sourceexpectedshadercolors/texcoords. Currentstager syntax PASS afterconditionalstringconcatenationfix. DefaultoldSDKsource notice conditionCI onlywith738fcommit.

## Upstream LEGACY RENDERING FIXES BUILT + DEPLOYED, retest pending
Build73795 COMPLETE, outputs/logs artifacts/wine-graphics-ci. NewCURRENTwin32u SHA b7a7f01628afdb9873bc57fe6188a27813bad6ed4241b1f18fe02b94ab838149 (25627395B). Prxstatus0, builttrue, ALLunresolved/errors/titleunbound/WebKit/rawsyscalls empty. Systemdataimports __isthreaded/__stderrp/__stdinp/__stdoutp verifiedsamevalid asprior. Sources reportNOWCORRECT OpenGL738f94cbdf6ff1de0376dc1cd4ce1229fd640730 andSDKmanifestec96253ae019c50c9ddfe31bf2f7a38eaca029c631fcfa54f7dde57f565d8b69. ActualCIcompiledBGRAcapabilityfunction PASS; officialartifactzipdigestmatchedGitHub7ef042... . Sourcecommits 6e56016513c7 legacyvaryingsgl_Color/gl_TexCoord(no longer dropped), 386c0211e8e6 acceptsnonindexedlowereduserindices(no longerreturn-2),75d40042933e HUDduringEGLpresentation ALLincludedCI738f. This isdocumentedupstreamfixes, notspeculativeGPUbatchtoggle.
Staged scripts/stage-wine-graphics.py --build artifacts/wine-graphics-ci --sdk .deps/graphics-sdk-ci-738f94c/extracted COMPLETE. PriorSDK1.0.1f606 modulebackup artifacts/wine-graphics-ci/win32u-before-update.prx, ORIGINAL7298 backupretained artifacts/wine-graphics/win32u-v0.1.1-original.prx. BothStageReports+WINE_SOURCES newCIprovenance. FTPELFcomparisonwin32u updated15records. UserpreviousCLOSEDconfirmedandnointerveninglaunch. --graphics-onlyuploadCOMPLETE+readback executablecontentverified: ONLYwin32u/WINE_SOURCES/2reports/manifests. NewnativeEBOOTbc674(MESADEBUG1),JavaJAR96b9/ntdll1c86unchanged. dataRoot/data/ProsperoMC,loader/data/homebrew/PPSA99888. Noothergames/titleuploaded; CIshowcaseZIPonlylocaldepsNOTdeployed. Vanillaoptions fboEnabletrue,useVbofalse,mipmap0.
NOW asyncquestionpending: fullyreopenProsperoMCPlayVanilla1.12.2 menu+pointervsstillcolorsvsreturn. Actualvisiblemenu/world STILLUNVERIFIED G7pending. Needreadfresh rotatinglogs afteruserreply underartifacts/console-legacy-fix-retest; newHUDshouldpresentexactsourcefix. Ifmenuworksaskcreateworldmovement/audio/save(useR2click/rightstickpointer fromgameprofile). Do notdeclareMinecraftplayableuntilworldconfirmation. Noactivebuild/upload. verify-graphics-upload.py nowreadsactualSourceCommitfromstagedgraphicsFix metadata(ratheroldhardcodeddb752), currentpublishedmodule+2reportreceipt artifacts/console-graphics-repair.json. Needcheckpoint/gatesupdateafteractualresult.


## Minecraft world confirmed; severe performance remains (2026-10-09)
The upstream CI graphics module b7a7f016 now renders Mojang logo, menu, creation screen and pointer on actual PS5. Initial world crash came from Netty 4.1.9 DefaultChannelId -> MacAddressUtil -> NetUtil -> NetworkInterface/GetIfTable. Ps5Compat now supplies Netty supported io.netty.machineId override using eight kernel-random bytes (locally administered/unicast), preserving any existing override. Actual supplied Java8/packaged Netty LocalServerChannel smoke PASS, no NetUtil loaded (artifacts/netty-machine-id-smoke.log). Launcher JAR SHA19e57df575456995d3d55304934b63c464629defee07cd281fe492f88abc9cb0 uploaded to both app copies with reports/manifests and verified after user closed.
USER CONFIRMS world loads and movement works, but reports0.237FPS. G7 remains pending acceptable performance and save/reopen verification. Fresh logs artifacts/console-world-performance confirm integrated server/login, no fatal crash, ~one presentation every4seconds, draw preparation phase0 dominates; GPU submissions succeed. World starts with DEFAULT12-chunk distance because remote options only had fboEnable:true/useVbo:false/mipmapLevels:0. Do not guess JavaJIT disabled: no -Xint/no compiler disable flags.
NEXT smallest test: restore VBOtrue, renderDistance2, fast graphics/noAO/clouds/shadows/particles/vsync, framebuffer staysTRUE. scripts/set-test-graphics.py --performance prepared, backs up options-before-performance-test.txt and preserves other keys. MUST await user close confirmation before modifying active options. No module rebuild/upload needed for this first test. New graphics module/ntdll/native unchanged. All app data /data/ProsperoMC, loader /data/homebrew/PPSA99888.

Performance preset APPLIED after user explicitly closed app. Remote options verified SHAeaf6789fe3e239bb8d043d960dd41be580b68646739baa5d2f52ab6218d58124. Pending user FPS retest same world after30sec. User rightly questions settings alone (menu15FPS); told this is first measurement, not complete optimization.
Exact additional renderer bottleneck FOUND in pinned CI source .deps/graphics-sdk-ci-738f94c/extracted/ps5_screen.c: lines12646ff unconditionally split legacy GL_QUADS/QUAD_STRIP/POLYGON to individual triangle draws, context.legacy_primitive_conversion=true disables deferred batch. Mesa patch u_primconvert then loops every3indices; this fits millions of phase0draw calls/~60kGPU submits perworldframe. Need investigate conditional batched conversion for smooth/no-flat fragment inputs while preserving flat provoking-vertex correctness, explicitflat shaders, GS/queries/TFB. No renderer patch/build yet. Exact CI shader info IO-lowered NIR: load_input/load_input_vertex areflat, load_interpolated_input smooth; shader_info known_interpolation_qualifiers and perspective/linear_varyings allow O(1) conservative test whenknown. Don't blindly set split=false globally (breaks flatquad semantics).

User retest with low settings only0.8-1.3FPS; shader/runtime optimization necessary. Logs artifacts/console-world-low-settings capture counters. Prepared exact CI-source patch915cdc13ca343babae4a73d420f0fe62163fab60ec3da7c6202a1d4c8e166c3f, artifacts/graphics-batching/smooth-legacy-batching.patch. Conservative helper checks Mesa known_interpolation_qualifiers plus input masks against perspective/linear; flatshader/rasterizer, unknown masks, GS, TFB and active occlusion keep original split path. Smooth convertedgeometry staysone drawandallowsexistingdeferredbatch. No wait/resourceownershipremoved.
ACTIVE build session74294: scripts/build-graphics-batching.sh -> compile-graphics-batching.py. /tmp/prosperomc-graphics-performance venvMeson1.8.3,Mako1.3.10,PyYAML6.0.2,packaging25.0; first attempt11276 failedmissingpackagingandended, restartedcorrectly. Exactsource/Mesa/PSBCarchivehashverified,24Mesaheaderpatchesapplied, currentMesonsetupgeneratesheadersONLY, thencompileONEps5_screen.o andreplaceinCOPYoforiginalSDK .deps/graphics-sdk-batching; originalSDKunchanged. Driverout/artifactspolicytests -> invokeexistingWinegraphicsbuildONLYwin32u againstmodifiedSDK, outputartifacts/wine-graphics-batching. Needs actualbuildsuccess/capcheck/metadata/sourcepatchstaging/ELFviews/userCLOSED/upload/retest. Do noteditrunningbuildfiles. UsergamewasleftRUNNINGforlowsettingslog; newcloseconfirmationneededbeforemoduleupdate.
User requestedmanualCMDbuild/send. DONErootProsperoMC.cmd menu/build/send/build-send/help, powershellscripts/build-send-ps5.ps1 orchestratesJava/nativebuild,stage-app-update.py preservesrepairedWine,FTPebootviews,deploy-ps5-patch.py --app-update onlybinaries/reports/sourcepatches,skipsunchangedandPRESERVESremoteoptions/prefix/worlds/Java/mods. Default192.168.1.111:2121. HelpCMDandPythoncompile/stagevalidationPASS. docs/build-and-deploy.md updated. Notrunmanualsendwhilegameopen.

Build74294 ended beforedrivercompile: SDK source snapshot carries unpatchedPSBCheaders; -iquotePSBCsrc tookNIRheaders butgeneratedbuiltin_types.h absent. PolicytestPASS,39MesaheadersgeneratedbutWSLtmpvanished. Correctedbuildscript sourcecompiler nowappliesFULLofficialopengnm-psbc-ps5.patch andgeneratesmatchingPSBCheadersusingofficialMakefile(no compilerarchive rebuild). AddedLLVM_CONFIG=/usr/bin/llvm-config-18 toavoidmanyslowWindowsPATHmissingLLVMprobes. Addedscopedbuild-state.tar.gz trap so configuredheaders/source/tools surviveerrorsandWSLshutdown. CURRENTbuild91635 active, finaloutputsunchangeduntilsuccess. scripts/stage-wine-graphics.py allowscurrentb7a7backupandrecordslocalpatch metadata; --graphics-onlyuploader includesverifiedsourcepatch whenpresent. NoPS5modulechange yet.
Manualupdateunitchecks2/2PASS: unrelatedworldfilepreserved, unchangedfile notwritten, corruptreadback prevents replacingoldappfile. CMDhelpPASS, stagingvalidationPASS. README+builddocs entrypointadded. Existing distributionfields readyToPlayfalse correctly retained dueFPSissue.

Renderer build continuation:91635 finishedMeson+39headers in~minuteswithLLVMenv, thenPSBCMakefile hadno builtin_types.h rule. Headergeneration nowonlyfivePSBCNIRheaders; driveralsoincludesMesa-build/src/compilerforgeneratedbuiltin_types.h. Savedbuildstate150MB persistsartifacts/graphics-batching/build-state.tar.gz. Retry28903 failedbecausecachedsourcealreadycontainednewfilescreatedbyfullPSBCpatch; trackedfileswereoverlaidrawbutnewtestsremained. AddedtargetedcleanupONLYexactpatch-createdfilesafterverifiedarchivecopy, withresolvedscopecheck, thenapplyfullpublishedpatch. CURRENTACTIVE build15123 (91635/28903ended). No PS5changes. Needcompilednativeobject+win32u checks/capabilities/ELFviewandcloseconfirmationbeforeupload. PolicycheckPASS frompreviousattempts. ManualCMD2unitchecksPASS anddocscomplete.

## Renderer performance module BUILT + STAGED; user CLOSED; sending via CMD
Finalbuild79266 COMPLETE. Oneobjectps5_screen.o replaced in verifiedCIruntimearchive. Currentruntimearchive34f0016018bfc4a9c98fbdba2482195655cd1f408c4802ecfe820d4734a7b884, modifiedSDKmanifestec1d3a524f4a0ffface62795e93ff62c0ba6c0567e6954462862183dc87df985, publicPSBCarchive32699unchanged. ActualcompiledBGRA/RGBAcapabilitycheckPASS; archivecheckeveryotherobjectunchangedPASS; shaderpolicyflat/unknownfallbackPASS. Buildhadgeneratedheadersmissingfromsourcearchives; officialMesa/PSBCpatches+NIR/AMDgeneration suppliedmatchinginterface, no compilerlibraryrebuild. WSLsavedstateartifacts/graphics-batching/build-state.tar.gz.
Currentwin32u9f458e225f68a51b22f9f958630b11e169a3b7d584d3552e159b9038e57f98c4(25624243B); ALLunresolved/errors/titleunbound/WebKit/rawsyscallsEMPTY. Currentntdll1c86 unchanged. Stage+sourcepatch915cdc verified andFTP15ELFviewsrefreshed. Priorworkingb7a7graphicsbackup artifacts/wine-graphics-batching/win32u-before-update.prx. ModuleperformanceSTILLUNVERIFIEDuntilPS5test. VanillaoptsVBOtrue/FBOtrue/renderDistance2/AO0/fancyfalse/noVSYNC/mipmap0. ActualMinecraftworldrendererbytecodesbuq unconditionallysetsGL_SMOOTH7425forworldterrain/translucent, so fastpredicatecanhitwithoutenablingAO.
ManualCMDactualendtoendbuild90001PASS aftercorrectingELFtoolpath to.deps/source/foundation9c0.../build/runtime-shim/ps5-native-tool. Initial88537 onlylastverificationstepfailedwrongtoolpath; fixed. CMDbuildrecompiledsamecodeJAR ZIPtimestampschangedsha CURRENTJAR1c62b711fcb28edf82f9a2ed07c3d337c60629e554a6b59dfe61a0901a81b48b; nativeEBOOTbc674 unchanged.2reportsupdated. Use --app-update/send insteadgraphics-only this time tokeepbothJARcopies/reportsconsistent.
User NOW CONFIRMED CLOSED (call22495reply). Currentauthorized CMDsend executed, toolsessionIDnextoutput. App-only updates skipunchangedmodules and onlyreplacechangedbinaries/JAR/sourcepatch/reports/manifests; worlds/options/prefix/Java/modsunmodified. Needfinishuploadreadback+verification, askuserreopenSAMEworld30secFPSandrendering; comparedrawcountsusing--sessions2freshlogs. Do notmarkG7playableuntilFPSimprovesandactualsave/reopenverified. Noagents/commit/push/PR.

CMD SEND COMPLETE and verified, noactivebuild/upload. Onlynew9f458win32u, two1c62JARcopies,sourcepatch/notices/twoStageReports/manifests changed. ntdll1c86 andnativebc674 were verifiedandSKIPPEDunchanged. NoJava/world/settings/prefix/modchanges. Asyncuserquestionpendingcalllatest: reopenappsameworld30secFPS+texturecorrectness. Usercloseauthorizationconsumedbynewtestnowgamecanrunning; don'treplaceagainwithoutfreshcloseconfirm. Finalverificationreceiptgraphics-readbackscriptisrunningorcompletednextoutput. Capturefresh performance logs afterreplyusingnewscopeand--sessions2. AllnecessarymanualCMDbuild/sendtestsACTUALLYpassed onhost/console now, commandProsperoMC.cmd build-send; rootmenualsoworks. G7 remainsFPSpending.

## SUCCESS: Minecraft 1.12.2 playable on PS5; manual CMD build/send complete
User confirms NEWoptimizedmodule reaches30-60FPSat2chunks;9-40FPSat10chunksusinglowsettings, versus0.8-1.3at2beforepatch. Logs artifacts/console-batching-success confirm sameNewWorldserverstart/login, world savesoverworld/nether/end, viewdistance2->10->7, thousandsrenderedframes, inputs/audio andnoGPUsubmissionfailures. OfflineauthDNSwarning stillnonfatal; online/services/downloads consoleDNS remainseparatescope. G7 nowPASS narrowlyactualvanilla1.12.2worldat2chunks; high-distancepacingstilllimited. DoNOTclaimfullPolyMCparity orallversions/mods/authconsoleverified.
CurrentDEPLOYEDwin32u9f458e225f68a51b22f9f958630b11e169a3b7d584d3552e159b9038e57f98c4, JAR1c62b711fcb28edf82f9a2ed07c3d337c60629e554a6b59dfe61a0901a81b48b, EBOOTbc674, ntdll1c86. ExistingpublicCIbaselinewithlocalpatch915cdc, othersunchanged. Sourcepatchuploadedandexactexecutablereadbackverified. ReceiptupdatedwithactualuserFPS/worldevidence. Noactivebuild/upload/question. UsergamecanstillRUNNING; nofurtherwriteswithoutfreshcloseifchangingmodule/options. Usercurrentlychose7chunkdistanceaccordingtolastlog; doNOTresettheirsettings.
ManualrootProsperoMC.cmd build/send/build-send/menu/help readyandACTUALcompletebuild+console-sendPASS; default192.168.1.111:2121. Sendschangedappmodules/JARs/sourcepatches/reports only, retainsworlds/Java/settings/prefix/mods. 2publicationtestsPASS, properELFverificationviews15records. README/builddocsdescribecommand. NoGitcommit/push/PR requested. FuturegoaloptionaloptimizationhigherchunkdistancesandconsoleDNS/downloads/modernJava/mods/auth; currenttoppriorityMinecraftworldexecutionachieved.

## 2026-10-09: targeted GUI/particle batching, LAN fallback and artwork DEPLOYED; console retest pending
User resumed optimization/LAN/TNT/artwork work after publishing main commit768c2d9 to Ayoubec/ProsperoMC. TNT is severe lag (~0.5FPS), not a crash; inventory ~5FPS. Read own-console logs artifacts/console-lan-tnt: actual Open-to-LAN crash is NetUtil static initializer -> NetworkInterface.getAll -> GetIfTable Error. User confirms BOTH CLOSED before this update.
Latest upstream GL90ef9f only release/docs/SDL changes beyond already-used CI738f. New targeted driver path handles non-indexed GL_QUADS using Mesa u_index_generator API first/last -> hardware last, fragment flat-input vertex2 fixed, one indexed draw + existing deferred batch. Original conservative path handles indexed/restart/complex draws. Shader compiler/resources/waits unchanged. scripts/graphics-quad-batch.c integrated by existing prepare-graphics-batching.py, patchc8c9a5...; runtimearchive0fb681..., SDKmanifest13ade5...; only ps5_screen.o differs from original CI. Actual generated Mesa indices first/last-color/winding/multiple-quads PASS, compiled capability PASS, native import/link audits PASS. Cached state rebuilt and saved; all build sessions ended. Prior working9f458 module rollback at artifacts/graphics-before-flat-batching/win32u.prx.
PS5/Java8/1.12.2-only NettyCompat generates hash-pinned single-class overlay compat/netty-4.1.9-ps5.jar during prepare. Broadens that class's existing adapter exception catches to Throwable so GetIfTable Error falls back to loopback, original dependency unchanged. Original class7b47c212... pinned, Apache/component license carried. Test with actual bundledJava8 and Netty simulates exact GetIfTable Error: original fails, patched opens NIO TCP listener and request/reply PASS. All30 launcher regressions, native frontend guard/navigation, runtime bridge+4stage checks and2upload preservation checks PASS.
New imagegen assets assets/generated/prosperomc-icon.png and prosperomc-world.png; local saved prompts in assets/generated/README.md; native embedded RGB565 app/native/pm_art.h generated by prepare-artwork.py. Real native framebuffer preview assets/generated/launcher-preview.png checked. PS5 icon512PNG and1920x1080DDS backgrounds encoded and added to app-only uploader; no new runtime image decoder.
CMD SEND COMPLETE and readback VERIFIED. CurrentDEPLOYED win32u ba5edcc275bea3fee3038d548156f2359d6d9adf29d6d9efe356f746ed6a7381, JAR e226601902fac4dbd1c6f2d6b2b8d6c3e2d71b068be1f70c0eebdf62c62ee028, EBOOT f6fcac9f7d15e2383fa696d2827e6a0f6e3bd10779b4426f8fdbc837e257d8d3. ntdll1c86 unchanged/verified/skipped. Own reports/sourcepatch/notices/icon/backgrounds updated. Worlds/options/Java/mods/prefix preserved. User GAME NOW CAN BE RUNNING: new async retest asks inventory/TNT FPS, colors, OpenLANport/error and leave running; DON'T replace again without new close confirmation.
Fresh artifacts/console-quad-batching shows session0 starting saved world (spawn76%), no conclusion yet. Need wait for user result/read fresh logs. LAN host/join and FPS gain NOT YET CLAIMED. Further requested16chunk60FPS is a target, not established. OriginalG7baseline remains2chunk30-60 tested; new graphics receipt resets console proof pendingretest. Current uncommitted changes remain local; prior GitHub publishing authorization exists, push updates after real retest when appropriate.

User console confirms first quad update: TNT now smooth30FPS (was0.5), LAN UI now opens and permits Survival, general25FPS6chunks/10FPS10chunks stillneedswork. Native log confirms hosted61238 (GetIfTable warning caughtnonfatal). OnePCstatusTCP attempt61238 refused; cross-devicejoinUNVERIFIED, donotclaimfullLAN. User now saysMinecraftSTOPPED; interpretedsameappclosecontext, don'trestartwithoutnotice. New indexed quad extension uses Mesa u_index_translator with8/16/32bitinput, preservesindexBias/maps/ownership. Realgenerator/translators first/lastprovokingcolors+windingtestsPASS. Initialbuild79897 caughtobsoleteMesafieldtake_index_buffer_ownership; removed. Secondbuild29278 drivercompiled, Winehost/modulebuildCURRENTLYRUNNING. Preparedadditional targeted boundskip ONLYcontext.legacy_batch_quads&&index_bounds_valid&&zeroBias forgeneratedsequentialindices; external/indexed data stillscanned. This newer source NOT built/deployed yet: after29278finishes launchbuild-graphics-batching AGAIN, not concurrent sameworkdir. Currentnewpatchchecksum fromlatestprepareprint differsa9f5; docslockstillc8firstrelease needupdateFINALSDKprovenanceafterbuild. CurrentDEPLOYEDba5edcc remainsworkingTNTfix. Backuppriorflatversion artifacts/graphics-before-indexed-batching/win32u.prx. Native/JAR/art unchanged; nextsendGRAPHICS-ONLY. Needcompiledchecks/link/sourcepatch/FTPview, closedusercurrent, deployverifiedthenask6/10/16sameworldFPS+inventoryterrain/TNTstillcorrect andLANportifjoiningprobe needed. Artlooksfitnativepreview. AllpreviousfulltestsPASS andnoJava/nativechanged since. NoGitcommit/push newerchanges yet.

## FINAL indexed/known-bounds renderer BUILT + DEPLOYED; console retest now pending
Build72038 COMPLETE; prior29278 ended. Final source patchd26d3e489f2774dc85155080b0d2cbd16cf9d08961cc94a822a762e6928a203e, runtimearchive6a745d7a9f464a1d764b51d963a3768a221de3f27a8f157cb94ecc45270ceb4d, SDKmanifest9dfe49fbb600c2387b39a272b96b22c7d9bea198fbd6162882a732f98226c311; versions.lock updated. Allimports/errors/rawsyscalls/titleunbound empty; actualcompiledtexturecapsPASS; Mesa8/16/32bitindex first/lastprovokingcolors+windingPASS; onlyps5_screen.oarchivechangedPASS. Finalrenderer ee4d18241c1e4c7deda06344fb18c526d1ff53a780fbbe1548b423d6537d61f3 staged, FTP15ELFviewsrefreshed, GRAPHICS-ONLYupload+readbackverified complete. Shadercompiler/resourcewaits unchanged. User explicitlyMinecraftSTOPPED beforethissend. CurrentJAR e226601... andEBOOT f6fcac9... unchangedfromart/LANupdate; ntdll1c86 unchanged. Worlds/settings/mods/Java/prefixunmodified.
Known-bounds optimization avoidsps5_index_bounds scan ONLYoninternallygeneratedquads withinfo.index_bounds_valid, zeroindexBias andmax<UINTMAX; external/indexeddata usesoriginalfullscan. Indexedquadmap/unmap andindexBias remain; rasterizerfirst/lastprovoking preservedviaofficialMesa translator. ExistinggoodTNT30moduleba5edcc backup artifacts/graphics-before-indexed-batching/win32u.prx.
Useraskedculling; answeredvanillaMinecraft hiddenblockfaces/camera-frustumterrain/entityculling plusdriverbackfacecullingalreadyactive, noadditionalentity-behind-wallCPUocclusionimplemented. Verifiednativecullflags; localclientbuq containsfrustum/culling, bzfRenderManager bytecode saved. DoNOTclaimcustomocclusionwasadded.
NEW asyncquestionpending: reopenSAMEworld FPS6/10/16chunks aftersettle andterrain/items correctness; ifOpenLANincludeportandleaverunningforonePCstatusprobe. UsergameCANRUNNINGNOW; no furthermodule/optionswriteswithoutfreshcloseconfirmation. CandidateperformanceUNVERIFIEDcurrently; previouslyuserfirstquadupdateTNT30FPS, general25at6/10at10. OpenLANUIandhostport61238works; cross-devicejoinstillunverified/onePCconnectionrefused. Latestgraphicsreceipt resetsconsoleproofbecausemodulechanged. AllbuildsessionsDONE. New GitHub sourcechanges notcommitted/pushedyet; priorauthorizationtopublishrepoexists. Addlatesthardwareoutcome todocs/checkpoint beforefinishing/pushing. Logo/artwork savedintegrated andactualnativepreviewchecked. Needkeepcheckingfreshlogsboundedownscopeandnotre-pollunchanged tooquickly.

## 2026-10-09 input, graphics, UI and modpack update (build in progress)
User confirms BOTH CLOSED for this update; later asks expedite due 9% usage remaining. Current remote remains ee4d182 graphics/e226601 JAR/f6fcac9 native. No console writes yet this turn. Latest actual console feedback: 60FPS 4 low chunks, 21FPS 8 fancy/fullscreen, 8FPS 16 fancy/fullscreen. Keep all user graphics settings/worlds unchanged.
Implemented USB wheel forwarding and L1/R1 wheel bindings using existing motion-code ABI; new Wine patch0671 handles Windows MOUSEEVENTF_WHEEL without changing ntdll. Native game-profile wheel parsing + input tests PASS. Main launches refresh120, metadata attribute3=0x80040 matches upstream HFR docs, SDK fallback60 remains; no claim130FPS guarantee.
New graphics source a68ac3dbc8daa56ff2077dc7b484b7d7127407c209b24846b588c8d867f5f647: immutable quad indices cached per provoking convention bounded12MiB; owned VBO/index buffers publish once, CPU map/subdata/drain invalidates publication; external/persistent/GPU-written keep conservative flush. Source driver cross-compile PASS; runtimearchive9665578ed587d5392f1011f8665d9153ac19f89c735738e39054e71eaf48c0b2; manifestbad8f45e33e11b3ca23716ac619fbdfdfbdd84e0eafaa043733816908b84c9f8; onlyps5_screen.o changes, PSBC unchanged. Publication, cached-index/winding/provoking and compiledBGRA checks PASS. Rollback ee4d module at artifacts/graphics-before-static-buffers/win32u.prx.
UI adds animated focus/underline/progress, held D-pad repeat and quiet procedural audio tones; native modpack picker via Square in Library/Mods scans only regular files under /data/ProsperoMC/imports. Existing PolyMC ZIP import exposed, new Modrinth .mrpack import implemented with SHA1/SHA512, client env/overrides and loader checks. All32 Java integration tests PASS, frontend guards/navigation PASS, bridge/stage4 checks PASS, upload-preservation2 PASS. Native final rebuild session34123 active after tiny footer/nav adjustment; previousnativeebca564...built successfully. Graphics Wine build session95889 ACTIVE; earlier56038 failedFreeType download;95628failedhunkcount. Patch nowcorrect3->10 and gitapply--numstat PASS. FreeTypearchive.cached.deps/archives/freetype-2.13.3.tar.xz verified0550350666d427c74daeb85d5ac7bb353acba5f76956395995311a9c6f063289, build script reuses it.
Needfinishactualgraphicsbuild95889; stage-app-update.py FIRST afternative34123, stage-wine-graphics.py THEN usingmodifiedSDK; wheelpatchstager copiesnewpatch/sourcehash onlyifreportincludes0671. Regenerate FTP EBOOT +WIN32U views with exactfoundationtool, send --app-update (nowincludesparam.json), readbackverify. User remainsCLOSED unless newmessage/test changesstate. Updateversions.lock/docs/checkpoint withFINALhashes, commit/push to authorizedAyoubec/ProsperoMC, requestconsoleFPS/controls/UI test. NEVERsendnewwheel-native/JAR witholdwin32u: oldhandlerwouldtreatwheelasmotion and oldnativeparserrejectwheelbindings. No unsupported guarantee16chunks60. CurrentnewrendererHWvalidationpending. Screenshot actualnativepicker artifacts/frontend/packs.png inspected good. No private data committed. No newagentsallowed.

## FINAL input/UI/modpack/static-buffer update UPLOADED + VERIFIED
All builds complete; no active build sessions. Wine module8894438ef7e7e362c85a2a47390ef3eab34c4e7d94be0f45e58f912a5d981c91, all link/import errors empty,74patches including0671 confirmed. Finalnativec35de9bdecea1362a1e62152813c8c8cacab1be8e2873a8ab097f510cee70e55, ELF8a9ba3a09d2d0b563af449c423a609b58e09535b07a117865f5b8a9bb6486b74. FinalJARf3ba9dc3162cefed22808388fb5849e9b6670993e640a826257f4f92b556b0e1. ntdll1c86 unchanged, verified/skipped. Updatedapp/JAR/win32u/Eboot/param0x80040/sourcepatches/reports/manifests ONLY. ActualPS5ELFviews and ordinaryfilesreadbackPASS. Worlds/options/prefix/Java/modsunmodified. UserCLOSEDauthorizationusedforsend; newtestquestionNOWasksreopen8/16fancyFPS+hotbarwheel, gamecanrunNOmorewriteswithoutfreshcloseconfirmation.
Candidateperformanceand120HzactualnegotiationNOTCLAIMEDyet. 32launchertestsPASS; nativefrontend guards/navigationPASS; runtimebridge/stage4PASS; wheeledgesactualnativefunctionsPASS; package-preservation2PASS; publicationCPUedit/external/GPUwritechecksPASS; cachedquadprefix/provoking/windingPASS; originalCIarchiveonlydriverobjectchangedPASS; actualcompiledtexturecapsPASS. CurrentofficialSDKbaseline unchanged otherobjects/PSBC. Previousrendererfeedback60@4low/21@8fancy/8@16fancy recorded. Useraskedhurry9percent: completedverifiedsendbeforeGithubpublication. Newnativepickeractualpreviewartifacts/frontend/packs.png viewedcorrect. PublicdocsupdatedformatlimitationsandHFRfallback. ReadyforuserconsoleFPS/control/UIfeedback; doNOTresetgraphicssettingsorclaim60@16.


## 2026-10-09 resolution, fixed window and selection music — UPLOADED

User confirmed app/game closed before upload. New async console test now pending;
the game may be running again, so obtain a fresh close confirmation before writes.
Resolution selector supports 720p/1080p, saves with memory, changes Wine virtual
desktop plus Minecraft width/height on the next launch. Settings render preview
was inspected. Frontend navigation/guards, native bridge persistence/preservation,
32 launcher integration checks and 2 app-only publication checks pass. Initial
launcher tests hit sandbox loopback denial; approved loopback run passes all 32.

Rebuilt only win32u with 76 release-matched patches, adding local0672 fixed
window styles and reviewed upstream0910 worker-desktop cache. The native title
sets WINE_PS5_FIXED_WINDOW=1; child/non-PS5 window styles are preserved. Existing
working ntdll/OpenGL shader/resource synchronization remains unchanged. Latest
upstream reviewed through d5a0ec0195531f0b607aea548be8f014d2f9146a: new D3D9
batch structural validation is irrelevant to this OpenGL game; not imported.
0908 applies to native/guest machine differences, not this PE64 Java instance.

Home selection music sce_sys/snd0.at9 now contains 87.355 seconds of “hollow.
(mastered)” by steveologic, using PS5 AT9 Converter f8ab08b. 192kbps stereo48kHz,
2096808 bytes, measured-28.04LUFS, loop and fades; decoded WAV preview passed.
Added build/upload inclusion and prominent README thanks with GitHub/Instagram.
Original MP3 remains outside Git. Presentation cache may need loader refresh.

Fresh console options already useVbo:true, renderDistance4, fancyGraphicstrue,
maxFps150. Previous VBO:false observation was stale. Scoped write preserves EVERY
option value, checked by parsed dictionary equality; no FPS benefit claimed.
User explicitly reports VBO made no difference. Latest logs archived in
artifacts/console-window-before show expensive draw preparation/individual
submissions and successful PS5 AGC operations. Future performance work should
profile draw overhead, not reset graphics options or treat etaHEN0 as GPUidle.
60FPS ceiling still unresolved; actual TV120Hz negotiation unknown. Vulkan
possible in principle for newer releases, unvalidated; 1.12.2 stays OpenGL.

All app-only uploads and exact signed-ELF/ordinary-file readbacks pass. Both stage
reports verified; worlds, mods, Java and prefix untouched. Local deletion of three
old artwork source files predated this work; excluded from our Git commit.
New hashes:
win32u f003791d4e4fb39f12e54b52fb924486cce746beec6908c84a817c71bfcd2e13
JAR 1b97a153d167a4b1ad7d0c552bdfc3f549e81dbb37f37b427adb1585173df822
EBOOT aff64dee9d1418147d532197081435a8a259796107fe7abad040d81e59071188


## Resolution follow-up — UPLOADED, console dimensions pending

User confirms home-screen music works and window edges are fixed. 1080p still
showed720p. Read fresh settings/profile/plan: NO resolution key; desktop/arguments
both1280x720. No GPU allocation error involved in that launch. Resolution now
saves immediately on Left/Right/X selector changes, with trace logging of actual
native settings actions. Presets720/1080/1440/2160 added consistently to frontend,
bridge validation/serialization and Java. Settings subtitle explains HDMI output
remains1080p; larger render resolutions downscale, not native4K HDMI mode.
Frame mailbox capacity increased to3840*2160*4, avoiding old1920x1200 drop limit.
Wine driver already accepts up to3840x2160 and graphics caps allow16384.

User explicitly BOTH CLOSED before send. Saved only requestedresolution1920x1080
in /data/ProsperoMC/settings.properties, preserving other keys, backed up and
readback verified. Native/JAR staged, Eboot FTP comparison refreshed; app-only
upload/readback and bothreportsPASS, Wine/music/art/modulesunchanged. All33Java
integrationtestsPASS (new4presetprofile/args persistence), frontend immediate-save
navigation/guardsPASS, bridge4presetpersistencePASS. Existingoptions/worlds untouched.
New async test asks1080F3 firstthen1440/4Kpicture/dimensions. The app may be running
now; obtain freshcloseconfirmation before further console writes. No performance
increase claimed; VBOalreadyenabled withnoimprovement peruser. Stilldraw-overhead
and60Hzceiling workpending. Archivedlatest logsartifacts/console-resolution-retest.
New hashes:
JAR 722679be25b99eb208fba871a1ac843150773607c937570fecce677dede36ae5
EBOOT 06352734edb67b4aa14191edd9a9c4cad358e282649e1106d409378bfa0960a0
win32u f003791d4e4fb39f12e54b52fb924486cce746beec6908c84a817c71bfcd2e13


## Read-only owned draw-buffer performance candidate — build complete

Baseline user25FPS1080p/18FPS1440p. User confirms bothMinecraft/ProsperoMC CLOSED
before this graphics-only update. Latestdiagnostics artifacts/console-performance-highres
confirm2560x1440 actualgameframe. Candidate only changes ps5_screen.c's read-only
CPU-owned vertex/index buffer map/unmap path, notsettings/renderdistance/resolution.
Guard requiresPIPE_BUFFER withVERTEX/INDEX and optionalVERTEX_STATE binds only;
READ withoutWRITE/PERSISTENT/COHERENT, noexternalCPUexports and noGPUwrites.
Eligible CPUreads skip unnecessary queued-GPU-read drains, readcacheflush and
publication invalidation. CPUwrites, computeGPUwritten, persistent/external,
texture and otherbindings retain oldsync. Map/unmap/publish regression excerpts
pass1000repeatedreads pluswrite/GPU/export/bind guardcases. Staticbufferpublication
regressionPASS; compiledBGRAcapabilitiesPASS; archiveonlyps5_screen.o changed,
allotherobjects/PSBCexactCI. Preserved076Winepatchseries inclwindowfix+0910.

Sourcepatch e37a0daa292a89832421060f52ecd50872b12653c44cb253fa3255e9796b2078;
SDKmanifest aeb8111595362a40e66aab441cfcd9bbf2258958c55735a91eea985c0f91864e;
runtimearchive949e2bd4b16960b2bbc9d066e49f19e7c9c3118c7a3d66f3dcc53d886a52a3b5.
Modulelinkallimports/error/rawsyscall/unbound checksPASS. Rollback previousworking
f003module artifacts/graphics-before-readonly-maps/win32u.prx, originalpatch and
SDKprovenancebesideit. NoJava/nativechanged. Build45062DONE. Stagingdone, FTPview
refreshed. Upload70230 COMPLETE: module/patch/notices/bothreports transferred and readback
verified; graphicsreceiptPASS. Noactivebuildsessions. Newasynctestnowasks1080p/1440p
sameworld/settings FPS plusvisualcorrectness; appmayberunningNOW, obtainfreshclose
confirmation beforemorewrites. CandidateconsoleFPSnotestablished; compare sameworld/camera/chunkdistance/options at1080p/1440p.

win32u bc0f2f2b08f20c5015cbce19e7120b46d95946998ccf5d6d391582330b698205
JAR unchanged 722679be25b99eb208fba871a1ac843150773607c937570fecce677dede36ae5
EBOOT unchanged 06352734edb67b4aa14191edd9a9c4cad358e282649e1106d409378bfa0960a0

## Lowered non-indexed batching candidate — uploaded

Latest user retest: 1440p/8 chunks initially32FPS, then13–14 after moving and
staying still. Freshlogs artifacts/console-readonly-map-retest show read-map
phase6 average about287cycles (692423calls/198496586cycles), versus about23k
before the previous update. That optimization worked. During slowdown input
fallbacks rise, with3400–4700 individual submissions per interval; allother
batch rejection categories remainzero. Existing ps5_draw_vbo_locked qualifies
has_user_indices with index_size because Mesa retains stale flags on lowered
non-indexed draws; ps5_multidraw_eligible incorrectly rejected that flag alone.
Aligning the batch predicate is the targeted follow-up, with atmost16 bounded
input diagnostic lines after10000rejects. Null/empty draws are guarded. Actual
client-indexed, indirect, primitive-restart and unsupported formats stay guarded.
Host test extracts realpredicate, including restrictedblitterfan/null/emptycases.
Read-only map/unmap/publication tests, compiledBGRA capability and only-driver
archive tests allPASS. NoJava/native/optionschanges. BothCLOSED explicitly
confirmed byuser thisturn; do notaskagain before thiscandidate upload.

Build session64531 finished successfully. Allimports/rawsyscall/unbound checks
passed;076Winepatches and repairedntdll preserved. Stagingcompleted, win32u-only
FTPcomparisonview refreshed (55442finished), graphics-only upload completed with
executable readback and bothstage reports. User worlds/options/Java/native/JAR
were untouched. Further console writes require a freshclose once test is requested.
Sourcepatch f10b726029f9671365f3e1a10642e8e796741dcde28c06bcdb32c0b49e27801d;
SDKmanifest af4e78238786c8f718489d3926883eee32d64ed42ba2969cfb0bb646805eb04f;
runtimearchive38299f03c2fb372ffb80627114e276ad3bf938f4d938247d895e16c8ecc8af82.
Rollback deployedbc0f module/patch/provenance preserved in
artifacts/graphics-before-lowered-batching. Newwin32u:
7ffe5791b5004342018ab7700ed1cd7da872c3c3bfad1eb585bfc763d84d2e31.
JAR unchanged722679be25b99eb208fba871a1ac843150773607c937570fecce677dede36ae5;
EBOOT unchanged06352734edb67b4aa14191edd9a9c4cad358e282649e1106d409378bfa0960a0.
The next test is sameworld1440p/8chunks movement/stop FPS andvisualcorrectness;
leave open for boundedinputfallback logs. NoFPSgain from thiscandidate claimed.

## Menu strips — uploaded, awaiting console retest

User reports lowered-draw fix settles24–30FPS at1440p/8chunks, about35flying,
butmainmenu16–20FPS. Read artifacts/console-lowered-batching-retest; inputrejects
fell sharply. User completed30sec mainmenu test and explicitlyCLOSEDProsperoMC.
Freshmenulogs artifacts/console-menu-batching-retest session5 show mode5,index0,
count4strips; ~3400–3500singles perprofilinginterval. Otherrejectcategorieszero.
Verified pinned native source fromSDKtar supports primitive6TRISTRIP and queues
perdrawpreparedcommands withtopology, shadercachekeys includeprimitive. Candidate
onlyadmits non-indexedstrips in ps5_multidraw_eligible. Indexedstrips, restart,
indirect, attachmentfeedback andotherguards remainunchanged. Exactpredicate+
nativevalidator tests andread-only/publication regressionsPASS. Firsthosttest
neededstdintheader; repaired, latesttestPASS andbuildsession65121finished.
Rollback7ffe/patch/
provenance in artifacts/graphics-before-strip-batching. Candidatepatch
e98b54f8b965aa47735399ac3b6e2d5cd8344149179de57cc4c3f69001a03e53.
Localjavap ofclientbib.k() confirmsvanilla's menu30FPScap; nogamebytecodeedited.
NoFPSpromiseat16chunks, noJava/native/settings changes. CompiledBGRA/archive
checksPASS; onlyps5_screen.o changed, otherobjects/PSBCunchanged. Staging/imports/
rawsyscall/unboundchecksPASS; ntdll1c86 and76Winepatches retained. FTPcomparison
refreshed; graphics-onlyupload andexecutable/bothreportsreadbackPASS. Module:
910c698b7a3437ee878062be2e92a4241cb791df5bbf604e252be28c6a85ae56.
SDKmanifest87d824fed6dc73bafb7111d7a4a41e2517f6f98a27a88790fd4526dd16da3570;
runtimearchive ddae0d067b8b1ed82c1478a1add4d051bc019aa11d0af5b0fae28cafe0b76089.
Native/JAR remain06352734/722679be. Nativepresentationlog shows15–16calls per
~0.51sec inmenu, near30; user's16–20counter maymeasure differenttiming. Need
compareF3worldFPS vsdebugoverlay without fakingFPS; nooverlaycodechanged.
Latestupstreamcommit008a3c3b4d285199601d75624208d8e8e18ad2a7 checkedviaGitHub;
latest5commits areissue/release/template changes, no runtimeupdate applied.
Nexttest: menu/text/item rendering, menuFPS, same1440p8chunkworldF3FPS after
movementandstop; leaveopenforlogs. Afteraskingtestneedfreshclosebeforemorewrites.

## Deferred multi-draw candidate — uploaded

Userstripretest:1440p8chunks43–55FPS still,32–57walking; F3drops13–22.
16chunks7–22,10~20,lookdown/sky60. Screenshot actual2560x1440 andVBOenabled.
User explicitlyBOTHCLOSED thisturn. Freshlogs artifacts/console-strip-batching-retest
showeligible6812366,input8474,otherrejectszero;4014 multi-draw-batched linesin
last512KB. Definite oldpathwait:ps5_try_multi_draw_batch enterssubmit_lock then
callsbatch_end pergroup; nativebatch_end retiresallpending withwait1. RootdrawVbo
triesdeferred (onlynum_draws1) thenthissyncmulti path. Targetedguardnow dispatches
eligible num_draws>1 viaexisting Mesa util_draw_multi BEFOREsync/deferredattempt;
childrenuseexistingdeferredqueue/fences/resource+descriptorretention. No newqueue,
capacitychanges, native/Java/settings changes. Legacyconversionexcludedunless
alreadyqualifiedquadbatch; indirect/ineligible groups useoldpaths.

Actualroutingblock plusverifiedMesahelper testsPASS IDs (includingemptydraw),
guardcases; existingnative-strip/readmap/publication checksPASS. Buildsession74183
finishedsuccessfully. Rollback910c module/patch/provenance preserved
in artifacts/graphics-before-deferred-multidraw. Patch:
af938a3b9827e4225cbe4478cf448b6550a7e5af5a6ea012958185a1f60bc901.
CompiledBGRAcapability/archivechecksPASS; onlyps5_screen.o changed. Moduleimport/
rawsyscall/unboundchecksPASS, ntDLL/76Winepatches preserved. Staged, FTPview
79485completed. Usernoticedrapid slightflicker ondirectmonitor vs capturecard;
confirmedgamewasrunningagain, sohelduploadthenuserexplicitlyclosed. Scoped
graphics-onlyupload/readback thencompleted successfully; bothreportsverified.
Module2d25202c18f36607991424ce613ef3aed7c86619d425acb0fc6543ee8bbf8a20;
SDKmanifest867d47117e86c4e2bdb571d800cc152d7180ec9cf6d74b574ea89776518c2223;
runtimearchived3b3ed13d7ad4f324bb7e988f58815dd2ea39d5afcfd4bb7f4e57778a4806392.
No gainclaimed yet. Aftertestrequestmustgetfreshclosebeforemoreconsolewrites.

Flickerclassification asyncquestion pending: brightnesspulse vs tearing vsblack/
oldframe flashes; VRR/AdaptiveSyncstatusunknown. Readonlylivegameoptions show
renderDistance10,fullscreentrue,enableVsyncfalse,useVbotrue. Nooptionchangesmade.
Inspectednativependingflip-marker gate; thiscandidate doesnotalterpresenter.
Need FPS/visualretest1440p8/16chunks plusF3on/off andflickerclassification; do not
claimflickerfixed orblindlyforce60Hz/VSync withoutunderstandingobservedartifact.

Flickeranswer: slight veryrapid pulsevisibleonbright sky/sand, especially~20FPS,
no tearing; monitorFreeSyncON. Refresh-relatedbrightnessflicker isahypothesis,
notconfirmed. UsercomparisonFreeSyncoff requestedbeforefurtherpresenterchanges.
Currentmodule2d25202uploaded/readbackverified; sourcecommitted/pushed0739bf5.
NeedretestFPSwithF3on/offand8/16chunks plusflickerwithFreeSyncoff; leavegameopen
forfreshlogs. Latestclosurewasexplicitafteruserreopenedmidbuild. Afternewtest
requesttreatgamepotentiallyrunning; requirefreshclosebeforeanyfurtherwrites.

## Deferred multi-draw regression reverted — comparison pending

Userlatest:8chunks32FPS,10chunks24,16chunks15–16; lookingupthenbackdown can
settle10FPS, mousemovement worsens it. FreeSyncOFF removesflicker. Monitorwas
previouslynotset120Hz; now120, skyreaches120FPS. UserexplicitBOTHCLOSED.
Savedfresh artifacts/console-deferred-multidraw-retest (sessions2/3/4). Native
drawpreparation~20us/draw remainslarge; noGPUsubmitfailure orallocationfailure.
Do nottreatfpsresultsunderdifferentdisplayconfiguration aspreciseapples/apples.

Restoredprepare/compile scripts+versions.lockexactfrom9f23432; removedexperimental
check-deferred-multidraw.py. Regeneratedpatchmatches e98b54f8b965aa47735399ac3b6e2d5cd8344149179de57cc4c3f69001a03e53.
One-off artifacts/rollback-last-graphics.py verifiesexactbackup910c698b module,
patch/provenance andcurrentregressed2d25202c beforemutatingstagedfiles. Regressed
module/report/notice saved artifacts/graphics-regression-rollback. Restored
module,patch,notices+bothreports; validate_packagePASS. FTPview refreshed, scoped
graphics-onlyupload/readback executableandbothreportsPASS. NoJava/native/game
options/worldchanges. Restoredmodule:
910c698b7a3437ee878062be2e92a4241cb791df5bbf604e252be28c6a85ae56.
ItsSDKmanifest87d824fed6dc73bafb7111d7a4a41e2517f6f98a27a88790fd4526dd16da3570;
runtimearchive ddae0d067b8b1ed82c1478a1add4d051bc019aa11d0af5b0fae28cafe0b76089.
NOTE: .deps/graphics-sdk-batching and artifacts/wine-graphics-batching stillhold
rejected2d build. Do notstage them; sourcepatch mismatchguardshouldrejectstaging.
Nextgraphicsbuild mustprepare/compilefromrestoredsource first. Manualappbuild/send
usesrestoredstagedWine; don'tfullstageoriginalruntime. Earlierimprovementskeep.
Needcontrolledsamecamera1440p8/16chunk FPS,F3on/off,lookup/returntest withmonitor
120Hz andFreeSyncoff; leaveopenforlogs. Freshclosebeforefurtherwritesaftertest.

## Production descriptor-reuse fix and launcher input - uploaded, retest pending

The user explicitly rejected further rollback and requested root-cause fixes
plus controller/mouse support. Latest report: 8-24 FPS at 8 chunks. Both apps
were explicitly CLOSED this turn. Fresh read-only logs are saved under
artifacts/console-root-cause-retest (game session6, prepare5, launcher7).
The game destruction receipt records 2,522,286 descriptor-cache hits and
1,952,046 misses. Native command preparation remains about 20 microseconds
per draw. Successful synchronous groups log hundreds of lines per second.

The synchronous group cleanup already waits for GPU retirement but discards
its private descriptors. It now returns them to the existing bounded cache,
matching deferred cleanup. Shared/oversized/full-cache/unretired cases keep
conservative handling. Successful batches no longer print on the hot path;
errors remain. PS5_DRAW_PROFILE is disabled in BOTH the generated draw driver
and unchanged verified native-backend source. All other features and all
GPU fence/retirement checks stay enabled. PROSPEROMC_DRAW_PROFILE=1 supports
explicit diagnostic builds. This fixes observed code paths, not proof that
all terrain bottlenecks are solved or that any particular FPS target is met.

Actual generated cleanup ownership test, read-only map, buffer-publication,
input predicates, compiled BGRA capabilities and archive object checks PASS.
Archive check proves only ps5_screen.o and ps5_agc_runtime_backend.o change;
shader compiler and other runtime objects remain byte-identical to verified CI.
Production objects contain no per-draw profile reports, retain native batching,
and report profile=0. WSL graphics/Wine session4441 finished successfully;
all PRX import/raw-syscall/unbound checks passed.

Launcher now consumes HID motion, left/right click and wheel records, supports
mouse hit-testing on every page, and renders a pointer. List clicks select
rather than accidentally launching/downloading. D-pad and left stick navigate;
right stick moves pointer, R2 clicks; existing X/O/L1/R1 actions remain. HID
retries missing devices so plugging in a mouse after a keyboard can recover.
Mouse selection/scroll, busy guards, coordinate clamps and framebuffer tests
PASS. Native build84345 and runtime bridge/persistence suite PASS.

Both reports were staged with fresh eboot hash. Initial graphics staging
validation detected old eboot hash after native build; app staging synchronized
it and the graphics staging was rerun successfully. Full ELF comparison views
70305 finished. Scoped graphics-only and native-only uploads completed; both
executable readbacks and stage reports verified. Worlds/options/Java/JAR and
repaired ntdll remain unchanged. New hashes:
win32u 5ef251df23c2e00f85478c54a2cd7015d8a12b2e5b7449323579991e6b52a11b
eboot 5c1c679ed0c75e64329a0387830f06db285569b24b15cf898c52dde588314759
source patch cc048f1453f4f49049d727da545c9966585e32110b748cb9244e6a951d43da5f
SDK manifest f40ea2e5e0a9e49455c7f8e4789e13ed09961de81df2ddbdf3da5ba5b85b32ff
runtime archive 662483cfe466617f0beb2b5b65894a7bbf85c2abd1b1e2d6107785af486fa9d2

Async console retest requested: same world1440p/8chunks, F3 closed for30sec;
FPS plus look-sky/return persistence, and launcher mouse/controller checks.
Once requested treat the app as potentially running: need fresh close before
any further console mutation. Read-only logs remain authorized. The current
native/graphics source, artifacts and staged modules all match (no stale
experimental SDK now). Preserve three pre-existing deleted artwork source PNGs.


## Shader-layout cache follow-up - build running

User confirms launcher mouse works. Production retest, same1440p settings:
wandering25-35 then33-45FPS, stationary44-56, fastmouse~33, F3 16-32,
16chunks13-23; sky120 thenterrain33 (no return-to-terrain10FPS persistence
in this retest). User explicitly closed ProsperoMC; scope allows replacement.
Fresh read-only diagnostics: artifacts/console-production-retest, game session1.
Receipt confirms profile0, descriptorhits10801992/misses4658247, cache retained768;
no allocation failures. Pair cache nearshutdown:5200000lookups,5199964hot hits,
35entries,~1.23MB. Nearly every native draw still parses/validates both shader
packages BEFORE checking the paircache. This is redundant even on a cachehit.

Prepared sourcepatch now includes native runtime as well as driver. Native pair
stores validated section pointers/sizes inside its OWNED package snapshot.
Lookup-only call (NULL API) retains full pointer/size/topology/byte comparisons
and cannot allocate an unvalidated entry. Main tries this lookup before parsing;
only byte-identical cachehits skip parse/header validation. Mutation/addressreuse
still takes original path. Hull/tessellation, diagnostic and negative-package
paths retain existing parsing. GPU batches, submit, flush and retirement logic
are unchanged. No ASYNC_NATIVE_PREP enabled. Native two-worker mode exists in
upstream source but is experimental, busy-spins and pins cores10/12; do not
blindly enable it. Root command-generation costs remain another possible target.

Generated actual lookup/layout-assignment/main-routing plus actual ELF parser/
header validation tests PASS:10000 warm draws dozero parses/validations, mutated
VS/PS bytes, malformed ELF, wrongstage andtopologychanges runoriginalguards.
Descriptor ownership testPASS. CompiledBGRA andarchiveonly2objectchecksPASS.
Buildsession3403 is still buildingWine afterdrivercomplete/HOST_WINE_TOOLS_READY.
Do notstage until it completes. No newmodule uploaded yet. Current PS5win32u
still5ef251df23c2e00f85478c54a2cd7015d8a12b2e5b7449323579991e6b52a11b;
EBOOT5c1c679ed0c75e64329a0387830f06db285569b24b15cf898c52dde588314759.
Newsourcepatchf5c0bf8e0c3e8ce98ba926c7a6745ab0a8a740f81fa06dcb8b788ca7705bd505;
SDKd86909d374d310fac2fe0603f67271356e40d1daaed477f629a6113671352352;
archiveb0012defb867050d2f7cd1aeec698c4e4a39bf768c3257bb78abfb394d8e3e53.
README/versions/provenance pending edits reflect follow-up. Automatic build
checks added for shadercache anddescriptorretirement. Next: wait3403, stage
win32u, ELFcomparisonviewonlywin32u, scopedgraphicsupload+readback, checkpoint,
commit/push, samecameraF3on/off8/16chunkretest. Freshclose after requestingtest.


Shader-cache build3403 completed successfully; WIN32U_GRAPHICS_BUILD_COMPLETE.
PRX status/imports/rawsyscall/unbound checksPASS. Stage validationPASS; source
patch/provenance/compiledcapability hashesmatch. Win32u-onlyELFcomparisonview
finished. Scopedgraphics-onlyupload completed andexecutable+bothreports readback
verified. Newwin32u:
859f900e191e97780b1110d546043e87fbddba820fb12db676d727a52b306719
Native/JAR/Java/ntdll/worlds/options unchanged. Async retest asked for same
1440p8chunks withF3off/on, then16chunks, settled30seconds, leaveopenforlogs.
NoFPScandidategain claimed; usermustfreshclosebeforefurtherconsolemutation.


## Upstream two-worker native preparation - build running

Shader-cache retest:1440p8chunks wandering29-35 occasional40, returnfromsky35-40,
still43/44,fastmouse27-41,wandering35-38,F3~32;16chunks16-23mostly17/19.
MinecraftwasleftOPEN; read-onlylive logs saved artifacts/console-shader-cache-retest
(game4, prepare3, previouslauncher2). Noallocationfailures;~34pairentrieshotcache,
no evidenceof43FPSimposedcap;sky120. User thenexplicitlyCLOSEDbothapps viaasync
questioncall_v5k1MylO0JGYoR7DLkgDkN8w; canupload oncebuildchecksfinish.

Audited pinned upstream PS5_ASYNC_NATIVE_PREP code:producer snapshotsdraw/backend
andowns scanoutinit;two nativeworkers preparecommands oncores10/12. Results
collected strictlyindraworder;resourceownership staysuntilGPUretirement. Nonew
scheduler implemented. Nativepair/workcachemutexes areenabled byupstreamflag;
detailed profiling mustbeoff for2workers. Workerbusyspinning meansCPUusagecanrise.
Compilationdefaults nowasync2 forproduction;profile diagnosticbuilds remainsync.
PROSPEROMC_ASYNC_NATIVE_PREP=0 supports synchronouscomparison builds.

New scripts/check-upstream-async.py verifies original sourcearchiveSHA, extracts
UNMODIFIED upstream test_async_preflight.py andtest_async_native_draw.py, runs
thoseagainst OURgeneratednative sourceunderASan/UBSan. Both1/2workersPASS:
stateownership,reversedcompletion,ringwrap,dupresult,startup/pin failure,
orderedappend,tessellationdrain,shutdown. Shadercache/descriptor tests automatic
incompile recipe. CompiledBGRAandarchiveonly2objects checksPASS;archiveasserts
actualobjectworkerstartup+pthreadsymbols. Native/JAR/game settingsunchanged.

Firstbuild18015 failedbeforeWine dueentrypoint redefinition: asyncwrapperalready
namesps5_agc_gate2_run, mainmustberenamedps5_agc_gate2_run_sync. Fixedconditional
compilerdefinition. Secondbuild78187 drivercomplete/HOST_WINE_TOOLS_READY,
Winebuildstillrunning. DoNOTstageuntilfinished. Current PS5 win32u remains
859f900e191e97780b1110d546043e87fbddba820fb12db676d727a52b306719.
New SDKmanifest/archive hashes:
60f5c11c4043fd3a46f23e8074323f3968d4c28c4f935a8920841888376e3b39
9a2afa07eba8681ced0b0b1d9ca3fa9b02a0f79e319db05f3a164f3bd5714bb2
Sourcepatch unchangedf5c0bf8e0c3e8ce98ba926c7a6745ab0a8a740f81fa06dcb8b788ca7705bd505;
worker code isoriginalpinnedsource, activatedbyflags. versions.lock/README/
provenancedocs updatedpendingcandidate. Next:wait78187, imports/raw-syscall/
unboundchecks; stage+ELFview onlywin32u;scopedgraphicsupload/readback;checkpoint/
commitpush;retest same1440p8/16,F3on/offandverifylive[ps5-async-prep] cpu10/12
startupreceipts. Do notpromiseFPSorclaimworkersrunningbeforeconsoletest.
Afteraskinguserretestfreshclosebeforefurtherconsolewrites.


Secondworkerbuild78187 completedfully(exit0). Win32ureportstatus0, builttrue,
no unresolved/errors/titleunbound/rawsyscalls. Module staged successfully;
ELFview onlywin32urefreshed. Scopedgraphics-onlyupload andexecutable+bothreports
readbackPASS. Newmodule:
d02aa80a3e5c70d99828668883fb9d2e2c07048883afb687b75c577bf2b318be
Stage graphicsFix asyncNativePrepare=true,nativePrepareWorkers=2,drawProfile=false.
NoJava/JAR/native/world/optionschanges. UserexplicitCLOSEDbeforeuploadthisturn.
Asyncretestquestionasked: sameworld1440p8then16chunks,F3on/off,settle30seconds,
leaveopenforliveworkerstartup receipts. Needread[ps5-async-prep] cpu=10/12,
verified1,worker0/1 beforeclaimingbothworkersrunning. FPSgainunverified.
Afterrequesttreatgameasrunning;freshclosebeforeanyfurtherconsolewrites.


Live retest hasstartedwithoutuserFPSreplyyet. Read artifacts/console-worker-startup
session7: actual[ps5-async-prep] cpu10verified1worker0 andcpu12verified1worker1
at16921.623. So console workerstartup/affinity isNOWVERIFIED. GLswap logsadvance
68.3,77.8,78.8FPS in5sec windows16949-16959, butunknownuserchunk/camera atthose
intervals soNOspecificterrainFPSgainclaimed. frames_put507stalled briefly; that
counterisPwWineFrameBoxCPUframetransfersequence, NOTGLswap; realPW_GLcounter
continues. Investigatedratherthanassumingrenderfreeze. Userwasinworld andchat
commandSettime1000loggedat16952. CPU~3.2sper1s now (includesbusyworkers).
AppcurrentlyRUNNING, neveruploadwithoutfreshclose. AwaituserFPSat8/16chunks.

## Worker-local shader lookup follow-up - build running

User reports strong async gain at1440p/8chunks: wandering47-77 occasional90,
returnfromsky84-86, still90, fastmouse45-60, anotherwandering66-82, F337-65.
16chunks20-23 mostly22, F3~18; back8chunks45-51. User nowexplicitly CLOSED
ProsperoMC. Final full logs artifacts/console-worker-final/logs_session-7.log
show clean shutdown, dmem failures0, ~2.14GiBstablelate-run, profile0,
eligible15,070,193 vs inputreject35,652; descriptorhits54,140,136/misses15,768,381.

Audited immutable native shader-pair cache: all hot hits still took shared
mutex. Added single TLS last-pair pointer per worker; full key/length/topology
and entire owned-byte comparisons retained. Cold/changed hits still mutex+
original validation. Shutdown joinsworkers beforefree and clearsproducerTLS.
Actual generated wrapper ASan/UBSan test:200,000 concurrent hot hits bypasslock;
26warmup/mutationlookups lock. bytes/reusedkeys/sizes/topology/threadstatecovered.
Automatic buildcheck added. Original upstream async testsPASS. Capabilities
and archive-only2objects checksPASS. NoGPUownership/batching/window/settingschanges.

Buildsession2399: SMOOTH_QUAD_DRIVER_BUILD_COMPLETE and HOST_WINE_TOOLS_READY;
Wine link stillrunning. DO NOTstage untilsessionexit0. Currentconsolewin32u
stilld02aa80a3e5c70d99828668883fb9d2e2c07048883afb687b75c577bf2b318be.
Candidate sourcepatchc723e1981b48e267fb3630f0810062fbed6595f3337e02533ade664d72c0e0b3;
SDKfcce2e2a16722534c64c6e18a7af616d3b4598415f0b596a68cda2c93d594b87;
archive042a8e684d29851797387ff9a9ded7fc5dcf1159faecf7d6169bc259c41f6506.
Next wait2399; check/stage win32u; ELFview+scopedgraphicsupload+readback; checkpoint,
commitpush excluding3userPNGdeletions; samecamera1440p8/16F3on/offretet.
Sharedcache logs no longer count worker-local hits; don'ttreatdecreaseasdrawdecrease.

Worker-local cache build2399 completed exit0. Newwin32u
b0d6b0a44dc28087bcd6c0b32eec41dccec4e737c3e2d34e869ba084dfe57025.
Validated PRX status0/builttrue/noerrors, import/rawsyscall/unboundchecksPASS;
stage validatedsource/provenance/capabilities; ELFviewgenerated. Graphics-only
upload completed afteruserclose; executable and both reports readbackPASS.
Java/JAR/nativeEBoot/settings/worlds/ntdll unchanged. NewworkerTLSshadercache
FPS effectstillUNVERIFIED. Asyncsamecamera1440p8/16/back8 F3closedretetasked,
settle30sec, leaveopenforlogs. AfteraskingtreatgameasRUNNING; freshclosebefore
anyconsolewrite. SharedcachecountersexcludeTLSlocalhitsnow.

## Producer-only batch timings - build running
User latest b0d6 cache retest:1440p8 peak78-88,turn44-54;16 up30/low19/mostly24;
back8 peak70/low39/avg53. Live logs artifacts/console-worker-local-cache-retest
session2 show dmemfail0/~2.2GiB, GLswap55-78 late8 windows, 500ksharedcache
lookups (TLSlocalhits excluded), workersstartup verified. Read beforeclose.
User explicitCLOSED viaasyncquestioncall_df3c1c4b9a724576a55a087bb0cee77a.

Ratherthanblindalteration, added PROSPEROMC_BATCH_TIMINGS opt-in build. Uses
producer batchbegin/submit/drain/retire/present timestamps only; no draw/worker
instrumentation. Logsaggregate perframe5sec, draws/groups/batches, queuetime
(overlapsworkers), remainingworkerwait, submit, CPUretirementpollwait,reclaim,
present. GPUwait NOTGPUtotalbusytime. Defaultflag0; currentcandidateenv1.
Actualhelper/sourcecallsite check PASS. Existingupstream checksautomatic.
Buildsession9611 running, drivercompiled/SMOOTH_QUAD_DRIVER_BUILD_COMPLETE.
DonotstageuntilWinecomplete AND sessionexit0. CurrentPS5win32ub0d6...57025.
Newpatchd7ba55ad604d62db3d8d7976b53409addc0042fdfeddb579439d5206aad537ab;
SDKf59ee9d0a360163bded6af9b5a476b4d5c034c2fee79cf1958712089f2277f9a;
archived470ba6e6b78c1541556606c708ab5ef17903e10159458e4ab29ceba9b5f233f;
configc2d5f6abeda95a1cfaaa6c6c4884430c8c390f0fc066165f083b64453fc00ca7.
Nextwait9611; capabilities/archiveasserttimingstring+workers/profile0;
stage+ELFview+graphics-onlyupload+readback; checkpointcommitpush; request
8stationary/16stationary/back8turning~20sec eachthenleaveopenandreadtimings.
NoFPSimprovementpromisedforthisdiagnosticbuild. Needfreshcloseafteraskbeforenextwrite.

Batchtiming build9611 finishedexit0. PRX imports/rawsyscall/unboundstatusPASS;
capabilities/archivepreservation/checktimerlogsPASS. Staged win32u
 a61632e2936a064011b2d4ec0c90b15764f4b7b0e81bb9352e293e61598b83ed.
ELFviewgenerated;graphics-onlyupload afterexplicituserclosecomplete;
executable+bothreportsreadbackPASS. stagebatchTimings=true,profilefalse,
asyncNativePrepare=true,workers2. Native/JAR/Java/worlds/settings unchanged.
Asyncretetrequest: sameworld1440p,F3closed,8terrainstationary30sec,
16stationary30sec,back8turncamera30sec;replytestedleaveopenforlogs.
NextREADONLYstatussessionlogslookfor[prosperomc-batch-time], align windows
withdrawcounts/stableFPSpattern. Queueoverlapsworker time;gpuwaitCPUwaitonly;
if sumsmallrelativeframetimeinvestigateJava/GLproduceroutsidenativebatch.
DoNOTcallCPUwaittotalGPUbusytime. DoNOTusepairlookupsasdrawcount(TLSbypass).
TreatconsoleRUNNING afterrequest;freshclosebeforeanybinarymutation.
NextperformancebuildshoulddefaultPROSPEROMC_BATCH_TIMINGS=0unlessneeded.
