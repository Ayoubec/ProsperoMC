#include "pm_frontend.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static PmView v;
static PmFrontend f;
static PmAction a;
static int key(PmKey k)
{
    return pm_frontend_update(&f, &v, k, &a);
}
static int pointer(int x, int y, int b, int wheel)
{
    return pm_frontend_pointer(&f, &v, x, y, b, wheel, &a);
}
static void fixture(void)
{
    memset(&v, 0, sizeof(v));
    pm_frontend_init(&f);
    v.instance_count = 16;
    v.memory_mb = 3584;
    v.resolution_height = 1440;
    for (int j = 0; j < 16; j++)
    {
        snprintf(v.instances[j].id, PM_TEXT, "world-%d", j);
        snprintf(v.instances[j].name, PM_TEXT, "World %d", j);
        strcpy(v.instances[j].version, "26.2");
        strcpy(v.instances[j].loader, "fabric");
        v.instances[j].installed = 1;
    }
    v.version_count = 3;
    strcpy(v.versions[0].id, "26.3");
    strcpy(v.versions[0].type, "snapshot");
    strcpy(v.versions[1].id, "26.2");
    strcpy(v.versions[1].type, "release");
    strcpy(v.versions[2].id, "1.12.2");
    strcpy(v.versions[2].type, "release");
    strcpy(v.account_mode, "microsoft");
    strcpy(v.account_username, "OwnedPlayer");
}
static void content_fixture(const char *id, const char *kind)
{
    strcpy(v.content_instance, id);
    strcpy(v.content_kind, kind);
    v.mod_count = 2;
    strcpy(v.mods[0].name, "sodium.jar");
    v.mods[0].enabled = 1;
    strcpy(v.mods[1].name, "example.jar");
    v.mods[1].enabled = 0;
}
static void home_library(void)
{
    fixture();
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "prepare-launch") && !strcmp(a.id, "world-0"));
    assert(!key(PM_KEY_DOWN));
    assert(f.selected_instance == 4);
    assert(!key(PM_KEY_DOWN));
    assert(f.selected_instance == 8);
    assert(!key(PM_KEY_DOWN));
    assert(f.selected_instance == 12);
    assert(!key(PM_KEY_UP));
    assert(f.selected_instance == 8 && f.header_focus < 0);
    assert(!pointer(1650, 865, 1, 0));
    assert(f.selected_instance == 12);
    assert(!pointer(775, 333, 1, 0));
    assert(f.selected_instance == 13);
    assert(pointer(775, 333, 1, 0));
    assert(!strcmp(a.id, "world-13"));
    assert(!key(PM_KEY_NEXT_TAB));
    assert(f.screen == PM_LIBRARY);
    assert(!key(PM_KEY_RIGHT));
    assert(!key(PM_KEY_DOWN));
    assert(key(PM_KEY_CONFIRM));
    assert(f.screen == PM_MODS && !strcmp(a.command, "content-list"));
    f.screen = PM_LIBRARY;
    f.focus = 4;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "clone"));
    f.focus = 5;
    assert(!key(PM_KEY_CONFIRM));
    assert(f.confirmation == 1 && !f.confirmation_choice);
    assert(!key(PM_KEY_CONFIRM));
    assert(!f.confirmation && !a.command[0]);
    assert(!key(PM_KEY_CONFIRM));
    assert(!key(PM_KEY_RIGHT));
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "delete-instance") && !strcmp(a.id, "world-13"));
    assert(!key(PM_KEY_CONFIRM));
    assert(!key(PM_KEY_RIGHT));
    f.selected_instance = 14;
    assert(!key(PM_KEY_CONFIRM));
    assert(!a.command[0]);
}
static void instances(void)
{
    fixture();
    f.screen = PM_VERSIONS;
    assert(!key(PM_KEY_CONFIRM));
    assert(f.add_source == 0 && f.selected_version == 1);
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "create-install") && !strcmp(a.version, "26.2") &&
           !strcmp(a.loader, "vanilla"));
    f.focus = 1;
    assert(!key(PM_KEY_CONFIRM));
    assert(f.loader_index == 1);
    f.focus = 2;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.loader, "fabric"));
    assert(!key(PM_KEY_BACK));
    assert(f.add_source == -1);
    f.focus = 0;
    assert(!key(PM_KEY_CONFIRM));
    f.loader_index = 3;
    assert(!key(PM_KEY_CONFIRM));
    assert(f.notice[0]);
    f.selected_version = 2;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.loader, "forge") && !strcmp(a.version, "1.12.2"));
    assert(!key(PM_KEY_BACK));
    f.focus = 2;
    assert(key(PM_KEY_CONFIRM));
    assert(f.remote_browser && !strcmp(a.command, "curse-search"));
    v.remote_count = 1;
    strcpy(v.remote_packs[0].id, "curse-project");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "curse-versions"));
    v.remote_version_count = 1;
    strcpy(v.remote_project, "curse-project");
    strcpy(v.remote_versions[0].id, "curse-release");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "curse-download"));
    assert(!a.name[0]);
    assert(!key(PM_KEY_BACK));
    assert(!key(PM_KEY_BACK));
    f.focus = 3;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "scan-packs") && f.pack_picker);
    v.pack_count = 1;
    strcpy(v.packs[0].source, "Z:/data/ProsperoMC/imports/pack.mrpack");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "import-pack") && !strcmp(a.source, v.packs[0].source));
    f.add_source = -1;
    f.focus = 1;
    assert(key(PM_KEY_CONFIRM));
    assert(f.remote_browser && !strcmp(a.command, "pack-search"));
    v.remote_count = 1;
    v.remote_total = 25;
    strcpy(v.remote_packs[0].id, "pack-project");
    assert(key(PM_KEY_RIGHT));
    assert(a.offset == 24);
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "pack-versions"));
    v.remote_version_count = 1;
    strcpy(v.remote_project, "pack-project");
    strcpy(v.remote_versions[0].id, "release-id");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "pack-download") && !strcmp(a.pack_version, "release-id"));
    assert(!key(PM_KEY_BACK));
    assert(!f.remote_stage);
    assert(!key(PM_KEY_BACK));
    assert(!f.remote_browser && f.add_source == -1);
    v.busy = 1;
    assert(!key(PM_KEY_CONFIRM));
    assert(!a.command[0]);
    memset(&v, 0, sizeof(v));
    pm_frontend_init(&f);
    assert(!key(PM_KEY_CONFIRM));
    assert(f.screen == PM_VERSIONS);
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "catalog"));
}
static void content(void)
{
    fixture();
    f.screen = PM_LIBRARY;
    f.focus = 2;
    assert(key(PM_KEY_CONFIRM));
    content_fixture("world-0", "mods");
    f.focus = 2;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "content-toggle") && !strcmp(a.enabled, "false") &&
           !strcmp(a.content_kind, "mods"));
    f.selected_mod = 1;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.enabled, "true") && !strcmp(a.mod, "example.jar"));
    f.focus = 1;
    assert(key(PM_KEY_RIGHT));
    assert(f.content_kind == 1 && !strcmp(a.content_kind, "resourcepacks"));
    content_fixture("world-0", "resourcepacks");
    assert(key(PM_KEY_RIGHT));
    assert(f.content_kind == 2 && !strcmp(a.content_kind, "shaderpacks"));
    content_fixture("world-0", "shaderpacks");
    f.focus = 0;
    assert(key(PM_KEY_RIGHT));
    assert(!strcmp(a.id, "world-1") && !strcmp(a.content_kind, "shaderpacks"));
    f.focus = 2;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "content-list")); /* stale content cannot affect another instance */
    content_fixture("world-1", "shaderpacks");
    f.focus = 5;
    assert(!key(PM_KEY_CONFIRM));
    assert(f.confirmation == 3);
    assert(!key(PM_KEY_RIGHT));
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "content-delete") && !strcmp(a.id, "world-1"));
    f.focus = 4;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "scan-content-imports") && f.pack_picker);
    v.content_import_count = 1;
    strcpy(v.content_imports[0].source, "Z:/data/ProsperoMC/imports/shaderpacks/shader.zip");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "content-import") && !strcmp(a.source, v.content_imports[0].source));
    f.focus = 3;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "content-search") && !strcmp(a.id, "world-1"));
    assert(!key(PM_KEY_SECONDARY));
    f.query[0] = 0;
    pm_frontend_text(&f, 'A');
    pm_frontend_text(&f, 'B');
    pm_frontend_text(&f, 8);
    assert(!strcmp(f.query, "A"));
    f.search_key = 39;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.query, "A"));
    v.remote_count = 1;
    strcpy(v.remote_packs[0].id, "shader-project");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "content-versions"));
    v.remote_version_count = 1;
    strcpy(v.remote_project, "shader-project");
    strcpy(v.remote_versions[0].id, "shader-version");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "content-download") && !strcmp(a.content_kind, "shaderpacks"));
    f.remote_browser = 0;
    v.busy = 1;
    f.focus = 1;
    assert(!key(PM_KEY_RIGHT));
    assert(!a.command[0]);
    assert(!pointer(150, 320, 1, 0));
    assert(!a.command[0]);
    assert(!key(PM_KEY_NEXT_TAB));
    assert(f.screen == PM_SETTINGS);
}
static void settings_accounts_close(void)
{
    fixture();
    f.screen = PM_SETTINGS;
    assert(!key(PM_KEY_NONE));
    assert(f.memory_mb == 3584 && f.resolution_index == 2);
    assert(!key(PM_KEY_RIGHT));
    assert(f.focus == 7);
    assert(!key(PM_KEY_RIGHT));
    assert(f.focus == 8);
    assert(!key(PM_KEY_RIGHT));
    assert(f.focus == 9);
    assert(!key(PM_KEY_LEFT));
    assert(f.focus == 8);
    assert(!key(PM_KEY_LEFT));
    assert(f.focus == 7);
    assert(!key(PM_KEY_LEFT));
    assert(f.focus == 0);
    assert(f.memory_mb == 3584 && f.resolution_index == 2 && f.graphics_index == 0 &&
           f.input_index == 0);
    assert(!key(PM_KEY_CONFIRM));
    assert(f.selector_popup == 1);
    assert(!key(PM_KEY_DOWN));
    assert(!key(PM_KEY_CONFIRM));
    assert(f.memory_mb == 3840);
    assert(!key(PM_KEY_RIGHT));
    assert(f.focus == 7);
    assert(!key(PM_KEY_CONFIRM));
    assert(f.selector_popup == 2);
    assert(!pointer(775, 350, 1, 0));
    assert(f.resolution_index == 0 && !f.selector_popup);
    assert(!key(PM_KEY_RIGHT));
    assert(f.focus == 8);
    assert(!key(PM_KEY_CONFIRM));
    assert(f.selector_popup == 3);
    assert(!key(PM_KEY_DOWN));
    assert(!key(PM_KEY_UP));
    assert(!key(PM_KEY_CONFIRM));
    assert(f.graphics_index == 0);
    assert(!key(PM_KEY_RIGHT));
    assert(f.focus == 9);
    assert(!key(PM_KEY_CONFIRM));
    assert(f.selector_popup == 4);
    assert(!key(PM_KEY_DOWN));
    assert(!key(PM_KEY_CONFIRM));
    assert(f.input_index == 1);
    assert(!key(PM_KEY_DOWN));
    assert(f.focus == 11);
    assert(!key(PM_KEY_UP));
    assert(f.focus == 8);
    f.focus = 6;
    assert(key(PM_KEY_CONFIRM));
    assert(a.memory_mb == 3840 && a.resolution_height == 720);
    assert(!strcmp(a.graphics, "zink"));
    assert(!strcmp(a.controller_mode, "native"));
    f.focus = 8;
    assert(!key(PM_KEY_CONFIRM));
    assert(!key(PM_KEY_DOWN));
    assert(f.selector_choice == 1);
    assert(!key(PM_KEY_CONFIRM));
    f.focus = 6;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.graphics, "vulkan"));
    const int majors[] = {8, 17, 21, 25};
    for (int j = 1; j <= 4; j++)
    {
        f.focus = j;
        assert(key(PM_KEY_CONFIRM));
        assert(a.java_major == majors[j - 1]);
    }
    f.focus = 5;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "detect-java"));
    f.screen = PM_ACCOUNTS;
    f.focus = 0;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.account_mode, "offline"));
    strcpy(v.account_mode, "offline");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.account_mode, "microsoft"));
    f.focus = 1;
    assert(!key(PM_KEY_CONFIRM));
    strcpy(v.account_mode, "microsoft");
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "auth-device"));
    f.focus = 2;
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "auth-poll"));
    assert(!pointer(1770, 75, 1, 0));
    assert(f.confirmation == 2);
    assert(!key(PM_KEY_CONFIRM));
    assert(!a.command[0]);
    assert(!pointer(1770, 75, 1, 0));
    assert(pointer(1100, 651, 1, 0));
    assert(!strcmp(a.command, "quit"));
    pm_frontend_init(&f);
    assert(!key(PM_KEY_UP));
    assert(f.header_focus == PM_HOME);
    for (int j = 0; j < PM_SCREEN_COUNT; j++)
        assert(!key(PM_KEY_RIGHT));
    assert(!key(PM_KEY_CONFIRM));
    assert(f.confirmation == 2);
    v.busy = 1;
    assert(!key(PM_KEY_RIGHT));
    assert(key(PM_KEY_CONFIRM));
    assert(!strcmp(a.command, "quit"));
}
static unsigned char image_pixels[] = {255, 0, 0, 255, 255, 0, 0, 255,
                                       255, 0, 0, 255, 255, 0, 0, 255};
