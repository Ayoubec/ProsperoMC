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
typedef struct PmPack { char name[PM_TEXT], source[512]; } PmPack;
typedef struct PmRemotePack { char id[64], name[PM_TEXT], description[512]; } PmRemotePack;
typedef struct PmPackRelease { char id[64], name[PM_TEXT], game[64], loader[32]; } PmPackRelease;
typedef struct PmJavaRuntime {
    int major, valid;
    char version[64], path[512], detail[PM_TEXT];
} PmJavaRuntime;
typedef struct PmView {
    char status[64], detail[512];
    PmInstance instances[PM_MAX_INSTANCES]; int instance_count;
    PmVersion versions[PM_MAX_VERSIONS]; int version_count;
    PmMod mods[PM_MAX_MODS]; int mod_count;
    PmPack packs[PM_MAX_INSTANCES]; int pack_count;
    PmRemotePack remote_packs[24]; int remote_count, remote_offset, remote_total;
    PmPackRelease remote_versions[64]; int remote_version_count;
    char remote_project[64];
    PmJavaRuntime java_runtimes[PM_MAX_JAVA]; int java_count;
    int memory_mb, busy, progress_done, progress_total, resolution_height;
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
    char project_id[64], pack_version[64], query[129];
    int offset;
    int memory_mb;
    int resolution_height;
    int java_major;
} PmAction;
typedef struct PmFrontend {
    PmScreen screen;
    int selected_instance, selected_version, selected_mod, selected_java;
    int focus, memory_mb, loader_index, version_filter;
    int initialized_settings;
    int resolution_index;
    int pack_picker, selected_pack;
    int remote_browser, remote_stage, selected_remote, selected_release;
    int search_editor, search_key;
    char query[129];
    unsigned animation_ms, focus_ms;
    int underline_x;
    int pointer_x, pointer_y, pointer_visible;
    char notice[PM_TEXT];
} PmFrontend;

void pm_frontend_init(PmFrontend *frontend);
void pm_frontend_tick(PmFrontend *frontend, unsigned elapsed_ms);
/* Printable USB keys and backspace feed the same search field as the pad. */
void pm_frontend_text(PmFrontend *frontend, unsigned key);
/* Returns 1 only for a backend command; caller invokes it and reloads PmView. */
int pm_frontend_update(PmFrontend *frontend, const PmView *view,
                       PmKey key, PmAction *action);
/* Pointer coordinates use the same 1920x1080 design as rendering. Button is
 * a press edge: 1 left/select, 2 right/back, 0 motion or wheel only. */
int pm_frontend_pointer(PmFrontend *frontend, const PmView *view,
                       int x, int y, int button, int wheel, PmAction *action);
/* Native BGRX8 framebuffer. Any size is scaled from the 1920 x 1080 design. */
void pm_frontend_render(const PmFrontend *frontend, const PmView *view,
                        const PwPresentTarget *target);

#ifdef __cplusplus
}
#endif
#endif
