# Version selection and Java management

- [x] J1: Native selected-version download invokes automatic required-Java provisioning.
  EVIDENCE: One create-install native action, Mojang javaMajor metadata, backend29fixtures including automatic8/17/21/25; parent1.12.2newmanagedprepare PASS. ActualPS5execution remains unverified.
- [x] J2: InstalledWindowsx64 runtimes detected/reused and native download controls operate.
  EVIDENCE: Settings16-runtimeinventory and8/17/21/25download/repair buttons; parentdetected suppliedJava8 and actualdownloadedJava17. Endpoint-unavailable reuse test passed without redundantdownload.
- [x] J3: Hash, architecture, major and corrupt download failures tested.
  EVIDENCE:29backendfixtures PASS plusactualofficialJava17TLSdownload/SHA256/PE64java.exe+jvm.dll/releasevalidation and -version PASS. Wrongarch/platform/major/missingDLL/repairbackup/JDKfallback covered.
- [x] J4: Updated native frontend/bridge compiled and final staged hashes match.
  EVIDENCE: EBOOTce2c6f5f3fc786059f245a1918d39bfcc80dbdc902bf18a2d7124f376e965991; JAR3e9d0f7bb75b32d4751b63d800279847ba4fed13add345cbecbac12deefc1cba. Parentnativefrontend/bridge+4stagechecks PASS. Deployvalidate-only PACKAGE_HASHES_VALID.