static void search_and_delete_regressions(void)
{
    for (int provider = 1; provider <= 2; provider++)
    {
        fixture();
        f.screen = PM_VERSIONS;
        f.focus = provider;
        strcpy(f.query, "Fabulously Optimized");
        assert(key(PM_KEY_CONFIRM));
        assert(!a.query[0] && !f.query[0]);
        assert(!strcmp(a.command, provider == 1 ? "pack-search" : "curse-search"));
        v.remote_count = 1;
        strcpy(v.remote_packs[0].id, "test-project");
        /* Saved provider source alone restores the page and its visible bar. */
        f.remote_browser = 0;
        assert(!key(PM_KEY_NONE));
        assert(f.remote_browser);
        assert(!pointer(450, 313, 1, 0));
        assert(f.search_editor);
        pm_frontend_text(&f, 'Q');
        assert(pointer(1650, 313, 1, 0));
        assert(!strcmp(a.query, "Q"));
        assert(!f.search_editor && f.remote_focus == 1);
        assert(!key(PM_KEY_UP));
        assert(f.remote_focus == 0);
        assert(!key(PM_KEY_CONFIRM));
        assert(f.search_editor);
        assert(key(PM_KEY_REFRESH));
        assert(pointer(450, 390, 1, 0));
        assert(!strcmp(a.command, provider == 1 ? "pack-versions" : "curse-versions"));
    }
    const char *kind[] = {"mods", "resourcepacks", "shaderpacks"};
    const char *file[] = {"test.jar", "resources.zip", "shader.zip"};
    for (int j = 0; j < 3; j++)
    {
        fixture();
        f.screen = PM_MODS;
        assert(pointer(160 + j * 290, 315, 1, 0));
        assert(!strcmp(a.content_kind, kind[j]) && !strcmp(a.id, "world-0"));
        content_fixture("world-0", kind[j]);
        strcpy(v.mods[0].name, file[j]);
        f.focus = 2;
        assert(!key(PM_KEY_RIGHT));
        assert(f.focus == 4);
        f.focus = 3;
        assert(!key(PM_KEY_DOWN));
        assert(f.focus == 2);
        assert(!key(PM_KEY_RIGHT));
        assert(f.focus == 4);
        assert(!key(PM_KEY_DOWN));
        assert(f.focus == 5);
        assert(!key(PM_KEY_UP));
        assert(f.focus == 4);
        assert(!key(PM_KEY_DOWN));
        assert(f.focus == 5);
        assert(!key(PM_KEY_CONFIRM));
        assert(f.confirmation == 3);
        assert(!key(PM_KEY_RIGHT));
        assert(key(PM_KEY_CONFIRM));
        assert(!strcmp(a.command, "content-delete") && !strcmp(a.content_kind, kind[j]) &&
               !strcmp(a.mod, file[j]));
        assert(!pointer(1480, 580, 1, 0));
        assert(f.confirmation == 3);
        assert(pointer(1110, 650, 1, 0));
        assert(!strcmp(a.mod, file[j]));
        f.focus = 3;
        assert(key(PM_KEY_CONFIRM));
        assert(!strcmp(a.command, "content-search"));
        assert(!pointer(450, 380, 1, 0));
        assert(f.search_editor);
        f.query[0] = 0;
        pm_frontend_text(&f, 'P');
        assert(pointer(1650, 380, 1, 0));
        assert(!strcmp(a.command, "content-search") && !strcmp(a.query, "P") &&
               !strcmp(a.content_kind, kind[j]));
        assert(!key(PM_KEY_BACK));
        assert(!f.remote_browser);
        /* Search is directly on the installed-content page, not only browse. */
        f.focus = 0;
        assert(!key(PM_KEY_DOWN));
        assert(f.focus == 1);
        assert(!key(PM_KEY_DOWN));
        assert(f.focus == 6);
        assert(!key(PM_KEY_CONFIRM));
        assert(f.search_editor);
        assert(!key(PM_KEY_BACK));
        assert(!f.remote_browser && !f.search_editor);
        assert(!pointer(450, 380, 1, 0));
        assert(f.search_editor);
        assert(!key(PM_KEY_BACK));
        assert(pointer(1650, 380, 1, 0));
        assert(!strcmp(a.command, "content-search"));
    }
}
static const uint8_t *test_icon(const char *path, unsigned *w, unsigned *h)
{
    if (strcmp(path, "test-icon"))
        return NULL;
    *w = *h = 2;
    return image_pixels;
}
static void render_bounds(void)
{
    fixture();
    strcpy(v.instances[0].icon, "test-icon");
    pm_frontend_set_icon_loader(test_icon);
    unsigned char *bytes = malloc(1920 * 1080 * 4 + 32);
    assert(bytes);
    memset(bytes, 0x5a, 1920 * 1080 * 4 + 32);
    PwPresentTarget t = {0};
    t.pixels = bytes + 16;
    t.width = 1920;
    t.height = 1080;
    t.stride = 1920 * 4;
    t.bytes = 1920 * 1080 * 4;
    pm_frontend_render(&f, &v, &t);
    unsigned char *p = t.pixels + 350 * t.stride + 160 * 4;
    assert(p[0] == 0 && p[1] == 0 && p[2] == 255);
    v.instance_count = PM_MAX_INSTANCES + 99;
    v.version_count = PM_MAX_VERSIONS + 99;
    v.mod_count = PM_MAX_MODS + 99;
    for (int screen = 0; screen < PM_SCREEN_COUNT; screen++)
    {
        pm_frontend_init(&f);
        f.screen = (PmScreen)screen;
        f.selected_instance = f.selected_version = f.selected_mod = 99999;
        f.focus = 9999;
        for (int j = 0; j < 40; j++)
            key((PmKey)(PM_KEY_UP + j % 4));
        assert(f.selected_instance < PM_MAX_INSTANCES && f.selected_version < PM_MAX_VERSIONS &&
               f.selected_mod < PM_MAX_MODS);
        pm_frontend_render(&f, &v, &t);
    }
    for (int j = 0; j < 16; j++)
    {
        assert(bytes[j] == 0x5a);
        assert(bytes[1920 * 1080 * 4 + 16 + j] == 0x5a);
    }
    memset(bytes + 16, 0x5a, 1920 * 1080 * 4);
    t.bytes = 1;
    pm_frontend_render(&f, &v, &t);
    assert(bytes[16] == 0x5a);
    t.bytes = 1920 * 1080 * 4;
    t.stride = 1;
    pm_frontend_render(&f, &v, &t);
    assert(bytes[16] == 0x5a);
    free(bytes);
    pm_frontend_set_icon_loader(NULL);
}
static void themes_and_motion(void)
{
    fixture();
    f.screen=PM_SETTINGS;
    strcpy(v.theme_color,"ocean");
    assert(!key(PM_KEY_NONE)&&f.theme_index==1);
    assert(!key(PM_KEY_DOWN)&&f.focus==10);
    assert(!key(PM_KEY_CONFIRM)&&f.selector_popup==5);
    assert(!key(PM_KEY_DOWN));
    assert(!key(PM_KEY_DOWN));
    assert(key(PM_KEY_CONFIRM)&&f.theme_index==3&&!strcmp(a.theme_color,"amethyst"));
    f.focus=6;assert(key(PM_KEY_CONFIRM)&&!strcmp(a.theme_color,"amethyst"));
    assert(!pointer(350,480,1,0)&&f.selector_popup==5);
    assert(pointer(900,350,1,0)&&f.theme_index==0&&!strcmp(a.theme_color,"grass"));
    assert(!key(PM_KEY_NEXT_TAB)&&f.transition_ms==220);
    pm_frontend_tick(&f,16);assert(f.transition_ms==204);
    for(int j=0;j<15;j++)pm_frontend_tick(&f,16);
    assert(!f.transition_ms);
    f.screen=PM_SETTINGS;f.focus=10;
    assert(!key(PM_KEY_RIGHT)&&f.focus==11);
    assert(key(PM_KEY_CONFIRM)&&f.vrr_index==1&&!strcmp(a.vrr_mode,"stable"));
    f.focus=6;assert(key(PM_KEY_CONFIRM)&&!strcmp(a.vrr_mode,"stable"));
    assert(pointer(1650,480,1,0)&&f.vrr_index==0&&!strcmp(a.vrr_mode,"auto"));
    f.focus=9;assert(!key(PM_KEY_DOWN)&&f.focus==11);
    assert(!key(PM_KEY_DOWN)&&f.focus==3);
    assert(!key(PM_KEY_UP)&&f.focus==11);
    assert(!key(PM_KEY_LEFT)&&f.focus==10);
    assert(!key(PM_KEY_DOWN)&&f.focus==1);
    assert(!key(PM_KEY_DOWN)&&f.focus==5);
    assert(!key(PM_KEY_RIGHT)&&f.focus==6);
}
static void full_palettes_and_transparent_icons(void)
{
    fixture();
    const char *names[]={"grass","ocean","diamond","amethyst","redstone","gold"};
    uint8_t *pixels=calloc(1,1920*1080*4);assert(pixels);
    PwPresentTarget target={pixels,1920,1080,1920*4,1920*1080*4};
    uint32_t backgrounds[6],surfaces[6];
    pm_frontend_set_icon_loader(test_icon);
    image_pixels[15]=0;
    strcpy(v.instances[0].icon,"test-icon");
    for(int j=0;j<6;j++)
    {
        pm_frontend_init(&f);strcpy(v.theme_color,names[j]);
        f.header_focus=PM_HOME;
        pm_frontend_render(&f,&v,&target);
        memcpy(&backgrounds[j],pixels+(180*1920+20)*4,4);
        memcpy(&surfaces[j],pixels+(325*1920+218)*4,4);
        // The existing 2x2 icon fixture's transparent corner must leave the
        // same card surface as its surroundings, with no opaque icon plate.
        assert(!memcmp(pixels+(377*1920+193)*4,pixels+(377*1920+218)*4,4));
        for(int k=0;k<j;k++)
        {
            assert(backgrounds[j]!=backgrounds[k]);
            assert(surfaces[j]!=surfaces[k]);
        }
    }
    image_pixels[15]=255;
    free(pixels);pm_frontend_set_icon_loader(NULL);
    puts("FULL_PALETTE_AND_ICON_ALPHA_PASS six backgrounds and surfaces");
}
static void renaming(void)
{
    fixture();f.screen=PM_LIBRARY;f.focus=3;
    assert(!key(PM_KEY_CONFIRM)&&f.rename_editor&&f.rename_replace);
    assert(!key(PM_KEY_CONFIRM)&&!strcmp(f.rename_text,"A"));
    f.rename_key=42;assert(!key(PM_KEY_CONFIRM)&&f.rename_lower);
    f.rename_key=1;assert(!key(PM_KEY_CONFIRM)&&!strcmp(f.rename_text,"Ab"));
    pm_frontend_text(&f,'.');pm_frontend_text(&f,'2');
    assert(!key(PM_KEY_SECONDARY)&&!strcmp(f.rename_text,"Ab."));
    assert(key(PM_KEY_REFRESH)&&!f.rename_editor&&!strcmp(a.command,"rename-instance")&&
           !strcmp(a.id,"world-0")&&!strcmp(a.name,"Ab."));
    assert(!pointer(1400,689,1,0)&&f.rename_editor);
    assert(!pointer(250,320,1,0)&&f.rename_replace);
    pm_frontend_text(&f,'N');pm_frontend_text(&f,'E');pm_frontend_text(&f,'W');
    assert(pointer(1500,735,1,0)&&!strcmp(a.name,"NEW"));
    assert(!key(PM_KEY_CONFIRM)&&f.rename_editor);
    f.rename_key=41;assert(!key(PM_KEY_CONFIRM)&&!f.rename_text[0]);
    assert(!key(PM_KEY_REFRESH)&&f.rename_editor&&!a.command[0]&&f.notice[0]);
    pm_frontend_text(&f,'X');v.busy=1;
    assert(!key(PM_KEY_REFRESH)&&f.rename_editor&&!a.command[0]);
    v.busy=0;f.selected_instance=1;
    assert(!key(PM_KEY_REFRESH)&&!a.command[0]);
    assert(!key(PM_KEY_BACK)&&!f.rename_editor);
    f.selected_instance=0;assert(!key(PM_KEY_CONFIRM));
    pm_frontend_text(&f,'C');
    for(int j=0;j<150;j++)pm_frontend_text(&f,'D');
    assert(strlen(f.rename_text)==96);
    f.rename_key=44;assert(!key(PM_KEY_CONFIRM)&&!f.rename_editor&&!a.command[0]);
}
int main(void)
{
    home_library();
    instances();
    content();
    settings_accounts_close();
    search_and_delete_regressions();
    render_bounds();
    themes_and_motion();
    renaming();
    full_palettes_and_transparent_icons();
    puts("Launcher controller, pointer, content, deletion, close and framebuffer checks passed.");
    return 0;
}
