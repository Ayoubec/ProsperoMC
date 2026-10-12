Controlify was identifying the PS5's DualSense as Xbox because the existing
title input bridge exposes standardized XInput state with VID/PID045e:028e.
The console log and installed Controlify3.5.0+mc26.2 JAR confirm this path.
The actual mod JAR SHA256 is
710a7a8cc21ebfaddd29f6a15da1b6cf3d8de4098269a2534d06ac65ba8fa186.

Controlify's ControllerTypeManager reads every resource-pack layer of
assets/controlify/controllers/controller_identification.json5 and gives the
later layer priority for an existing HID identity. ControllerEntity.name uses
the identified type's friendlyName. Its built-in controlify:dualsense namespace
already supplies PlayStation button glyphs. This is the supported extension
point used by the repair; neither the mod JAR nor its controller profiles are
rewritten.

When preparing a console native-controller launch with a compatible installed
Controlify, the launcher creates its owned prosperomc-dualsense resource pack.
It maps only045e:028e to DualSense Controller/controlify:dualsense and enables
that pack last, preserving the other selected packs and all bindings/settings.
Minecraft's resource format is read from the verified client JAR version.json;
26.2 uses88.0. Modern resource formats65+ use min_format/max_format without
the prohibited supported_formats field; older formats retain the legacy schema.
The original options file is backed up once. Foreign pack folders,
unexpected ownership markers and invalid selections are rejected before options
are changed. Host, keyboard-emulation and absent/unsupported mod paths do not
add the pack. Managed files are repaired on subsequent launches if an earlier
write was interrupted.

SDL still discovers the transport's real capabilities. This change provides
DualSense identification and PlayStation prompts over the existing working
input/rumble bridge; it does not fabricate Sony HID gyro, adaptive-trigger or
audio-haptic capabilities.

The installed mod/client fixture checks the extension contract, exact bridge
identity, resource format, retained packs/options/controller profiles,
idempotence, original backup, host/keyboard/no-mod guards and ownership/invalid
selection refusal. The first2866f3d1 launcher update was uploaded and readback
verified, but session6 rejected its deprecated supported_formats metadata and
identified Xbox again. The corrected schema is verified using the actual26.2
PackFormat client codec, which rejects the original and accepts the generated
replacement. Console identity/prompts remain pending after this correction.

Primary extension implementation:
https://github.com/isXander/Controlify/blob/main/src/main/java/dev/isxander/controlify/controller/id/ControllerTypeManager.java
