# Microsoft sign-in setup

ProsperoMC uses Microsoft's device authorization flow. After setup, select
Accounts → Microsoft → Start sign-in. The launcher shows a verification address
and short code. Open the address on your phone or PC, enter the code, and sign in
on Microsoft's site. Return to ProsperoMC and select Check sign-in. Your Microsoft
password is never entered into or stored by ProsperoMC.

The current build has no Microsoft application ID configured. This prevents the
device-code request from starting; changing account mode alone cannot log in.
ProsperoMC needs its own registered public-client application. PolyMC asks
rebranded projects to change its API keys, so we do not borrow PolyMC's client ID.

## Register the application

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
application's access with Microsoft; do not disable ownership checks or substitute
another launcher's ID.

This setup has not been verified with a registered ProsperoMC application yet.
