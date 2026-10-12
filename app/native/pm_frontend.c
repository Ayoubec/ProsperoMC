/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "pm_frontend.h"
#include <stdio.h>
#include <string.h>
#include "pm_font.h"
#include "pm_art.h"
#include "../../vendor/qrcodegen/qrcodegen.h"
#define BASE 0x090e0c
#define PANEL 0x121d18
#define ROW 0x1a2921
#define EDGE 0x344a3c
#define FOCUS 0x273c2f
#define LIME 0xb4e777
#define TITLE 0xf4f3e6
#define TEXT 0xdde4d9
#define MUTED 0xa8b7ac
#define FAINT 0x81978a
#define WARN 0xf2b397
static int bound(int n, int lo, int hi)
{
    return n < lo ? lo : n > hi ? hi : n;
}
static int count(int n, int cap)
{
    return bound(n, 0, cap);
}
static void copy(char *to, size_t n, const char *from)
{
    if (n)
        snprintf(to, n, "%s", from ? from : "");
}
static const char *tabs[] = {"Home", "Library", "Add Instance", "Content", "Settings", "Accounts"};
static const char *loaders[] = {"vanilla", "fabric", "quilt", "forge", "neoforge"};
static const char *filters[] = {"All versions", "Releases", "Snapshots"};
static const char *kinds[] = {"mods", "resourcepacks", "shaderpacks"};
static const char *kind_labels[] = {"Mods", "Resource Packs", "Shader Packs"};
static const int java_majors[] = {8, 17, 21, 25};
static const int resolution_heights[] = {720, 1080, 1440, 2160};
static const char *resolution_labels[] = {"1280 x 720", "1920 x 1080", "2560 x 1440",
                                          "3840 x 2160"};
