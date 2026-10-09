/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PM_FRONTEND_H
#define PM_FRONTEND_H
#include "pw_present.h"

#ifdef __cplusplus
extern "C" {
#endif

#define PM_MAX_INSTANCES 64
#define PM_MAX_VERSIONS 2048
#define PM_MAX_MODS 128
#define PM_MAX_JAVA 16
#define PM_TEXT 192

typedef struct PmInstance {
    char id[PM_TEXT], name[PM_TEXT], version[64], loader[64];
    int installed;
} PmInstance;
typedef struct PmVersion { char id[64], type[32]; int java; } PmVersion;
typedef struct PmMod { char name[PM_TEXT]; int enabled; } PmMod;
typedef struct PmJavaRuntime {
    int major, valid;
    char version[64], path[512], detail[PM_TEXT];
} PmJavaRuntime;
typedef struct PmView {
    char status[64], detail[512];
    PmInstance instances[PM_MAX_INSTANCES]; int instance_count;
    PmVersion versions[PM_MAX_VERSIONS]; int version_count;
    PmMod mods[PM_MAX_MODS]; int mod_count;
    PmJavaRuntime java_runtimes[PM_MAX_JAVA]; int java_count;
    int memory_mb, busy, progress_done, progress_total;
    char java_path[512], username[PM_TEXT];
    char auth_url[256], auth_code[64], account_status[PM_TEXT];
    char account_mode[16];
} PmView;

typedef enum PmScreen {
    PM_HOME, PM_LIBRARY, PM_VERSIONS, PM_MODS, PM_SETTINGS, PM_ACCOUNTS,
    PM_SCREEN_COUNT
} PmScreen;
typedef enum PmKey {
    PM_KEY_NONE, PM_KEY_UP, PM_KEY_DOWN, PM_KEY_LEFT, PM_KEY_RIGHT,
    PM_KEY_CONFIRM, PM_KEY_BACK, PM_KEY_PREVIOUS_TAB, PM_KEY_NEXT_TAB,
    PM_KEY_SECONDARY, PM_KEY_REFRESH
} PmKey;
/* Runtime serializes non-empty fields into request.properties. No raw shell input. */
typedef struct PmAction {
    char command[32], id[PM_TEXT], version[64], name[PM_TEXT];
    char loader[32], loader_version[64], source[512], username[PM_TEXT];
    char mod[PM_TEXT], enabled[8], java_path[512];
    char account_mode[16];
    int memory_mb;
    int java_major;
} PmAction;
typedef struct PmFrontend {
    PmScreen screen;
    int selected_instance, selected_version, selected_mod, selected_java;
    int focus, memory_mb, loader_index, version_filter;
    int initialized_settings;
    char notice[PM_TEXT];
} PmFrontend;

void pm_frontend_init(PmFrontend *frontend);
/* Returns 1 only for a backend command; caller invokes it and reloads PmView. */
int pm_frontend_update(PmFrontend *frontend, const PmView *view,
                       PmKey key, PmAction *action);
/* Native BGRX8 framebuffer. Any size is scaled from the 1920 x 1080 design. */
void pm_frontend_render(const PmFrontend *frontend, const PmView *view,
                        const PwPresentTarget *target);

#ifdef __cplusplus
}
#endif
#endif
