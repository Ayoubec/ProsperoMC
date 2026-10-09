/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PM_BRIDGE_H
#define PM_BRIDGE_H
#include "pm_frontend.h"
#include "pw_game_profile.h"
/* Minecraft-only file bridge. It never scans directories for executables. */
int pm_bridge_initialize(const char *root, const char *app0);
int pm_bridge_view(const char *root, PmView *view);
int pm_bridge_request(const char *root, const PmAction *action);
int pm_bridge_backend(const char *root, PwGameProfile *profile);
int pm_bridge_game(const char *root, PwGameProfile *profile);
int pm_bridge_consume_launch(const char *root);
int pm_bridge_frontend_save(const char *root, const PmFrontend *frontend);
void pm_bridge_frontend_load(const char *root, PmFrontend *frontend);
void pm_bridge_notice(const char *root, const char *message);
/* Claim the first empty-catalog fetch once, including across title restarts. */
int pm_bridge_auto_catalog(const char *root, const PmView *view);
/* 1 handled locally, 0 requires Java, -1 local operation failed. */
int pm_bridge_local(const char *root, const PmAction *action, PmView *view);
int pm_bridge_response_ready(const char *root);
int pm_bridge_prepare_prefix(const char *root);
#endif