static const char *graphics_values[] = {"zink", "vulkan"};
static const char *graphics_labels[] = {"OpenGL (Zink)", "Vulkan (native PS5)"};
static const char *input_values[] = {"emulated", "native"};
static const char *input_labels[] = {"Emulated mouse / keyboard", "Native gamepad (Controllify)"};
static const char *theme_values[] = {"grass", "ocean", "diamond", "amethyst", "redstone", "gold"};
static const char *theme_labels[] = {"Grass", "Ocean", "Diamond", "Amethyst", "Redstone", "Gold"};
static const uint32_t theme_colors[] = {0xb4e777, 0x7dbaff, 0x70e6dc, 0xc6a1ff, 0xff9696, 0xf5d379};
static const uint32_t theme_backgrounds[] = {0x090e0c,0x090f1c,0x071512,0x140e21,0x1b0b10,0x1b1609};
static PmIconLoader icon_loader;
void pm_frontend_set_icon_loader(PmIconLoader loader)
{
    icon_loader = loader;
}
static int text_width(const char *s, int size);
static int content_matches(const PmFrontend *f, const PmView *v);
static const PmInstance *selected_instance(const PmFrontend *f, const PmView *v)
{
    int n = count(v->instance_count, PM_MAX_INSTANCES);
    return n ? &v->instances[bound(f->selected_instance, 0, n - 1)] : NULL;
}
static int visible_version(const PmFrontend *f, const PmVersion *v)
{
    return !f->version_filter ||
           (f->version_filter == 1 && (!v->type[0] || !strcmp(v->type, "release"))) ||
           (f->version_filter == 2 && !strcmp(v->type, "snapshot"));
}
static int next_version(const PmFrontend *f, const PmView *v, int from, int delta)
{
    for (int j = from; j >= 0 && j < count(v->version_count, PM_MAX_VERSIONS); j += delta)
        if (visible_version(f, &v->versions[j]))
            return j;
    return -1;
}
static int list_start(int selection, int rows)
{
    return selection / rows * rows;
}
void pm_frontend_init(PmFrontend *f)
{
    if (!f)
        return;
    memset(f, 0, sizeof(*f));
    f->memory_mb = 2048;
    f->version_filter = 1;
    f->header_focus = -1;
    f->add_source = -1;
    f->underline_x = 478;
    f->pointer_x = 960;
    f->pointer_y = 540;
    f->remote_focus = 1;
}
void pm_frontend_tick(PmFrontend *f, unsigned ms)
{
    if (!f)
        return;
    ms = ms > 100 ? 100 : ms;
    f->animation_ms += ms;
    f->focus_ms = bound((int)f->focus_ms + (int)ms, 0, 180);
    f->transition_ms = f->transition_ms > ms ? f->transition_ms - ms : 0;
    int x = 470;
    for (int j = 0; j < (int)f->screen; j++)
        x += text_width(tabs[j], 24) + 43;
    int distance = x - f->underline_x;
    int step = distance * (int)ms / 80;
    if (!step && distance && ms) step = distance > 0 ? 1 : -1;
    f->underline_x += distance > 0 ? bound(step, 0, distance) : bound(step, distance, 0);
}
static void normalize(PmFrontend *f, const PmView *v)
{
    f->screen = (PmScreen)bound(f->screen, 0, PM_SCREEN_COUNT - 1);
    f->selected_instance = bound(f->selected_instance, 0,
                                 count(v->instance_count, PM_MAX_INSTANCES)
                                     ? count(v->instance_count, PM_MAX_INSTANCES) - 1
                                     : 0);
    f->selected_version = bound(f->selected_version, 0,
                                count(v->version_count, PM_MAX_VERSIONS)
                                    ? count(v->version_count, PM_MAX_VERSIONS) - 1
                                    : 0);
    f->selected_mod =
        bound(f->selected_mod, 0,
              count(v->mod_count, PM_MAX_MODS) ? count(v->mod_count, PM_MAX_MODS) - 1 : 0);
    f->selected_java =
        bound(f->selected_java, 0,
              count(v->java_count, PM_MAX_JAVA) ? count(v->java_count, PM_MAX_JAVA) - 1 : 0);
    f->loader_index = bound(f->loader_index, 0, 4);
    f->version_filter = bound(f->version_filter, 0, 2);
    f->content_kind = bound(f->content_kind, 0, 2);
    f->header_focus = bound(f->header_focus, -1, PM_SCREEN_COUNT);
    f->focus = bound(f->focus, 0,
                     f->screen == PM_SETTINGS   ? 11
                     : f->screen == PM_MODS     ? 6
                     : f->screen == PM_LIBRARY  ? 5
                     : f->screen == PM_VERSIONS ? 3
                     : f->screen == PM_ACCOUNTS ? 2
                                                : 1);
    f->memory_mb = bound(f->memory_mb, 512, 8192);
    f->resolution_index = bound(f->resolution_index, 0, 3);
    f->graphics_index = bound(f->graphics_index, 0, 1);
    f->input_index = bound(f->input_index, 0, 1);
    f->theme_index = bound(f->theme_index, 0, 5);
    f->vrr_index = bound(f->vrr_index, 0, 1);
    f->remote_focus = bound(f->remote_focus, 0, 1);
    /* Provider pages are real Add Instance pages, not transient overlays.
     * Restoring the saved source must restore its search/catalogue too. */
    if (f->screen == PM_VERSIONS && (f->add_source == 1 || f->add_source == 2))
        f->remote_browser = 1;
    if (!f->initialized_settings)
    {
        f->memory_mb = v->memory_mb ? bound(v->memory_mb, 512, 8192) : 2048;
        f->graphics_index = !strcmp(v->graphics, "vulkan");
        f->input_index = !strcmp(v->controller_mode, "native");
        f->vrr_index = !strcmp(v->vrr_mode, "stable");
        for (int j = 0; j < 6; j++)
            if (!strcmp(v->theme_color, theme_values[j])) f->theme_index = j;
        for (int j = 0; j < 4; j++)
            if (v->resolution_height == resolution_heights[j])
                f->resolution_index = j;
        f->initialized_settings = 1;
    }
    if (count(v->version_count, PM_MAX_VERSIONS) &&
        !visible_version(f, &v->versions[f->selected_version]))
    {
        int j = next_version(f, v, 0, 1);
        if (j >= 0)
            f->selected_version = j;
    }
}
static int action(PmAction *a, const char *command, const PmInstance *i)
{
    copy(a->command, sizeof(a->command), command);
    if (i)
        copy(a->id, sizeof(a->id), i->id);
    return 1;
}
static int unavailable(PmFrontend *f, const char *reason)
{
    copy(f->notice, sizeof(f->notice), reason);
    return 0;
}
static int content_action(PmFrontend *f, PmAction *a, const char *command, const PmInstance *i)
{
    copy(a->content_kind, sizeof(a->content_kind), kinds[f->content_kind]);
    return action(a, command, i);
}
static int switch_screen(PmFrontend *f, const PmView *v, PmScreen screen, PmAction *a)
{
    f->transition_direction = screen < f->screen ? -1 : 1;
    f->transition_ms = 220;
    f->screen = screen;
    f->focus = 0;
    f->header_focus = -1;
    f->pack_picker = 0;
    f->remote_browser = 0;
    f->search_editor = 0;
    f->notice[0] = 0;
    if (screen == PM_VERSIONS)
        f->add_source = -1;
    if (screen == PM_MODS)
        f->query[0] = 0;
    if (screen == PM_MODS && selected_instance(f, v) && !v->busy)
        return content_action(f, a, "content-list", selected_instance(f, v));
    return 0;
}
static const char search_keys[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -";
static const char rename_keys[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -._";
void pm_frontend_text(PmFrontend *f, unsigned key)
{
    if (!f || (!f->search_editor && !f->rename_editor))
        return;
    char *buffer = f->rename_editor ? f->rename_text : f->query;
    size_t capacity = f->rename_editor ? sizeof(f->rename_text) : sizeof(f->query);
    if (f->rename_editor && f->rename_replace && (key == 8 || (key >= 32 && key <= 126)))
    {
        buffer[0] = 0;
        f->rename_replace = 0;
    }
    size_t n = strlen(buffer);
    if (key == 8)
    {
        if (n)
            buffer[n - 1] = 0;
    }
    else if (key >= 32 && key <= 126 && n < capacity - 1)
    {
        buffer[n] = (char)key;
        buffer[n + 1] = 0;
    }
}
static int remote_search(PmFrontend *f, const PmView *v, PmAction *a, int offset)
{
    copy(a->query, sizeof(a->query), f->query);
    a->offset = offset;
    f->remote_stage = 0;
    f->selected_remote = 0;
    f->remote_focus = 1;
    f->search_editor = 0;
    if (f->screen == PM_MODS)
        return content_action(f, a, "content-search", selected_instance(f, v));
    return action(a, f->add_source == 2 ? "curse-search" : "pack-search", NULL);
}
static int remote_update(PmFrontend *f, const PmView *v, PmKey key, PmAction *a)
{
    int releases = f->remote_stage,
        n = count(releases ? v->remote_version_count : v->remote_count, releases ? 64 : 24);
    int *sel = releases ? &f->selected_release : &f->selected_remote;
    *sel = bound(*sel, 0, n ? n - 1 : 0);
    if (f->search_editor)
    {
        if (key == PM_KEY_BACK)
        {
            f->search_editor = 0;
            if (f->screen == PM_MODS)
            {
                f->remote_browser = 0;
                f->remote_stage = 0;
            }
            return 0;
        }
        if (key == PM_KEY_LEFT)
            f->search_key = bound(f->search_key - 1, 0, 39);
        if (key == PM_KEY_RIGHT)
            f->search_key = bound(f->search_key + 1, 0, 39);
        if (key == PM_KEY_UP)
            f->search_key = bound(f->search_key - 10, 0, 39);
        if (key == PM_KEY_DOWN)
            f->search_key = bound(f->search_key + 10, 0, 39);
        if (key == PM_KEY_SECONDARY)
            pm_frontend_text(f, 8);
        if (key == PM_KEY_REFRESH || (key == PM_KEY_CONFIRM && f->search_key == 39))
            return v->busy ? unavailable(f, "Wait for the current operation.")
                           : remote_search(f, v, a, 0);
        if (key == PM_KEY_CONFIRM)
            pm_frontend_text(f, f->search_key == 38 ? 8 : (unsigned)search_keys[f->search_key]);
        return 0;
    }
    if (key == PM_KEY_BACK)
    {
        if (releases)
            f->remote_stage = 0;
        else
        {
            f->remote_browser = 0;
            if (f->screen == PM_VERSIONS)
                f->add_source = -1;
        }
        return 0;
    }
    if (key == PM_KEY_SECONDARY)
    {
        f->search_editor = 1;
        f->search_key = 0;
        return 0;
    }
    if (!releases && !n)
        f->remote_focus = 0;
    if (key == PM_KEY_UP)
    {
        if (*sel > 0 && f->remote_focus == 1)
            (*sel)--;
        else
            f->remote_focus = 0;
    }
    if (key == PM_KEY_DOWN)
    {
        if (f->remote_focus == 0)
            f->remote_focus = 1;
        else
            *sel = bound(*sel + 1, 0, n ? n - 1 : 0);
    }
    if (key == PM_KEY_CONFIRM && f->remote_focus == 0)
    {
        f->search_editor = 1;
        f->search_key = 0;
        return 0;
    }
    if (v->busy)
        return 0;
    if (!releases && f->remote_focus == 1 && (key == PM_KEY_LEFT || key == PM_KEY_RIGHT))
    {
        int offset = v->remote_offset + (key == PM_KEY_RIGHT ? 24 : -24);
        if (offset >= 0 && offset < v->remote_total)
            return remote_search(f, v, a, offset);
        return 0;
    }
    if (key == PM_KEY_REFRESH)
        return remote_search(f, v, a, 0);
    if (key == PM_KEY_CONFIRM && n)
    {
        if (!releases)
        {
            copy(a->project_id, sizeof(a->project_id), v->remote_packs[*sel].id);
            f->remote_stage = 1;
            f->selected_release = 0;
            return f->screen == PM_MODS
                       ? content_action(f, a, "content-versions", selected_instance(f, v))
                       : action(a, f->add_source == 2 ? "curse-versions" : "pack-versions", NULL);
        }
        if (!v->remote_project[0])
            return unavailable(f, "Choose a project first.");
        copy(a->project_id, sizeof(a->project_id), v->remote_project);
        copy(a->pack_version, sizeof(a->pack_version), v->remote_versions[*sel].id);
        return f->screen == PM_MODS
                   ? content_action(f, a, "content-download", selected_instance(f, v))
                   : action(a, f->add_source == 2 ? "curse-download" : "pack-download", NULL);
    }
    return 0;
}
static void confirm(PmFrontend *f, const PmView *v, int kind)
{
    f->confirmation = kind;
    f->confirmation_choice = 0;
    const PmInstance *i = selected_instance(f, v);
    copy(f->confirmation_id, sizeof(f->confirmation_id), i ? i->id : "");
    copy(f->confirmation_file, sizeof(f->confirmation_file),
         count(v->mod_count, PM_MAX_MODS) ? v->mods[f->selected_mod].name : "");
}
static int add_source(PmFrontend *f, const PmView *v, int source, PmAction *a)
{
    f->add_source = source;
    f->focus = 0;
    if (source == 1 || source == 2)
    {
        f->remote_browser = 1;
        f->query[0] = 0;
        return remote_search(f, v, a, 0);
    }
    if (source == 3)
    {
        f->pack_picker = 1;
        return action(a, "scan-packs", NULL);
    }
    f->loader_index = 0;
    return v->version_count ? 0 : action(a, "catalog", NULL);
}
int pm_frontend_update(PmFrontend *f, const PmView *v, PmKey key, PmAction *a)
{
    if (!f || !v || !a)
        return 0;
    memset(a, 0, sizeof(*a));
    normalize(f, v);
    const PmInstance *i = selected_instance(f, v);
    int n = count(v->instance_count, PM_MAX_INSTANCES),
        delta = key == PM_KEY_DOWN || key == PM_KEY_RIGHT ? 1 : -1;
    if (key == PM_KEY_NONE)
        return 0;
    f->focus_ms = 0;
    if (f->rename_editor)
    {
        if (key == PM_KEY_BACK) { f->rename_editor = 0; return 0; }
        if (key == PM_KEY_LEFT || key == PM_KEY_RIGHT)
            f->rename_key = bound(f->rename_key + delta, 0, 44);
        if (key == PM_KEY_UP || key == PM_KEY_DOWN)
            f->rename_key = bound(f->rename_key + delta * 9, 0, 44);
        if (key == PM_KEY_SECONDARY) pm_frontend_text(f, 8);
        if (key == PM_KEY_REFRESH || (key == PM_KEY_CONFIRM && f->rename_key == 43))
        {
            if (v->busy || !i || strcmp(i->id, f->rename_id))
                return unavailable(f, "Wait for the current operation before renaming.");
            if (!f->rename_text[0]) return unavailable(f, "Enter an instance name.");
            copy(a->name, sizeof(a->name), f->rename_text);
            f->rename_editor = 0;
            return action(a, "rename-instance", i);
        }
        if (key == PM_KEY_CONFIRM)
        {
            if (f->rename_key < 40)
            {
                unsigned letter = (unsigned char)rename_keys[f->rename_key];
                if (f->rename_lower && letter >= 'A' && letter <= 'Z') letter += 'a' - 'A';
                pm_frontend_text(f, letter);
            }
            else if (f->rename_key == 40) pm_frontend_text(f, 8);
            else if (f->rename_key == 41) { f->rename_text[0] = 0; f->rename_replace = 0; }
            else if (f->rename_key == 42) f->rename_lower = !f->rename_lower;
            else if (f->rename_key == 44) f->rename_editor = 0;
        }
        return 0;
    }
    if (f->confirmation)
    {
        if (key == PM_KEY_BACK)
        {
            f->confirmation = 0;
            return 0;
        }
        if (key == PM_KEY_LEFT)
            f->confirmation_choice = 0;
        if (key == PM_KEY_RIGHT)
            f->confirmation_choice = 1;
        if (key == PM_KEY_CONFIRM)
        {
            int kind = f->confirmation;
            f->confirmation = 0;
            if (!f->confirmation_choice)
                return 0;
            if (kind == 2)
                return action(a, "quit", NULL);
            if (v->busy)
                return unavailable(f, "Wait for the current operation before deleting.");
            if (!i || strcmp(i->id, f->confirmation_id))
                return 0;
            if (kind == 1)
                return action(a, "delete-instance", i);
            if (!count(v->mod_count, PM_MAX_MODS))
                return 0;
            if (!content_matches(f, v))
                return 0;
            copy(a->mod, sizeof(a->mod), f->confirmation_file);
            return content_action(f, a, "content-delete", i);
        }
        return 0;
    }
    if (f->selector_popup)
    {
        int cap = f->selector_popup == 1 ? 30 : f->selector_popup == 2 ? 3 : f->selector_popup == 5 ? 5 : 1;
        if (key == PM_KEY_BACK)
        {
            f->selector_popup = 0;
            return 0;
        }
        if (key == PM_KEY_UP || key == PM_KEY_DOWN)
            f->selector_choice = bound(f->selector_choice + delta, 0, cap);
        if (key == PM_KEY_CONFIRM)
        {
            if (f->selector_popup == 1)
                f->memory_mb = 512 + f->selector_choice * 256;
            else if (f->selector_popup == 2)
                f->resolution_index = f->selector_choice;
            else if (f->selector_popup == 3)
                f->graphics_index = f->selector_choice;
            else if (f->selector_popup == 5)
            {
                f->theme_index = f->selector_choice;
                copy(a->theme_color,sizeof(a->theme_color),theme_values[f->theme_index]);
                f->selector_popup=0;
                return action(a,"settings",NULL);
            }
            else
                f->input_index = f->selector_choice;
            f->selector_popup = 0;
        }
        return 0;
    }
    if (key == PM_KEY_PREVIOUS_TAB || key == PM_KEY_NEXT_TAB)
        return switch_screen(
            f, v,
            (PmScreen)((f->screen + (key == PM_KEY_NEXT_TAB ? 1 : PM_SCREEN_COUNT - 1)) %
                       PM_SCREEN_COUNT),
            a);
    if (f->header_focus >= 0)
    {
        if (key == PM_KEY_LEFT || key == PM_KEY_RIGHT)
            f->header_focus = bound(f->header_focus + delta, 0, PM_SCREEN_COUNT);
        if (key == PM_KEY_DOWN || key == PM_KEY_BACK)
            f->header_focus = -1;
        if (key == PM_KEY_CONFIRM)
        {
            if (f->header_focus == PM_SCREEN_COUNT)
            {
                confirm(f, v, 2);
                return 0;
            }
            return switch_screen(f, v, (PmScreen)f->header_focus, a);
        }
        return 0;
    }
    if (f->remote_browser)
        return remote_update(f, v, key, a);
    if (f->pack_picker)
    {
        int content = f->screen == PM_MODS;
        n = count(content ? v->content_import_count : v->pack_count, PM_MAX_INSTANCES);
        f->selected_pack = bound(f->selected_pack, 0, n ? n - 1 : 0);
        if (key == PM_KEY_BACK || key == PM_KEY_SECONDARY)
        {
            f->pack_picker = 0;
            if (!content)
                f->add_source = -1;
            return 0;
        }
        if (key == PM_KEY_UP || key == PM_KEY_DOWN)
            f->selected_pack = bound(f->selected_pack + delta, 0, n ? n - 1 : 0);
        if (v->busy)
            return 0;
        if (key == PM_KEY_REFRESH)
            return content ? content_action(f, a, "scan-content-imports", i)
                           : action(a, "scan-packs", NULL);
        if (key == PM_KEY_CONFIRM)
        {
            if (!n)
                return unavailable(f, "Copy files to the imports folder shown here, then refresh.");
            copy(a->source, sizeof(a->source),
                 (content ? v->content_imports : v->packs)[f->selected_pack].source);
            f->pack_picker = 0;
            return content ? content_action(f, a, "content-import", i)
                           : action(a, "import-pack", NULL);
        }
        return 0;
    }
    if (key == PM_KEY_BACK)
    {
        if (f->screen == PM_VERSIONS && f->add_source >= 0)
        {
            f->add_source = -1;
            f->focus = 0;
            return 0;
        }
        return switch_screen(f, v, PM_HOME, a);
    }
    if (key == PM_KEY_REFRESH && !v->busy)
        return f->screen == PM_MODS
                   ? content_action(f, a, "content-list", i)
                   : action(a, f->screen == PM_SETTINGS ? "detect-java" : "catalog", NULL);
    f->notice[0] = 0;
    switch (f->screen)
    {
    case PM_HOME:
        if (key == PM_KEY_UP && (!n || f->selected_instance < 4) && f->focus == 0)
        {
            f->header_focus = PM_HOME;
            break;
        }
        if (key == PM_KEY_SECONDARY)
        {
            f->screen = PM_VERSIONS;
            f->add_source = -1;
            f->focus = 0;
            break;
        }
        if (key == PM_KEY_LEFT || key == PM_KEY_RIGHT)
            f->selected_instance = bound(f->selected_instance + delta, 0, n ? n - 1 : 0);
        if (key == PM_KEY_UP || key == PM_KEY_DOWN)
            f->selected_instance = bound(f->selected_instance + delta * 4, 0, n ? n - 1 : 0);
        if (key == PM_KEY_CONFIRM)
        {
            if (!i)
                return switch_screen(f, v, PM_VERSIONS, a);
            if (v->busy)
                return 0;
            return action(a, i->installed ? "prepare-launch" : "install", i);
        }
        break;
    case PM_LIBRARY:
        if (key == PM_KEY_LEFT)
            f->focus = 0;
        if (key == PM_KEY_RIGHT)
            f->focus = 1;
        if (key == PM_KEY_UP || key == PM_KEY_DOWN)
        {
            if (!f->focus)
            {
                if (key == PM_KEY_UP && !f->selected_instance)
                {
                    f->header_focus = PM_LIBRARY;
                    break;
                }
                f->selected_instance = bound(f->selected_instance + delta, 0, n ? n - 1 : 0);
            }
            else
                f->focus = bound(f->focus + delta, 1, 5);
        }
        if (key == PM_KEY_SECONDARY)
            return switch_screen(f, v, PM_VERSIONS, a);
        if (key == PM_KEY_CONFIRM)
        {
            if (!i)
                return switch_screen(f, v, PM_VERSIONS, a);
            if (v->busy)
                return 0;
            if (f->focus <= 1)
                return action(a, i->installed ? "prepare-launch" : "install", i);
            if (f->focus == 2)
                return switch_screen(f, v, PM_MODS, a);
            if (f->focus == 3)
            {
                f->rename_editor = 1;
                f->rename_key = f->rename_lower = 0;
                f->rename_replace = 1;
                copy(f->rename_id, sizeof(f->rename_id), i->id);
                copy(f->rename_text, sizeof(f->rename_text), i->name[0] ? i->name : i->id);
                break;
            }
            if (f->focus == 4)
                return action(a, "clone", i);
            confirm(f, v, 1);
        }
        break;
    case PM_VERSIONS:
        if (f->add_source < 0)
        {
            if (key == PM_KEY_UP && f->focus == 0)
            {
                f->header_focus = PM_VERSIONS;
                break;
            }
            if (key == PM_KEY_LEFT || key == PM_KEY_RIGHT || key == PM_KEY_UP || key == PM_KEY_DOWN)
                f->focus = bound(f->focus + delta, 0, 3);
            if (key == PM_KEY_CONFIRM && !v->busy)
                return add_source(f, v, f->focus, a);
            break;
        }
        if (key == PM_KEY_SECONDARY)
        {
            f->version_filter = (f->version_filter + 1) % 3;
            normalize(f, v);
            break;
        }
        if (key == PM_KEY_LEFT)
        {
            if (f->focus == 1)
                f->loader_index = (f->loader_index + 4) % 5;
            else
                f->focus = 0;
        }
        if (key == PM_KEY_RIGHT)
        {
            if (f->focus == 1)
                f->loader_index = (f->loader_index + 1) % 5;
            else
                f->focus = 1;
        }
        if (key == PM_KEY_UP || key == PM_KEY_DOWN)
        {
            if (!f->focus)
            {
                int j = next_version(f, v, f->selected_version + delta, delta);
                if (j >= 0)
                    f->selected_version = j;
            }
            else
                f->focus = bound(f->focus + delta, 1, 3);
        }
        if (key == PM_KEY_CONFIRM && !v->busy)
        {
            if (f->focus == 3 || next_version(f, v, 0, 1) < 0)
                return action(a, "catalog", NULL);
            if (f->focus == 1)
            {
                f->loader_index = (f->loader_index + 1) % 5;
                break;
            }
            if (f->loader_index == 4)
                return unavailable(f, "NeoForge packs are not supported in this build.");
            if (f->loader_index == 3 && strcmp(v->versions[f->selected_version].id, "1.12.2"))
                return unavailable(f, "This build supports legacy Forge for Minecraft 1.12.2.");
            copy(a->version, sizeof(a->version), v->versions[f->selected_version].id);
            copy(a->loader, sizeof(a->loader), loaders[f->loader_index]);
            snprintf(a->name, sizeof(a->name), "Minecraft %s - %s", a->version, a->loader);
            return action(a, "create-install", NULL);
        }
        break;
    case PM_MODS:
        if (!i)
        {
            if (key == PM_KEY_CONFIRM)
                return switch_screen(f, v, PM_VERSIONS, a);
            break;
        }
        if (key == PM_KEY_UP)
        {
            if (f->focus == 0)
                f->header_focus = PM_MODS;
            else if (f->focus == 2 && f->selected_mod > 0)
                f->selected_mod--;
            else
                f->focus = f->focus == 6   ? 1
                           : f->focus == 1 ? 0
                           : f->focus > 3  ? f->focus - 1
                           : f->focus == 3 ? 6
                                           : 6;
        }
        if (key == PM_KEY_DOWN)
        {
            if (f->focus == 2)
                f->selected_mod = bound(
                    f->selected_mod + 1, 0,
                    count(v->mod_count, PM_MAX_MODS) ? count(v->mod_count, PM_MAX_MODS) - 1 : 0);
            else
                f->focus = f->focus == 0   ? 1
                           : f->focus == 6 || f->focus == 3 ? 2
                           : f->focus == 1 ? 6
                                           : bound(f->focus + 1, 3, 5);
        }
        if (key == PM_KEY_LEFT || key == PM_KEY_RIGHT)
        {
            if (f->focus == 0)
            {
                f->selected_instance = (f->selected_instance + delta + n) % n;
                f->selected_mod = 0;
                return v->busy ? 0 : content_action(f, a, "content-list", selected_instance(f, v));
            }
            if (f->focus == 1)
            {
                f->content_kind = (f->content_kind + delta + 3) % 3;
                f->selected_mod = 0;
                return v->busy ? 0 : content_action(f, a, "content-list", i);
            }
            f->focus = key == PM_KEY_RIGHT ? (f->focus == 6 ? 3 : 4)
                       : f->focus == 3 ? 6 : 2;
        }
        if (key == PM_KEY_SECONDARY)
        {
            if (v->busy)
                return 0;
            f->focus = 3;
            f->remote_browser = 1;
            f->search_editor = 1;
            f->remote_focus = 0;
            return 0;
        }
        if (key == PM_KEY_CONFIRM && !v->busy)
        {
            if (f->focus == 0)
            {
                f->selected_instance = (f->selected_instance + 1) % n;
                f->selected_mod = 0;
                return content_action(f, a, "content-list", selected_instance(f, v));
            }
            if (f->focus == 1)
            {
                f->content_kind = (f->content_kind + 1) % 3;
                f->selected_mod = 0;
                return content_action(f, a, "content-list", i);
            }
            if (f->focus == 3 || f->focus == 6)
            {
                f->remote_browser = 1;
                if (f->focus == 6)
                {
                    f->search_editor = 1;
                    f->remote_focus = 0;
                    return 0;
                }
                return remote_search(f, v, a, 0);
            }
            if (f->focus == 4)
            {
                f->pack_picker = 1;
                f->selected_pack = 0;
                return content_action(f, a, "scan-content-imports", i);
            }
            if (!count(v->mod_count, PM_MAX_MODS))
                return unavailable(f, "Add content to this instance first.");
            if (strcmp(v->content_instance, i->id) ||
                strcmp(v->content_kind, kinds[f->content_kind]))
                return content_action(f, a, "content-list", i);
            if (f->focus == 5)
            {
                confirm(f, v, 3);
                break;
            }
            copy(a->mod, sizeof(a->mod), v->mods[f->selected_mod].name);
            copy(a->enabled, sizeof(a->enabled),
                 v->mods[f->selected_mod].enabled ? "false" : "true");
            return content_action(f, a, "content-toggle", i);
        }
        break;
    case PM_SETTINGS:
        if (key == PM_KEY_SECONDARY)
        {
            if (v->java_count)
                f->selected_java = (f->selected_java + 1) % count(v->java_count, PM_MAX_JAVA);
            break;
        }
        if (key == PM_KEY_UP)
        {
            if (f->focus == 0 || (f->focus >= 7 && f->focus <= 9))
                f->header_focus = PM_SETTINGS;
            else if (f->focus == 10 || f->focus == 11)
                f->focus = f->focus == 10 ? 0 : 8;
            else if (f->focus >= 1 && f->focus <= 4)
                f->focus = f->focus <= 2 ? 10 : 11;
            else
                f->focus = f->focus == 5 ? 1 : 3;
        }
        if (key == PM_KEY_DOWN)
        {
            if (f->focus == 10 || f->focus == 11)
                f->focus = f->focus == 10 ? 1 : 3;
            else if (f->focus == 0 || f->focus >= 7)
                f->focus = f->focus == 0 || f->focus == 7 ? 10 : 11;
            else if (f->focus >= 1 && f->focus <= 4)
                f->focus = f->focus <= 2 ? 5 : 6;
        }
        if (key == PM_KEY_LEFT || key == PM_KEY_RIGHT)
        {
            if (f->focus == 10 || f->focus == 11)
                f->focus = bound(f->focus + delta, 10, 11);
            else if (f->focus == 0 || f->focus >= 7)
            {
                int column = f->focus == 0 ? 0 : f->focus - 6;
                column = bound(column + delta, 0, 3);
                f->focus = column == 0 ? 0 : column + 6;
            }
            else if (f->focus <= 4)
                f->focus = bound(f->focus + delta, 1, 4);
            else
                f->focus = bound(f->focus + delta, 5, 6);
        }
        if (key == PM_KEY_CONFIRM && !v->busy)
        {
            if (f->focus == 11)
            {
                f->vrr_index = !f->vrr_index;
                copy(a->vrr_mode,sizeof(a->vrr_mode),f->vrr_index?"stable":"auto");
                return action(a,"settings",NULL);
            }
            if (f->focus == 0 || f->focus >= 7)
            {
                f->selector_popup = f->focus == 10 ? 5 : f->focus == 0 ? 1 : f->focus == 7 ? 2 : f->focus == 8 ? 3 : 4;
                f->selector_choice = f->focus == 0   ? (f->memory_mb - 512) / 256
                                     : f->focus == 7 ? f->resolution_index
                                     : f->focus == 8 ? f->graphics_index
                                     : f->focus == 10 ? f->theme_index : f->input_index;
                break;
            }
            if (f->focus <= 4)
            {
                a->java_major = java_majors[f->focus - 1];
                return action(a, "install-java", NULL);
            }
            if (f->focus == 5)
                return action(a, "detect-java", NULL);
            a->memory_mb = f->memory_mb;
            a->resolution_height = resolution_heights[f->resolution_index];
            copy(a->graphics, sizeof(a->graphics), graphics_values[f->graphics_index]);
            copy(a->controller_mode, sizeof(a->controller_mode), input_values[f->input_index]);
            copy(a->theme_color, sizeof(a->theme_color), theme_values[f->theme_index]);
            copy(a->vrr_mode, sizeof(a->vrr_mode), f->vrr_index ? "stable" : "auto");
            return action(a, "settings", NULL);
        }
        break;
    case PM_ACCOUNTS:
        if (key == PM_KEY_UP)
        {
            if (!f->focus)
                f->header_focus = PM_ACCOUNTS;
            else
                f->focus--;
        }
        if (key == PM_KEY_DOWN)
            f->focus = bound(f->focus + 1, 0, 2);
        if (key == PM_KEY_CONFIRM && !v->busy)
        {
            if (!f->focus)
            {
                copy(a->account_mode, sizeof(a->account_mode),
                     !strcmp(v->account_mode, "offline") ? "microsoft" : "offline");
                copy(a->username, sizeof(a->username), v->username[0] ? v->username : "Player");
                return action(a, "settings", NULL);
            }
            if (!strcmp(v->account_mode, "offline"))
                return unavailable(f, "Choose Microsoft mode to sign in.");
            return action(a, f->focus == 1 ? "auth-device" : "auth-poll", NULL);
        }
        break;
    default:
        break;
    }
    return 0;
}
static int inside(int x, int y, int left, int top, int w, int h)
{
    return x >= left && x < left + w && y >= top && y < top + h;
}
int pm_frontend_pointer(PmFrontend *f, const PmView *v, int x, int y, int button, int wheel,
                        PmAction *a)
{
    if (!f || !v || !a)
        return 0;
    memset(a, 0, sizeof(*a));
    normalize(f, v);
    f->pointer_x = bound(x, 0, 1919);
    f->pointer_y = bound(y, 0, 1079);
    f->pointer_visible = 1;
    x = f->pointer_x;
    y = f->pointer_y;
    if (button == 2)
        return pm_frontend_update(f, v, PM_KEY_BACK, a);
    if (f->rename_editor)
    {
        if (button == 1 && inside(x, y, 140, 295, 1640, 64)) f->rename_replace = 1;
        for (int j = 0; j < 45; j++)
            if (inside(x, y, 140 + (j % 9) * 184, 380 + (j / 9) * 82, 170, 66))
            {
                f->rename_key = j;
                if (button == 1) return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
            }
        return 0;
    }
    if (f->confirmation)
    {
        if (button == 1 && inside(x, y, 630, 625, 310, 66))
        {
            f->confirmation_choice = 0;
            return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
        }
        if (button == 1 && inside(x, y, 980, 625, 310, 66))
        {
            f->confirmation_choice = 1;
            return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
        }
        return 0;
    }
    if (f->selector_popup)
    {
        int rows = f->selector_popup == 5   ? 6
                   : f->selector_popup == 1 ? 7
                   : f->selector_popup == 2 ? 4
                   : f->selector_popup == 3 ? 2
                                            : 2,
            start = f->selector_popup == 1 ? list_start(f->selector_choice, 7) : 0;
        if (f->selector_popup == 1)
            rows = bound(31 - start, 0, rows);
        if (wheel)
            return pm_frontend_update(f, v, wheel > 0 ? PM_KEY_UP : PM_KEY_DOWN, a);
        for (int j = 0; j < rows; j++)
            if (button == 1 && inside(x, y, 665, 320 + j * 70, 590, 60))
            {
                f->selector_choice = start + j;
                return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
            }
        return 0;
    }
    if (button == 1 && inside(x, y, 1702, 52, 150, 54))
    {
        confirm(f, v, 2);
        return 0;
    }
    int tx = 470;
    for (int j = 0; j < PM_SCREEN_COUNT; j++)
    {
        int w = text_width(tabs[j], 24) + 30;
        if (button == 1 && inside(x, y, tx - 12, 52, w, 55))
            return switch_screen(f, v, (PmScreen)j, a);
        tx += w + 13;
    }
    if (f->remote_browser)
    {
        int content = f->screen == PM_MODS;
        int search_y = content ? 355 : 283, list_y = content ? 445 : 363, rows = content ? 4 : 5;
        if (content)
        {
            for (int j = 0; j < 3; j++)
                if (button == 1 && inside(x, y, 110 + j * 290, 292, 274, 50))
                {
                    f->content_kind = j;
                    f->selected_mod = 0;
                    f->remote_browser = 0;
                    f->search_editor = 0;
                    f->focus = 2;
                    return v->busy ? 0
                                   : content_action(f, a, "content-list", selected_instance(f, v));
                }
        }
        if (button == 1 && inside(x, y, 110, search_y, content ? 1120 : 1410, 64))
        {
            f->remote_focus = 0;
            if (f->search_editor)
                return 0;
            return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
        }
        if (button == 1 && inside(x, y, content ? 1290 : 1545, search_y, content ? 490 : 265, 64))
            return v->busy ? 0 : remote_search(f, v, a, 0);
        if (f->search_editor)
        {
            for (int j = 0; j < 40; j++)
                if (button == 1 && inside(x, y, 140 + (j % 10) * 164,
                                          (content ? 445 : 385) + (j / 10) * 92, 150, 76))
                {
                    f->search_key = j;
                    return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
                }
            return 0;
        }
        if (wheel)
            return pm_frontend_update(f, v, wheel > 0 ? PM_KEY_UP : PM_KEY_DOWN, a);
        int rel = f->remote_stage,
            n = count(rel ? v->remote_version_count : v->remote_count, rel ? 64 : 24),
            start = list_start(rel ? f->selected_release : f->selected_remote, rows);
        for (int j = start; j < n && j < start + rows; j++)
            if (button == 1 && inside(x, y, 110, list_y + (j - start) * 86, 1700, 76))
            {
                if (rel)
                    f->selected_release = j;
                else
                    f->selected_remote = j;
                f->remote_focus = 1;
                return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
            }
        if (button == 1 && inside(x, y, 110, 824, 480, 58))
            return pm_frontend_update(f, v, PM_KEY_BACK, a);
        if (button == 1 && inside(x, y, 615, 824, 480, 58))
            return pm_frontend_update(f, v, PM_KEY_LEFT, a);
        if (button == 1 && inside(x, y, 1120, 824, 690, 58))
            return pm_frontend_update(f, v, PM_KEY_RIGHT, a);
        return 0;
    }
    if (f->pack_picker)
    {
        int content = f->screen == PM_MODS,
            n = count(content ? v->content_import_count : v->pack_count, PM_MAX_INSTANCES),
            start = list_start(f->selected_pack, 6);
        if (wheel)
            return pm_frontend_update(f, v, wheel > 0 ? PM_KEY_UP : PM_KEY_DOWN, a);
        for (int j = start; j < n && j < start + 6; j++)
            if (button == 1 && inside(x, y, 110, 315 + (j - start) * 86, 1700, 76))
            {
                f->selected_pack = j;
                return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
            }
        return 0;
    }
    if (button == 1 && inside(x, y, 1080, 985, 300, 48))
        return pm_frontend_update(f, v, PM_KEY_REFRESH, a);
    if (wheel)
    {
        if (f->screen == PM_HOME || f->screen == PM_LIBRARY || f->screen == PM_VERSIONS)
            f->focus = 0;
        else if (f->screen == PM_MODS)
            f->focus = 2;
        else
            return 0;
        return pm_frontend_update(f, v, wheel > 0 ? PM_KEY_UP : PM_KEY_DOWN, a);
    }
    int n = count(v->instance_count, PM_MAX_INSTANCES), start, hit = -1;
    switch (f->screen)
    {
    case PM_HOME:
        if (button == 1 && inside(x, y, 1530, 190, 280, 64))
        {
            f->add_source = -1;
            return switch_screen(f, v, PM_VERSIONS, a);
        }
        start = list_start(f->selected_instance, 12);
        for (int j = start; j < n && j < start + 12; j++)
        {
            int k = j - start;
            if (button == 1 && inside(x, y, 110 + (k % 4) * 432, 290 + (k / 4) * 181, 408, 161))
            {
                if (f->selected_instance == j)
                    return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
                f->selected_instance = j;
                f->focus = 0;
                return 0;
            }
        }
        if (button == 1 && inside(x, y, 1520, 852, 290, 52))
        {
            f->selected_instance = bound(start + 12, 0, n ? n - 1 : 0);
            return 0;
        }
        if (button == 1 && inside(x, y, 1200, 852, 290, 52))
        {
            f->selected_instance = bound(start - 12, 0, n ? n - 1 : 0);
            return 0;
        }
        break;
    case PM_LIBRARY:
        start = list_start(f->selected_instance, 7);
        for (int j = start; j < n && j < start + 7; j++)
            if (button == 1 && inside(x, y, 110, 282 + (j - start) * 83, 870, 74))
            {
                f->selected_instance = j;
                f->focus = 0;
                return 0;
            }
        for (int j = 0; j < 5; j++)
            if (inside(x, y, 1050, 520 + j * 70, 730, 66))
                hit = j + 1;
        break;
    case PM_VERSIONS:
        if (f->add_source < 0)
        {
            for (int j = 0; j < 4; j++)
                if (button == 1 && inside(x, y, 110 + j * 432, 320, 408, 385))
                    return v->busy ? 0 : add_source(f, v, j, a);
            break;
        }
        start = f->selected_version;
        for (int j = 0; j < 6; j++)
        {
            int k = next_version(f, v, start - 1, -1);
            if (k < 0)
                break;
            start = k;
        }
        for (int j = start, row = 0; j < count(v->version_count, PM_MAX_VERSIONS) && row < 7; j++)
        {
            if (!visible_version(f, &v->versions[j]))
                continue;
            if (button == 1 && inside(x, y, 110, 285 + row * 79, 870, 70))
            {
                f->selected_version = j;
                f->focus = 0;
                return 0;
            }
            row++;
        }
        if (inside(x, y, 1050, 465, 730, 66))
            hit = 1;
        if (inside(x, y, 1050, 683, 730, 66))
            hit = 2;
        if (inside(x, y, 1050, 768, 730, 66))
            hit = 3;
        break;
    case PM_MODS:
        if (inside(x, y, 110, 355, 1120, 64))
            hit = 6;
        if (inside(x, y, 1290, 355, 490, 64))
            hit = 3;
        if (inside(x, y, 110, 190, 1050, 68))
            hit = 0;
        for (int j = 0; j < 3; j++)
            if (button == 1 && inside(x, y, 110 + j * 290, 292, 274, 50))
            {
                f->content_kind = j;
                f->selected_mod = 0;
                f->focus = 2;
                return v->busy ? 0 : content_action(f, a, "content-list", selected_instance(f, v));
            }
        start = list_start(f->selected_mod, 5);
        for (int j = start; j < count(v->mod_count, PM_MAX_MODS) && j < start + 5; j++)
            if (button == 1 && inside(x, y, 110, 445 + (j - start) * 81, 1120, 72))
            {
                f->selected_mod = j;
                f->focus = 2;
                return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
            }
        for (int j = 0; j < 2; j++)
            if (inside(x, y, 1290, 459 + j * 94, 490, 66))
                hit = j + 4;
        break;
    case PM_SETTINGS:
        if (inside(x, y, 110, 430, 840, 110))
            hit = 10;
        if (inside(x, y, 974, 430, 840, 110))
            hit = 11;
        if (inside(x, y, 110, 280, 408, 134))
            hit = 0;
        if (inside(x, y, 542, 280, 408, 134))
            hit = 7;
        if (inside(x, y, 974, 280, 408, 134))
            hit = 8;
        if (inside(x, y, 1406, 280, 408, 134))
            hit = 9;
        for (int j = 0; j < 4; j++)
            if (inside(x, y, 110 + j * 432, 600, 408, 185))
                hit = j + 1;
        if (inside(x, y, 110, 861, 840, 66))
            hit = 5;
        if (inside(x, y, 974, 861, 840, 66))
            hit = 6;
        break;
    case PM_ACCOUNTS:
        if (inside(x, y, 110, 286, 700, 72))
            hit = 0;
        if (inside(x, y, 110, 726, 700, 66))
            hit = 1;
        if (inside(x, y, 110, 815, 700, 66))
            hit = 2;
        break;
    default:
        break;
    }
    if (hit >= 0)
    {
        f->focus = hit;
        f->header_focus = -1;
        if (button == 1)
            return pm_frontend_update(f, v, PM_KEY_CONFIRM, a);
    }
    return 0;
}
typedef struct Canvas
{
    const PwPresentTarget *t;
    unsigned focus_alpha;
    unsigned opacity;
    int offset_x;
    uint32_t accent, focus_rgb, base, panel, row, edge, muted, faint;
} Canvas;
static uint32_t mix(uint32_t a, uint32_t b, unsigned alpha)
{
    unsigned r = ((a >> 16 & 255) * (255 - alpha) + (b >> 16 & 255) * alpha) / 255;
    unsigned g = ((a >> 8 & 255) * (255 - alpha) + (b >> 8 & 255) * alpha) / 255;
    unsigned bl = ((a & 255) * (255 - alpha) + (b & 255) * alpha) / 255;
    return (r << 16) | (g << 8) | bl;
}
static void px(Canvas *c, int x, int y, uint32_t rgb, unsigned alpha)
{
    uint8_t *p;
    x += c->offset_x;
    alpha = alpha * c->opacity / 255;
    if (x < 0 || y < 0 || x >= (int)c->t->width || y >= (int)c->t->height)
        return;
    p = c->t->pixels + (size_t)y * c->t->stride + (size_t)x * 4;
    if (alpha < 255)
        rgb = mix(((uint32_t)p[2] << 16) | ((uint32_t)p[1] << 8) | p[0], rgb, alpha);
    p[0] = (uint8_t)rgb;
    p[1] = (uint8_t)(rgb >> 8);
    p[2] = (uint8_t)(rgb >> 16);
    p[3] = 255;
}
static int sx(Canvas *c, int x)
{
    return (int)((int64_t)x * c->t->width / 1920);
}
static int sy(Canvas *c, int y)
{
    return (int)((int64_t)y * c->t->height / 1080);
}
static void box(Canvas *c, int x, int y, int w, int h, uint32_t rgb)
{
    int left = bound(sx(c, x) + c->offset_x, 0, c->t->width), top = bound(sy(c, y), 0, c->t->height);
    int right = bound(sx(c, x + w) + c->offset_x, 0, c->t->width), bottom = bound(sy(c, y + h), 0, c->t->height),
        xx, yy;
    if (c->opacity < 255) rgb = mix(c->base, rgb, c->opacity);
    uint32_t pixel = rgb | 0xff000000u;
    for (yy = top; yy < bottom; yy++)
    {
        uint8_t *p = c->t->pixels + (size_t)yy * c->t->stride + (size_t)left * 4;
        for (xx = left; xx < right; xx++, p += 4)
            memcpy(p, &pixel, 4);
    }
}
static void roundbox(Canvas *c, int x, int y, int w, int h, int rad, uint32_t rgb)
{
    int xx, yy, left = sx(c, x) + c->offset_x, top = sy(c, y), right = sx(c, x + w) + c->offset_x,
                        bottom = sy(c, y + h);
    int rx = sx(c, rad), ry = sy(c, rad);
    if (rx < 1 || ry < 1)
    {
        box(c, x, y, w, h, rgb);
        return;
    }
    if (c->opacity < 255) rgb = mix(c->base, rgb, c->opacity);
    uint32_t pixel = rgb | 0xff000000u;
    for (yy = bound(top, 0, c->t->height); yy < bound(bottom, 0, c->t->height); yy++)
    {
        int dy = yy < top + ry ? top + ry - yy : yy >= bottom - ry ? yy - (bottom - ry - 1) : 0;
        int inset = 0;
        while (dy && inset < rx &&
               (int64_t)(rx-inset)*(rx-inset)*ry*ry + (int64_t)dy*dy*rx*rx > (int64_t)rx*rx*ry*ry) inset++;
        int begin = bound(left + inset, 0, c->t->width), end = bound(right - inset, 0, c->t->width);
        uint8_t *p = c->t->pixels + (size_t)yy*c->t->stride + (size_t)begin*4;
        for (xx=begin;xx<end;xx++,p+=4) memcpy(p,&pixel,4);
    }
}
static void panel(Canvas *c, int x, int y, int w, int h, int focused)
{
    roundbox(c, x, y + 5, w, h, 4, c->base);
    roundbox(c, x, y, w, h, 4, focused ? mix(c->edge, c->accent, c->focus_alpha) : c->edge);
    roundbox(c, x + 2, y + 2, w - 4, h - 4, 2, focused ? c->focus_rgb : c->panel);
    /* A recessed inventory edge, with a clear controller focus outline. */
    box(c, x + 7, y + 2, w - 14, 1, focused ? c->accent : mix(c->edge,c->accent,35));
    if (focused)
        box(c, x + 2, y + 9, 4, h - 18, c->accent);
}
static int text_width(const char *s, int size)
{
    int width = 0;
    while (*s)
    {
        unsigned ch = (unsigned char)*s++;
        if (ch < 32 || ch > 126)
            ch = '?';
        width += pm_glyphs[ch - 32].advance * size / 48;
    }
    return width;
}
static void text(Canvas *c, const char *s, int x, int y, int size, uint32_t rgb, int max_width)
{
    int pen = x;
    if (!s)
        return;
    while (*s)
    {
        unsigned ch = (unsigned char)*s++;
        const PmGlyph *g;
        int l, t, w, h, xx, yy, gx, gy;
        if (ch < 32 || ch > 126)
            ch = '?';
        g = &pm_glyphs[ch - 32];
        if (max_width > 0 && pen + g->advance * size / 48 > x + max_width)
            break;
        l = sx(c, pen + g->left * size / 48);
        t = sy(c, y + (46 + g->top) * size / 48);
        w = sx(c, g->width * size / 48);
        h = sy(c, g->height * size / 48);
        if (w && h)
            for (yy = 0; yy < h; yy++)
                for (xx = 0; xx < w; xx++)
                {
                    gx = xx * g->width / w;
                    gy = yy * g->height / h;
                    px(c, l + xx, t + yy, rgb, pm_font_pixels[g->offset + gy * g->width + gx]);
                }
        pen += g->advance * size / 48;
    }
}
static void small(Canvas *c, const char *s, int x, int y, uint32_t color, int maxw)
{
    text(c, s, x, y, 24, color, maxw);
}
static int instance_name(Canvas *c, const char *name, int x, int y, int width)
{
    if (text_width(name, 24) <= width)
    {
        text(c, name, x, y, 24, TITLE, width);
        return 0;
    }
    char first[PM_TEXT];
    size_t cut = 0, space = 0;
    for (size_t j = 0; name[j] && j < sizeof(first) - 1; j++)
    {
        first[j] = name[j];
        first[j + 1] = 0;
        if (text_width(first, 24) > width)
            break;
        cut = j + 1;
        if (name[j] == ' ')
            space = j;
    }
    if (space)
        cut = space;
    first[cut] = 0;
    text(c, first, x, y, 24, TITLE, width);
    const char *rest = name + cut;
    while (*rest == ' ')
        rest++;
    text(c, rest, x, y + 27, 24, TITLE, width);
    return 1;
}
static float segment_distance_squared(float x, float y, float ax, float ay, float bx, float by)
{
    float dx = bx - ax, dy = by - ay, t = ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy);
    if (t < 0)
        t = 0;
    if (t > 1)
        t = 1;
    dx = x - ax - t * dx;
    dy = y - ay - t * dy;
    return dx * dx + dy * dy;
}
/* Shared size, stroke, color and antialiasing for every controller symbol. */
static void controller_symbol(Canvas *c, char shape, int x, int y)
{
    int w = sx(c, 26), h = sy(c, 26), left = sx(c, x), top = sy(c, y);
    if (w <= 0 || h <= 0)
        return;
    for (int yy = 0; yy < h; yy++)
        for (int xx = 0; xx < w; xx++)
        {
            unsigned hits = 0;
            for (int j = 0; j < 4; j++)
                for (int i = 0; i < 4; i++)
                {
                    float px0 = (xx + (i + .5f) / 4) * 26 / w, py0 = (yy + (j + .5f) / 4) * 26 / h,
                          d = 1000;
#define EDGE_DISTANCE(ax, ay, bx, by)                                                              \
    do                                                                                             \
    {                                                                                              \
        float v = segment_distance_squared(px0, py0, ax, ay, bx, by);                              \
        if (v < d)                                                                                 \
            d = v;                                                                                 \
    } while (0)
                    if (shape == 'X')
                    {
                        EDGE_DISTANCE(5, 5, 21, 21);
                        EDGE_DISTANCE(5, 21, 21, 5);
                    }
                    else if (shape == 'O')
                    {
                        float dx = px0 - 13, dy = py0 - 13, r = dx * dx + dy * dy;
                        d = (r >= 81 && r <= 121) ? 0 : 1000;
                    }
                    else if (shape == 'T')
                    {
                        EDGE_DISTANCE(13, 2, 1, 24);
                        EDGE_DISTANCE(1, 24, 25, 24);
                        EDGE_DISTANCE(25, 24, 13, 2);
                    }
                    else
                    {
                        EDGE_DISTANCE(3, 3, 23, 3);
                        EDGE_DISTANCE(23, 3, 23, 23);
                        EDGE_DISTANCE(23, 23, 3, 23);
                        EDGE_DISTANCE(3, 23, 3, 3);
                    }
#undef EDGE_DISTANCE
                    if (d <= 1)
                        hits++;
                }
            if (hits)
                px(c, left + xx, top + yy, TEXT, hits * 255 / 16);
        }
}
static void button(Canvas *c, const char *s, int x, int y, int w, int focused, int primary)
{
    roundbox(c, x, y + 4, w, 66, 4, c->base);
    roundbox(c, x, y, w, 66, 4,
             focused   ? mix(c->edge, c->accent, c->focus_alpha)
             : primary ? c->accent
                       : c->edge);
    if (!primary)
        roundbox(c, x + 2, y + 2, w - 4, 62, 2, focused ? c->focus_rgb : c->row);
    else
        box(c, x + 5, y + 3, w - 10, 2, mix(c->accent, TITLE, 55));
    text(c, s, x + (w - text_width(s, 24)) / 2, y + 17, 24,
         primary   ? 0x111b14
         : focused ? TITLE
                   : TEXT,
         w - 20);
}
static void chip(Canvas *c, const char *s, int x, int y, int accent)
{
    int w = text_width(s, 20) + 30;
    roundbox(c, x, y, w, 38, 10, accent ? c->focus_rgb : c->row);
    text(c, s, x + 15, y + 9, 20, accent ? c->accent : c->muted, w - 22);
}

static void logo(Canvas *c, int x, int y, int size)
{
    int xx, yy, left = sx(c, x), top = sy(c, y), right = sx(c, x + size), bottom = sy(c, y + size);
    if (right <= left || bottom <= top)
        return;
    for (yy = bound(top, 0, c->t->height); yy < bound(bottom, 0, c->t->height); yy++)
    {
        unsigned row = (unsigned)((int64_t)(yy - top) * PM_LOGO_H / (bottom - top));
        for (xx = bound(left, 0, c->t->width); xx < bound(right, 0, c->t->width); xx++)
        {
            unsigned col = (unsigned)((int64_t)(xx - left) * PM_LOGO_W / (right - left));
            uint16_t v = pm_logo_pixels[row * PM_LOGO_W + col];
            unsigned r = v >> 11, g = (v >> 5) & 63, b = v & 31;
            px(c, xx, yy, ((r * 255 / 31) << 16) | ((g * 255 / 63) << 8) | (b * 255 / 31), 255);
        }
    }
}

static void pixel_icon(Canvas *c, const char *loader, int x, int y, int size)
{
    int cell = size / 16;
    uint32_t stone = 0x8c918d;
    if (!strcmp(loader, "archive"))
    {
        box(c, x + cell, y + 3 * cell, 14 * cell, 11 * cell, 0x59452d);
        box(c, x + 2 * cell, y + 4 * cell, 12 * cell, 9 * cell, 0xa87b40);
        box(c, x + 2 * cell, y + 7 * cell, 12 * cell, cell, 0x5c462d);
        for (int j = 3; j < 13; j += 3)
            box(c, x + j * cell, y + 9 * cell, cell, 3 * cell, 0x8b6535);
        box(c, x + 7 * cell, y + 6 * cell, 2 * cell, 4 * cell, 0xebd49d);
        return;
    }
    if (!strcmp(loader, "fabric") || !strcmp(loader, "quilt"))
    {
        for (int row = 1; row < 15; row++)
            for (int col = 1; col < 15; col++)
                if (col >= 14 - row / 2 && col <= 17 - row / 2)
                {
                    box(c, x + col * cell, y + row * cell, cell, cell,
                        (col + row) % 3 ? 0xe5e9d9 : 0xbbccac);
                }
        for (int j = 3; j < 15; j++)
            box(c, x + (15 - j / 2) * cell, y + j * cell, cell, cell, 0x8caa7a);
        return;
    }
    if (!strcmp(loader, "forge"))
    {
        box(c, x + cell, y + cell, 14 * cell, 14 * cell, 0x525b56);
        for (int row = 2; row < 14; row++)
            for (int col = 2; col < 14; col++)
                box(c, x + col * cell, y + row * cell, cell, cell,
                    (row * 3 + col * 7) % 5 ? stone : 0x68746b);
        box(c, x + 4 * cell, y + 4 * cell, 8 * cell, 4 * cell, 0x26332b);
        box(c, x + 4 * cell, y + 10 * cell, 8 * cell, 3 * cell, 0x252d27);
        box(c, x + 5 * cell, y + 11 * cell, 6 * cell, cell, 0xefad60);
        return;
    }
    if (!strcmp(loader, "neoforge"))
    {
        for (int row = 3; row < 13; row++)
            for (int col = 2; col < 14; col++)
                box(c, x + col * cell, y + row * cell, cell, cell, row > 9 ? 0xebd6b2 : 0xc77c3c);
        box(c, x + 2 * cell, y + cell, 3 * cell, 4 * cell, 0xda8840);
        box(c, x + 11 * cell, y + cell, 3 * cell, 4 * cell, 0xda8840);
        box(c, x + 4 * cell, y + 7 * cell, 2 * cell, 2 * cell, 0x252a20);
        box(c, x + 10 * cell, y + 7 * cell, 2 * cell, 2 * cell, 0x252a20);
        box(c, x + 7 * cell, y + 11 * cell, 2 * cell, cell, 0x252a20);
        return;
    }
    /* Three pixelated faces, with the same silhouette as a Minecraft block. */
    for (int row = 1; row < 16; row++)
        for (int col = 1; col < 16; col++)
        {
            int left = col <= 8 && row >= 5 + (col - 1) * 4 / 7 && row <= 11 + (col - 1) * 4 / 7;
            int right = col >= 8 && row >= 9 - (col - 8) * 4 / 7 && row <= 15 - (col - 8) * 4 / 7;
            int dx = col > 8 ? col - 8 : 8 - col, dy = row > 5 ? row - 5 : 5 - row;
            int top = dx * 4 + dy * 7 <= 28;
            uint32_t rgb;
            if (top)
                rgb = (row * 3 + col * 7) % 4 ? 0x90bd59 : 0xb0d47a;
            else if (left)
                rgb = (row * 13 + col * 7) % 5 ? 0x806142 : 0xa17b51;
            else if (right)
                rgb = (row * 7 + col * 11) % 5 ? 0x5c4934 : 0x786044;
            else
                continue;
            if (!top && left && row < 7 + (col - 1) * 4 / 7)
                rgb = 0x6a9146;
            if (!top && right && row < 11 - (col - 8) * 4 / 7)
                rgb = 0x52753b;
            box(c, x + col * cell, y + row * cell, cell, cell, rgb);
        }
}
static void icon(Canvas *c, const char *path, const char *loader, int x, int y, int size)
{
    unsigned width = 0, height = 0;
    const uint8_t *pixels =
        path && path[0] && icon_loader ? icon_loader(path, &width, &height) : NULL;
    if (!pixels || !width || !height || width > 512 || height > 512)
    {
        pixel_icon(c, loader ? loader : "vanilla", x, y, size);
        return;
    }
    int left = sx(c, x), top = sy(c, y), right = sx(c, x + size), bottom = sy(c, y + size);
    for (int yy = top; yy < bottom; yy++)
        for (int xx = left; xx < right; xx++)
        {
            unsigned col = (unsigned)((int64_t)(xx - left) * width / (right - left)),
                     row = (unsigned)((int64_t)(yy - top) * height / (bottom - top));
            const uint8_t *p = pixels + ((size_t)row * width + col) * 4;
            px(c, xx, yy, ((uint32_t)p[0] << 16) | ((uint32_t)p[1] << 8) | p[2], p[3]);
        }
}
static void heading(Canvas *c, const char *title, const char *subtitle)
{
    text(c, title, 110, 181, 39, TITLE, 1400);
    small(c, subtitle, 112, 237, c->faint, 1630);
}
static void empty(Canvas *c, const char *title, const char *body)
{
    text(c, title, 152, 405, 34, TITLE, 1520);
    small(c, body, 154, 465, c->muted, 1500);
}
static void header(Canvas *c, const PmFrontend *f, const PmView *v)
{
    logo(c, 64, 43, 61);
    text(c, "PROSPERO MC", 141, 45, 29, TITLE, 315);
    small(c, "MINECRAFT JAVA / PS5", 142, 86, c->faint, 315);
    int x = 470;
    for (int j = 0; j < PM_SCREEN_COUNT; j++)
    {
        int w = text_width(tabs[j], 24) + 30;
        if (f->screen == (PmScreen)j)
            roundbox(c, x - 12, 52, w, 50, 4, c->row);
        if (f->header_focus == j)
            panel(c, x - 12, 52, w, 50, 1);
        text(c, tabs[j], x + 3, 66, 24, f->screen == (PmScreen)j ? TITLE : c->muted, w - 8);
        if (f->screen == (PmScreen)j)
        {
            box(c, f->underline_x, 110, w - 26, 3, c->accent);
            box(c, f->underline_x, 113, 12, 3, 0x527444);
        }
        x += w + 13;
    }
    roundbox(c, 1702, 52, 150, 54, 12, f->header_focus == PM_SCREEN_COUNT ? c->focus_rgb : c->row);
    small(c, "Close  X", 1730, 66, TEXT, 116);
    box(c, 65, 137, 1790, 1, c->edge);
    roundbox(c, 1813, 166, 10, 10, 5, v->busy ? WARN : strstr(v->status, "error") ? WARN : c->accent);
}
static void footer(Canvas *c, const PmFrontend *f, const PmView *v)
{
    box(c, 65, 967, 1790, 1, c->edge);
    small(c, "L1 / R1  Navigate", 80, 993, c->muted, 300);
    controller_symbol(c, 'X', 438, 992);
    small(c,
          f->confirmation        ? "Choose"
          : f->remote_browser    ? "Select / install"
          : f->screen == PM_HOME ? "Play selected"
                                 : "Select",
          478, 992, TEXT, 330);
    controller_symbol(c, 'O', 813, 992);
    small(c, "Back", 853, 992, TEXT, 170);
    controller_symbol(c, 'T', 1080, 992);
    small(c, f->screen == PM_SETTINGS ? "Detect Java" : "Refresh", 1120, 992, TEXT, 250);
    if (f->remote_browser || f->screen == PM_HOME || f->screen == PM_LIBRARY ||
        f->screen == PM_MODS || f->screen == PM_SETTINGS ||
        (f->screen == PM_VERSIONS && f->add_source >= 0))
    {
        controller_symbol(c, 'S', 1480, 992);
        small(c,
              f->remote_browser          ? "Search"
              : f->screen == PM_SETTINGS ? "Runtime info"
              : f->screen == PM_VERSIONS ? "Filter"
              : f->screen == PM_MODS     ? "Add content"
                                         : "Add instance",
              1520, 992, TEXT, 300);
    }
    else
        small(c, "D-PAD / ARROWS", 1480, 992, c->faint, 330);
    const char *detail = f->notice[0] ? f->notice : v->detail;
    if (detail[0])
        text(c, detail, 110, 919, 21, f->notice[0] ? WARN : v->busy ? c->accent : c->muted, 1700);
    if (v->busy)
    {
        box(c, 110, 955, 1700, 3, c->edge);
        if (v->progress_total > 0)
            box(c, 110, 955,
                (int)((int64_t)1700 * bound(v->progress_done, 0, v->progress_total) /
                      v->progress_total),
                3, c->accent);
        else
            box(c, 110 + (int)(f->animation_ms % 1600) * 1400 / 1600, 955, 300, 3, c->accent);
    }
}
static void home(Canvas *c, const PmFrontend *f, const PmView *v)
{
    char b[256];
    int n = count(v->instance_count, PM_MAX_INSTANCES),
        start = list_start(f->selected_instance, 12);
    heading(c, "Your worlds, your way",
            "Minecraft and modpacks. Choose an instance to continue your adventure.");
    button(c, "+ ADD INSTANCE", 1530, 185, 280, 0, 1);
    if (!n)
    {
        panel(c, 110, 300, 1700, 480, 0);
        empty(c, "Make room for your next world",
              "Add a Minecraft version, discover a Modrinth pack, or import your own.");
        return;
    }
    for (int j = start; j < n && j < start + 12; j++)
    {
        int k = j - start, x = 110 + (k % 4) * 432, y = 290 + (k / 4) * 181;
        const PmInstance *i = &v->instances[j];
        panel(c, x, y, 408, 161, j == f->selected_instance && f->header_focus < 0);
        icon(c, i->icon, i->loader, x + 23, y + 26, 80);
        int two_lines = instance_name(c, i->name[0] ? i->name : i->id, x + 118, y + 24, 265);
        snprintf(b, sizeof(b), "%s / %s", i->version, i->loader);
        text(c, b, x + 119, y + (two_lines ? 86 : 67), 19, c->muted, 265);
        chip(c, i->installed ? "READY TO PLAY" : "DOWNLOAD", x + 119, y + (two_lines ? 118 : 105),
             i->installed);
    }
    snprintf(b, sizeof(b), "%d instances  /  page %d of %d", n, start / 12 + 1, (n + 11) / 12);
    small(c, b, 110, 860, c->faint, 900);
    if (start)
        button(c, "< PREVIOUS", 1200, 847, 290, 0, 0);
    if (start + 12 < n)
        button(c, "NEXT >", 1520, 847, 290, 0, 0);
}
static void library(Canvas *c, const PmFrontend *f, const PmView *v)
{
    char b[256];
    int n = count(v->instance_count, PM_MAX_INSTANCES), start = list_start(f->selected_instance, 7);
    const PmInstance *i = selected_instance(f, v);
    heading(c, "Library", "Your instances, their own worlds and their own content.");
    for (int j = start; j < n && j < start + 7; j++)
    {
        int y = 282 + (j - start) * 83;
        const PmInstance *item = &v->instances[j];
        panel(c, 110, y, 870, 74, j == f->selected_instance && !f->focus);
        icon(c, item->icon, item->loader, 126, y + 8, 56);
        text(c, item->name[0] ? item->name : item->id, 204, y + 7, 25, TITLE, 720);
        snprintf(b, sizeof(b), "%s  /  %s", item->version, item->loader);
        text(c, b, 205, y + 43, 18, c->faint, 710);
    }
    panel(c, 1018, 282, 790, 586, 0);
    if (!i)
    {
        empty(c, "No instances yet", "Choose Add Instance to get started.");
        return;
    }
    icon(c, i->icon, i->loader, 1050, 314, 100);
    text(c, i->name[0] ? i->name : i->id, 1178, 320, 31, TITLE, 580);
    snprintf(b, sizeof(b), "Minecraft %s", i->version);
    small(c, b, 1180, 367, c->muted, 570);
    chip(c, i->loader, 1050, 446, 1);
    chip(c, i->installed ? "Installed" : "Not installed", 1230, 446, 0);
    button(c, i->installed ? "PLAY INSTANCE" : "DOWNLOAD MINECRAFT", 1050, 520, 730, f->focus == 1,
           1);
    button(c, "MANAGE CONTENT", 1050, 590, 730, f->focus == 2, 0);
    button(c, "RENAME INSTANCE", 1050, 660, 730, f->focus == 3, 0);
    button(c, "DUPLICATE INSTANCE", 1050, 730, 730, f->focus == 4, 0);
    button(c, "DELETE INSTANCE", 1050, 800, 730, f->focus == 5, 0);
}
static void versions(Canvas *c, const PmFrontend *f, const PmView *v)
{
    char b[256];
    if (f->add_source < 0)
    {
        heading(c, "Add an instance", "Choose how your next Minecraft adventure starts.");
        const char *names[] = {"Minecraft", "Modrinth", "CurseForge", "Your own pack"};
        const char *line1[] = {"Choose any release", "Discover modpacks", "Browse modpacks",
                               "Import .mrpack or .zip"};
        const char *line2[] = {"Vanilla, Fabric or Quilt", "Install a complete instance",
                               "Install a compatible release", "PolyMC and MultiMC packs"};
        const char *types[] = {"vanilla", "fabric", "forge", "archive"};
        for (int j = 0; j < 4; j++)
        {
            int x = 110 + j * 432;
            panel(c, x, 320, 408, 385, f->focus == j);
            icon(c, NULL, types[j], x + 143, 354, 112);
            text(c, names[j], x + 28, 511, 31, TITLE, 350);
            small(c, line1[j], x + 29, 572, c->muted, 350);
            text(c, line2[j], x + 29, 615, 20, c->faint, 350);
            text(c, "SELECT >", x + 29, 666, 20, c->accent, 350);
        }
        return;
    }
    heading(c, "Choose Minecraft",
            "Choose a version, then select its loader and download. Circle returns to sources.");
    int n = count(v->version_count, PM_MAX_VERSIONS), start = f->selected_version;
    for (int j = 0; j < 6; j++)
    {
        int prev = next_version(f, v, start - 1, -1);
        if (prev < 0)
            break;
        start = prev;
    }
    for (int j = start, row = 0; j < n && row < 7; j++)
    {
        if (!visible_version(f, &v->versions[j]))
            continue;
        int y = 285 + row * 79;
        panel(c, 110, y, 870, 70, j == f->selected_version && !f->focus);
        icon(c, NULL, loaders[f->loader_index], 127, y + 7, 54);
        text(c, v->versions[j].id, 207, y + 14, 29, TITLE, 525);
        text(c, v->versions[j].type, 748, y + 23, 20, c->faint, 180);
        row++;
    }
    panel(c, 1018, 285, 790, 584, 0);
    if (!n)
    {
        text(c, "Load the version catalog", 1050, 325, 32, TITLE, 710);
    }
    else
    {
        text(c, v->versions[f->selected_version].id, 1050, 328, 45, TITLE, 710);
        snprintf(b, sizeof(b), "%s  /  %s", v->versions[f->selected_version].type,
                 filters[f->version_filter]);
        small(c, b, 1052, 397, c->muted, 710);
    }
    small(c, "MOD LOADER", 1050, 442, c->faint, 710);
    snprintf(b, sizeof(b), "<  %s  >", loaders[f->loader_index]);
    button(c, b, 1050, 478, 730, f->focus == 1, 0);
    small(c,
          f->loader_index == 3 ? "Legacy Forge is available for Minecraft 1.12.2."
                               : "Java and loader files are downloaded automatically.",
          1050, 585, c->muted, 710);
    button(c, "DOWNLOAD INSTANCE", 1050, 683, 730, f->focus == 2, 1);
    button(c, "REFRESH CATALOG", 1050, 768, 730, f->focus == 3, 0);
}
static int content_matches(const PmFrontend *f, const PmView *v)
{
    const PmInstance *i = selected_instance(f, v);
    return i && !strcmp(i->id, v->content_instance) &&
           !strcmp(kinds[f->content_kind], v->content_kind);
}
static void search_bar(Canvas *c, const PmFrontend *f, const char *provider, const char *category,
                       int y, int content)
{
    char label[256];
    int editing = f->search_editor || (f->remote_browser ? f->remote_focus == 0 : f->focus == 6);
    panel(c, 110, y, content ? 1120 : 1410, 64, editing);
    if (f->query[0] || f->search_editor)
        snprintf(label, sizeof(label), "%s%s", f->query, f->search_editor ? "_" : "");
    else
        snprintf(label, sizeof(label), "Search %s %s...", provider, category);
    text(c, label, 139, y + 16, 25, f->query[0] || f->search_editor ? TITLE : c->faint,
         content ? 1060 : 1350);
    button(c, "SEARCH", content ? 1290 : 1545, y, content ? 490 : 265,
           !f->remote_browser && f->focus == 3, 1);
}
static void content(Canvas *c, const PmFrontend *f, const PmView *v)
{
    const PmInstance *i = selected_instance(f, v);
    char b[256];
    if (!i)
    {
        heading(c, "Content", "Manage mods, resource packs and shader packs per instance.");
        empty(c, "Choose an instance first", "Add or select an instance from your library.");
        return;
    }
    snprintf(b, sizeof(b), "<  %s  >", i->name[0] ? i->name : i->id);
    button(c, b, 110, 187, 1050, f->focus == 0, 0);
    snprintf(b, sizeof(b), "Minecraft %s / %s", i->version, i->loader);
    small(c, b, 1190, 203, c->faint, 600);
    for (int j = 0; j < 3; j++)
    {
        int x = 110 + j * 290;
        roundbox(c, x, 292, 274, 50, 10, f->content_kind == j ? c->focus_rgb : c->row);
        text(c, kind_labels[j], x + 20, 307, 22, f->content_kind == j ? c->accent : c->muted, 235);
        if (f->focus == 1 && f->content_kind == j)
            box(c, x + 18, 338, 235, 2, c->accent);
    }
    search_bar(c, f, "Modrinth", kind_labels[f->content_kind], 355, 1);
    int n = content_matches(f, v) ? count(v->mod_count, PM_MAX_MODS) : 0,
        start = list_start(f->selected_mod, 5);
    if (!n)
    {
        panel(c, 110, 445, 1120, 397, 0);
        text(c, content_matches(f, v) ? "Nothing added yet" : "Loading this instance...", 150, 480,
             31, TITLE, 1000);
        small(c, "Search above or import local files for this instance.", 150, 535, c->muted, 1000);
    }
    for (int j = start; j < n && j < start + 5; j++)
    {
        int y = 445 + (j - start) * 81;
        panel(c, 110, y, 1120, 72, j == f->selected_mod && f->focus == 2);
        roundbox(c, 132, y + 24, 14, 14, 7, v->mods[j].enabled ? c->accent : c->faint);
        text(c, v->mods[j].name, 174, y + 22, 24, TITLE, 825);
        text(c, v->mods[j].enabled ? "Enabled" : "Disabled", 1070, y + 24, 19,
             v->mods[j].enabled ? c->accent : c->faint, 135);
    }
    button(c, "IMPORT LOCAL FILE", 1290, 459, 490, f->focus == 4, 0);
    button(c, "DELETE SELECTED", 1290, 553, 490, f->focus == 5, 0);
    if (n)
    {
        small(c, "SELECTED FILE", 1290, 650, c->faint, 490);
        text(c, v->mods[f->selected_mod].name, 1290, 689, 21, TITLE, 490);
    }
    text(c, "Select an item to enable or disable it.", 1290, 748, 20, c->muted, 490);
    text(c, "Activate resource/shader packs in Minecraft.", 1290, 785, 19, c->faint, 490);
}
static const PmJavaRuntime *runtime_for_major(const PmView *v, int major)
{
    for (int j = 0; j < count(v->java_count, PM_MAX_JAVA); j++)
        if (v->java_runtimes[j].major == major && v->java_runtimes[j].valid)
            return &v->java_runtimes[j];
    return NULL;
}
static void settings(Canvas *c, const PmFrontend *f, const PmView *v)
{
    char b[256];
    heading(c, "Make it yours",
            "Choose display and memory settings, then save. Java is selected for each game.");
    panel(c, 110, 280, 408, 134, !f->focus);
    text(c, "MINECRAFT MEMORY", 140, 302, 21, c->faint, 348);
    snprintf(b, sizeof(b), "%d MB   v", f->memory_mb);
    text(c, b, 140, 350, 29, TITLE, 348);
    panel(c, 542, 280, 408, 134, f->focus == 7);
    text(c, "GAME RESOLUTION", 572, 302, 21, c->faint, 348);
    snprintf(b, sizeof(b), "%s   v", resolution_labels[f->resolution_index]);
    text(c, b, 572, 350, 28, TITLE, 348);
    panel(c, 974, 280, 408, 134, f->focus == 8);
    text(c, "GRAPHICS API", 1004, 302, 21, c->faint, 348);
    snprintf(b, sizeof(b), "%s  v", graphics_labels[f->graphics_index]);
    text(c, b, 1004, 352, 21, TITLE, 348);
    panel(c, 1406, 280, 408, 134, f->focus == 9);
    text(c, "CONTROLLER INPUT", 1436, 302, 21, c->faint, 348);
    snprintf(b, sizeof(b), "%s  v", f->input_index ? "Native gamepad" : "Mouse / keyboard");
    text(c, b, 1436, 352, 23, TITLE, 348);
    panel(c, 110, 430, 840, 110, f->focus == 10);
    small(c, "APPEARANCE", 140, 449, c->faint, 380);
    snprintf(b, sizeof(b), "%s  v", theme_labels[f->theme_index]);
    text(c, b, 140, 486, 29, TITLE, 380);
    roundbox(c, 850, 482, 42, 30, 6, c->accent);
    text(c, "Theme saves immediately", 535, 492, 20, c->muted, 310);
    panel(c, 974, 430, 840, 110, f->focus == 11);
    small(c, "DISPLAY PACING / VRR", 1004, 449, c->faint, 650);
    text(c, f->vrr_index ? "Stable refresh" : "Auto", 1004, 486, 29, TITLE, 330);
    text(c, "Stable refresh if VRR flickers", 1374, 492, 20, c->muted, 390);
    small(c, "JAVA RUNTIMES", 110, 565, c->faint, 1200);
    for (int j = 0; j < 4; j++)
    {
        int x = 110 + j * 432;
        const PmJavaRuntime *rt = runtime_for_major(v, java_majors[j]);
        panel(c, x, 600, 408, 185, f->focus == j + 1);
        snprintf(b, sizeof(b), "Java %d", java_majors[j]);
        text(c, b, x + 28, 615, 34, TITLE, 350);
        chip(c, rt ? "INSTALLED" : "NOT INSTALLED", x + 28, 660, rt != NULL);
        text(c, rt ? rt->version : "Download when needed", x + 29, 709, 20, c->muted, 350);
        text(c, rt ? "VERIFY >" : "DOWNLOAD >", x + 29, 750, 20, c->accent, 350);
    }
    if (v->java_count)
    {
        const PmJavaRuntime *rt =
            &v->java_runtimes[bound(f->selected_java, 0, count(v->java_count, PM_MAX_JAVA) - 1)];
        snprintf(b, sizeof(b), "Detected runtime: Java %d / %s / %s", rt->major, rt->version,
                 rt->valid ? "Ready" : "Needs attention");
        text(c, b, 110, 817, 21, c->faint, 1700);
    }
    button(c, "REFRESH JAVA RUNTIMES", 110, 861, 840, f->focus == 5, 0);
    button(c, "SAVE SETTINGS", 974, 861, 840, f->focus == 6, 1);
}
static void auth_qr(Canvas *c, const char *url)
{
    static char previous[256];
    static uint8_t qr[qrcodegen_BUFFER_LEN_FOR_VERSION(10)];
    static int valid;
    if (strncmp(url, "https://", 8))
        return;
    if (strcmp(previous, url))
    {
        uint8_t scratch[qrcodegen_BUFFER_LEN_FOR_VERSION(10)];
        copy(previous, sizeof(previous), url);
        valid = qrcodegen_encodeText(url, scratch, qr, qrcodegen_Ecc_MEDIUM, 1, 10,
                                     qrcodegen_Mask_AUTO, 1);
    }
    if (!valid)
        return;
    int size = qrcodegen_getSize(qr), scale = 208 / (size + 8), extent = (size + 8) * scale;
    int left = 1250 + (208 - extent) / 2, top = 445 + (208 - extent) / 2;
    box(c, left, top, extent, extent, 0xffffff);
    for (int y = 0; y < size; y++)
        for (int x = 0; x < size; x++)
            if (qrcodegen_getModule(qr, x, y))
                box(c, left + (x + 4) * scale, top + (y + 4) * scale, scale, scale, 0x000000);
}

static void accounts(Canvas *c, const PmFrontend *f, const PmView *v)
{
    int offline = !strcmp(v->account_mode, "offline");
    const char *name = !offline && v->account_username[0] ? v->account_username : v->username;
    heading(c, "Your account", "Sign in on your phone to use your Minecraft profile and skin.");
    button(c, offline ? "Offline  /  switch to Microsoft" : "Microsoft  /  switch to Offline", 110,
           286, 700, f->focus == 0, 0);
    panel(c, 110, 385, 700, 303, 0);
    icon(c, NULL, "vanilla", 140, 420, 82);
    text(c, name[0] ? name : offline ? "Player" : "Microsoft account", 250, 424, 36, TITLE, 520);
    text(c,
         offline                ? "Local offline profile"
         : v->account_status[0] ? v->account_status
                                : "Not signed in",
         250, 481, 23, c->muted, 520);
    small(c,
          offline ? "Local worlds are available offline." : "Your licensed Minecraft Java account.",
          141, 577, c->faint, 620);
    button(c, "START SIGN-IN", 110, 726, 700, f->focus == 1, 1);
    button(c, "CHECK SIGN-IN", 110, 815, 700, f->focus == 2, 0);
    panel(c, 864, 286, 946, 595, 0);
    if (v->auth_code[0] && !offline)
    {
        small(c, "SIGN IN ON YOUR PHONE", 910, 333, c->faint, 800);
        text(c, v->auth_code, 910, 405, 53, c->accent, 790);
        auth_qr(c, v->auth_url[0] ? v->auth_url : "https://microsoft.com/link");
        text(c, "Scan the QR code, or visit:", 910, 702, 24, TEXT, 800);
        text(c, v->auth_url[0] ? v->auth_url : "https://microsoft.com/link", 910, 746, 26, c->accent,
             800);
        text(c, "Enter the code. Sign-in completes automatically.", 910, 809, 21, c->muted, 800);
    }
    else
    {
        icon(c, NULL, "fabric", 1208, 362, 128);
        text(c, offline ? "Play your way" : "Bring your worlds with you", 910, 555, 36, TITLE, 800);
        text(c,
             offline ? "Switch to Microsoft for your licensed profile."
                     : "Start sign-in, then scan the code using your phone.",
             910, 625, 23, c->muted, 800);
        text(c, "Your password is entered only on Microsoft's website.", 910, 688, 21, c->faint, 800);
    }
}
static void packs(Canvas *c, const PmFrontend *f, const PmView *v)
{
    int content = f->screen == PM_MODS,
        n = count(content ? v->content_import_count : v->pack_count, PM_MAX_INSTANCES),
        start = list_start(f->selected_pack, 6);
    char b[512];
    snprintf(b, sizeof(b), "Copy files to /data/ProsperoMC/imports%s%s, then refresh.",
             content ? "/" : "", content ? kinds[f->content_kind] : "");
    heading(c, content ? "Import local content" : "Import your own pack", b);
    if (!n)
    {
        panel(c, 110, 315, 1700, 516, 0);
        empty(c, "No local files yet",
              content ? "Mods use .jar files; resource packs and shader packs use .zip."
                      : "PolyMC / MultiMC .zip and Modrinth .mrpack are supported.");
    }
    for (int j = start; j < n && j < start + 6; j++)
    {
        int y = 315 + (j - start) * 86;
        panel(c, 110, y, 1700, 76, j == f->selected_pack);
        icon(c, NULL, content ? "forge" : "vanilla", 129, y + 9, 56);
        text(c, (content ? v->content_imports : v->packs)[j].name, 214, y + 24, 27, TITLE, 1545);
    }
}
static void remote_packs(Canvas *c, const PmFrontend *f, const PmView *v)
{
    char b[512];
    int releases = f->remote_stage, content = f->screen == PM_MODS;
    const char *provider = f->add_source == 2 && !content ? "CurseForge" : "Modrinth";
    snprintf(b, sizeof(b), "%s / %s", provider,
             content ? kind_labels[f->content_kind] : "Modpacks");
    const PmInstance *i = selected_instance(f, v);
    char subtitle[512];
    if (content && i)
        snprintf(subtitle, sizeof(subtitle),
                 "For %s / Minecraft %s. Choose a project, then its release.",
                 i->name[0] ? i->name : i->id, i->version);
    else
        copy(subtitle, sizeof(subtitle),
             "Browse packs or search by name. Choose a project, then its release.");
    if (content && i)
    {
        snprintf(b, sizeof(b), "%s / Minecraft %s", i->name[0] ? i->name : i->id, i->version);
        heading(c, releases ? "Choose a release" : "Find content", b);
        for (int j = 0; j < 3; j++)
        {
            int x = 110 + j * 290;
            roundbox(c, x, 292, 274, 50, 10, f->content_kind == j ? c->focus_rgb : c->row);
            text(c, kind_labels[j], x + 20, 307, 22, f->content_kind == j ? c->accent : c->muted, 235);
        }
    }
    else
        heading(c, releases ? "Choose a release" : b, subtitle);
    int search_y = content ? 355 : 283, list_y = content ? 445 : 363, rows = content ? 4 : 5;
    search_bar(c, f, provider, content ? kind_labels[f->content_kind] : "modpacks", search_y,
               content);
    if (f->search_editor)
    {
        panel(c, 110, content ? 427 : 365, 1700, content ? 455 : 517, 0);
        for (int j = 0; j < 40; j++)
        {
            char label[16];
            if (j == 38)
                copy(label, sizeof(label), "ERASE");
            else if (j == 39)
                copy(label, sizeof(label), "SEARCH");
            else if (search_keys[j] == ' ')
                copy(label, sizeof(label), "SPACE");
            else
            {
                label[0] = search_keys[j];
                label[1] = 0;
            }
            button(c, label, 140 + (j % 10) * 164, (content ? 445 : 385) + (j / 10) * 92, 150,
                   f->search_key == j, j == 39);
        }
        small(c, "USB keyboard works here too. Triangle searches; Square erases.", 140, 803, c->faint,
              1630);
        return;
    }
    int n = count(releases ? v->remote_version_count : v->remote_count, releases ? 64 : 24);
    int sel = bound(releases ? f->selected_release : f->selected_remote, 0, n ? n - 1 : 0);
    int start = list_start(sel, rows);
    if (!n)
    {
        panel(c, 110, list_y, 1700, content ? 338 : 420, 0);
        snprintf(b, sizeof(b), "Searching %s...", provider);
        text(c, v->busy ? b : "No matching results", 150, list_y + 50, 34, TITLE, 1520);
        small(c, "Use the search bar above, or refresh to try again.", 152, list_y + 110, c->muted,
              1500);
    }
    for (int j = start; j < n && j < start + rows; j++)
    {
        int y = list_y + (j - start) * 86;
        panel(c, 110, y, 1700, 76, j == sel && f->remote_focus == 1);
        icon(c, releases ? NULL : v->remote_packs[j].icon, content ? "forge" : "fabric", 130, y + 8,
             60);
        text(c, releases ? v->remote_versions[j].name : v->remote_packs[j].name, 215, y + 8, 26,
             TITLE, 1530);
        if (releases)
            snprintf(b, sizeof(b), "Minecraft %s / %s", v->remote_versions[j].game,
                     v->remote_versions[j].loader);
        else
            copy(b, sizeof(b), v->remote_packs[j].description);
        text(c, b, 216, y + 47, 18, c->muted, 1530);
    }
    button(c, "< BACK", 110, 824, 480, 0, 0);
    if (!releases)
    {
        button(c, "< PREVIOUS PAGE", 615, 824, 480, 0, 0);
        snprintf(b, sizeof(b), "NEXT PAGE >   %d / %d", v->remote_offset / 24 + 1,
                 (v->remote_total + 23) / 24);
        button(c, b, 1120, 824, 690, 0, 0);
    }
}
static void overlay(Canvas *c, const PmFrontend *f, const PmView *v)
{
    if (!f->confirmation && !f->selector_popup && !f->rename_editor)
        return;
    for (int y = 0; y < (int)c->t->height; y++)
        for (int x = 0; x < (int)c->t->width; x++)
            px(c, x, y, c->base, 190);
    if (f->rename_editor)
    {
        panel(c, 110, 210, 1700, 690, 0);
        text(c, "Rename instance", 140, 238, 31, TITLE, 1300);
        roundbox(c, 140, 295, 1640, 64, 10, f->rename_replace ? c->focus_rgb : c->row);
        text(c, f->rename_text[0] ? f->rename_text : "Enter a name...", 161, 310, 27,
             f->rename_replace ? c->accent : TITLE, 1590);
        for (int j = 0; j < 45; j++)
        {
            char label[32];
            if (j < 40)
            {
                char letter = rename_keys[j];
                if (f->rename_lower && letter >= 'A' && letter <= 'Z') letter += 'a' - 'A';
                if (letter == ' ') copy(label, sizeof(label), "SPACE");
                else { label[0] = letter; label[1] = 0; }
            }
            else copy(label, sizeof(label), j == 40 ? "ERASE" : j == 41 ? "CLEAR" :
                      j == 42 ? (f->rename_lower ? "a > A" : "A > a") : j == 43 ? "SAVE" : "CANCEL");
            button(c, label, 140 + (j % 9) * 184, 380 + (j / 9) * 82, 170,
                   f->rename_key == j, j == 43);
        }
        small(c, "Square: erase  /  Triangle or Enter: save  /  Circle: cancel", 140, 821, c->muted, 1620);
        text(c, f->notice[0] ? f->notice : "Typing replaces the selected name. Worlds and content stay in this instance.",
             140, 858, 20, f->notice[0] ? WARN : c->faint, 1620);
        return;
    }
    if (f->selector_popup)
    {
        panel(c, 630, 233, 660, 626, 0);
        text(c,
             f->selector_popup == 5   ? "Theme color"
             : f->selector_popup == 1 ? "Minecraft memory"
             : f->selector_popup == 2 ? "Game resolution"
             : f->selector_popup == 3 ? "Graphics API"
                                      : "Controller input",
             666, 264, 31, TITLE, 580);
        int rows = f->selector_popup == 5   ? 6
                   : f->selector_popup == 1 ? 7
                   : f->selector_popup == 2 ? 4
                   : f->selector_popup == 3 ? 2
                                            : 2,
            start = f->selector_popup == 1 ? list_start(f->selector_choice, 7) : 0;
        if (f->selector_popup == 1)
            rows = bound(31 - start, 0, rows);
        for (int j = 0; j < rows; j++)
        {
            char b[64];
            if (f->selector_popup == 5)
                copy(b, sizeof(b), theme_labels[j]);
            else if (f->selector_popup == 1)
                snprintf(b, sizeof(b), "%d MB", 512 + (start + j) * 256);
            else if (f->selector_popup == 2)
                copy(b, sizeof(b), resolution_labels[j]);
            else if (f->selector_popup == 3)
                copy(b, sizeof(b), graphics_labels[j]);
            else
                copy(b, sizeof(b), input_labels[j]);
            if (start + j == f->selector_choice)
                roundbox(c, 665, 320 + j * 70, 590, 60, 10, c->focus_rgb);
            if (f->selector_popup == 5)
                roundbox(c, 1200, 338 + j * 70, 25, 25, 4, theme_colors[j]);
            text(c, b, 694, 336 + j * 70, 26, start + j == f->selector_choice ? c->accent : TEXT, 535);
        }
        return;
    }
    panel(c, 580, 330, 760, 412, 0);
    text(c,
         f->confirmation == 2   ? "Close ProsperoMC?"
         : f->confirmation == 1 ? "Delete this instance?"
                                : "Delete this content?",
         630, 376, 35, TITLE, 650);
    const PmInstance *i = selected_instance(f, v);
    text(c,
         f->confirmation == 2   ? "Return to the PS5 home screen."
         : f->confirmation == 3 ? f->confirmation_file
         : i                    ? (i->name[0] ? i->name : i->id)
                                : "",
         630, 444, 25, c->muted, 650);
    text(c,
         f->confirmation == 1   ? "This deletes its worlds and installed content."
         : f->confirmation == 3 ? "The selected file will be removed."
         : v->busy              ? "The current download or operation will stop."
                                : "",
         630, 494, 23, WARN, 650);
    button(c, "CANCEL", 630, 625, 310, !f->confirmation_choice, 0);
    button(c, f->confirmation == 2 ? "CLOSE" : "DELETE", 980, 625, 310, f->confirmation_choice, 1);
}
void pm_frontend_render(const PmFrontend *frontend, const PmView *v, const PwPresentTarget *target)
{
    if (!frontend || !v || !target || !target->pixels || !target->width || !target->height ||
        target->width > 16384 || target->height > 16384)
        return;
    if (target->stride < (uint64_t)target->width * 4 ||
        target->bytes < (uint64_t)target->stride * target->height)
        return;
    PmFrontend f = *frontend;
    normalize(&f, v);
    Canvas c;
    c.t = target;
    c.accent = theme_colors[f.theme_index];
    c.base = theme_backgrounds[f.theme_index];
    c.muted = mix(0xb8bec6, c.accent, 32);
    c.faint = mix(0x89909c, c.accent, 24);
    c.panel = mix(c.base,c.accent,14);
    c.row = mix(c.base,c.accent,22);
    c.edge = mix(c.base,c.accent,45);
    c.focus_rgb = mix(c.panel, c.accent, 26);
    c.opacity = 255;
    c.offset_x = 0;
    c.focus_alpha = 140 + bound((int)f.focus_ms, 0, 180) * 115 / 180;
    for (int y = 0; y < 1080; y++)
        box(&c, 0, y, 1920, 1, mix(c.base,c.accent,(unsigned)(y*9/1080)));
    /* Quiet block terrain behind the catalog; no textures or extra assets. */
    static const unsigned char skyline[] = {4,5,5,6,4,3,4,6,7,7,5,4,5,3,2,4,5,6,6,4,3,4,6,5,4,3,5,6,5,4};
    for (unsigned j = 0; j < sizeof(skyline); j++)
    {
        int top = 1010 - skyline[j] * 32;
        box(&c, (int)j * 64, top, 64, 1080 - top, mix(c.base,c.accent,5));
        box(&c, (int)j * 64, top, 64, 4, mix(c.base,c.accent,10));
    }
    header(&c, &f, v);
    unsigned remaining = bound((int)f.transition_ms, 0, 220);
    unsigned eased = remaining*remaining*remaining/(220u*220u);
    c.offset_x = f.transition_direction*sx(&c, (int)(18u*eased/220u));
    c.opacity = 255u-55u*eased/220u;
    if (f.remote_browser)
        remote_packs(&c, &f, v);
    else if (f.pack_picker)
        packs(&c, &f, v);
    else
        switch (f.screen)
        {
        case PM_HOME:
            home(&c, &f, v);
            break;
        case PM_LIBRARY:
            library(&c, &f, v);
            break;
        case PM_VERSIONS:
            versions(&c, &f, v);
            break;
        case PM_MODS:
            content(&c, &f, v);
            break;
        case PM_SETTINGS:
            settings(&c, &f, v);
            break;
        case PM_ACCOUNTS:
            accounts(&c, &f, v);
            break;
        default:
            break;
        }
    c.opacity = 255;
    c.offset_x = 0;
    footer(&c, &f, v);
    overlay(&c, &f, v);
    if (f.pointer_visible)
    {
        for (int j = 0; j < 20; j++)
            box(&c, f.pointer_x, f.pointer_y + j, j / 2 + 2, 1, c.base);
        for (int j = 1; j < 17; j++)
            box(&c, f.pointer_x + 1, f.pointer_y + j, j / 2, 1, TITLE);
    }
}
