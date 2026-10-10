# Microsoft sign-in

ProsperoMC uses Microsoft's device authorization flow. Select
Accounts → Microsoft → Start sign-in. The launcher shows a QR code, verification
address and short code. Scan the QR or open the address on your phone or PC, enter the code, and sign in
on Microsoft's site. Return to ProsperoMC and select Check sign-in. Your Microsoft
password is never entered into or stored by ProsperoMC.

At the project owner's request, this build defaults to PolyMC's published public
client ID `6b329578-bfec-42a3-b503-303ab3f2ac96`. The launcher displays that provider,
and Microsoft's consent identifies PolyMC. This is public application configuration,
not an account password or secret. An absent or empty `microsoftClientId` selects
this option; a configured value selects the custom application.

[PolyMC's CMake configuration](https://github.com/PolyMC/PolyMC/blob/master/CMakeLists.txt)
asks rebranded projects to change its API IDs. This compatibility option does not
imply PolyMC endorses ProsperoMC or guarantees availability of its ID. For an
independent distribution, register ProsperoMC's own public application as below.

## Optional custom application

Use Microsoft's [application registration guide](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app).
Register ProsperoMC with personal Microsoft accounts enabled, and enable public
client flows in its Authentication settings. Copy the Application (client) ID.
Do not create or put a client secret into this launcher: device authorization is
a public-client flow. See [Microsoft's device-flow documentation](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code).

With ProsperoMC closed, edit `/data/ProsperoMC/settings.properties` over FTP.
Keep its existing settings and add this line, replacing the example with your ID:

```properties
microsoftClientId=00000000-0000-0000-0000-000000000000
```

Reopen the launcher and start sign-in. The Xbox and Minecraft Services requests
still need to succeed, and Minecraft Java ownership is checked. Receiving a
Microsoft login code alone does not prove the application has Minecraft API
access. If those services reject the registered application, resolve that
application's access with Microsoft; ownership verification remains enabled.

The packaged Java 8 backend successfully requested a real Microsoft device code
with the PolyMC ID. Complete console sign-in and Minecraft account verification
still need a user authorization test. A separate PS5 browser is not needed for
this phone/PC flow.
