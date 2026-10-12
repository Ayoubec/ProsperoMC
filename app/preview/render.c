/* Native framebuffer preview: no browser, CSS or parallel mock UI. */
#include "pm_frontend.h"
#include "pm_icons.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static PmView view;
static char icon_root[512];
static void fixture(void)
{
    strcpy(view.status, "idle");
    view.memory_mb = 2048;
    view.instance_count = 16;
    const char *names[] = {"Prospero Adventures", "Minecraft 1.12.2",   "Fabulously Optimized",
                           "Vanilla survival",    "Fabric experiments", "Forge adventures",
                           "NeoForge creative",   "Redstone workshop",  "Sky islands",
                           "Caves and cliffs",    "Creative building",  "The old world"};
    const char *loaders[] = {"fabric", "vanilla", "fabric",   "vanilla",
                             "fabric", "forge",   "neoforge", "vanilla"};
    for (int j = 0; j < 16; j++)
    {
        PmInstance *i = &view.instances[j];
        snprintf(i->id, sizeof(i->id), "instance-%02d", j);
        snprintf(i->name, sizeof(i->name), "%s", names[j % 12]);
        snprintf(i->loader, sizeof(i->loader), "%s", loaders[j % 8]);
        snprintf(i->version, sizeof(i->version), "%s", j == 1 || j == 5 ? "1.12.2" : "26.2");
        i->installed = j != 10;
    }
    snprintf(view.instances[0].icon, sizeof(view.instances[0].icon), "%.490s/custom.png",
             icon_root);
    snprintf(view.instances[2].icon, sizeof(view.instances[2].icon), "%.490s/fo.webp", icon_root);
    view.memory_mb = 3584;
    view.resolution_height = 1440;
    strcpy(view.content_instance, view.instances[0].id);
    strcpy(view.content_kind, "mods");
    view.mod_count = 5;
    const char *mods[] = {"Sodium", "Iris Shaders", "Fabric API", "Entity Culling", "FerriteCore"};
    for (int j = 0; j < 5; j++)
    {
        snprintf(view.mods[j].name, PM_TEXT, "%s.jar", mods[j]);
        view.mods[j].enabled = j != 1;
    }
    view.remote_count = 3;
    view.remote_total = 3;
    const char *packs[] = {"Fabulously Optimized", "Simply Optimized", "Adventures in the forest"};
    for (int j = 0; j < 3; j++)
    {
        snprintf(view.remote_packs[j].name, PM_TEXT, "%s", packs[j]);
        snprintf(view.remote_packs[j].description, 512,
                 "A complete Minecraft instance with its own mods and settings.");
    }
    view.version_count = 6;
    {
        const char *v[] = {"1.21.1", "1.20.1", "1.19.4", "1.18.2", "1.16.5", "1.12.2"};
        int j;
        for (j = 0; j < 6; j++)
        {
            strcpy(view.versions[j].id, v[j]);
            strcpy(view.versions[j].type, "release");
            view.versions[j].java = j < 1 ? 21 : j < 4 ? 17 : 8;
        }
    }
    strcpy(view.java_path, "Java 8 / staged local runtime");
    strcpy(view.username, "Player");
    strcpy(view.account_username, "Ayoubec");
    strcpy(view.account_mode, "microsoft");
    strcpy(view.account_status, "Signed in");
    view.java_count = 2;
    view.java_runtimes[0].major = 8;
    view.java_runtimes[0].valid = 1;
    strcpy(view.java_runtimes[0].version, "1.8.0_451");
    strcpy(view.java_runtimes[0].detail, "Detected Windows 64-bit Java runtime.");
    view.java_runtimes[1].major = 21;
    view.java_runtimes[1].valid = 1;
    strcpy(view.java_runtimes[1].version, "21.0.8");
    strcpy(view.java_runtimes[1].detail, "Detected Windows 64-bit Java runtime.");
}
static void load(const char *path)
{
    FILE *fp = fopen(path, "rb");
    char line[1024];
    if (!fp)
    {
        perror(path);
        exit(2);
    }
    memset(&view, 0, sizeof(view));
    while (fgets(line, sizeof(line), fp))
    {
        char *value = strchr(line, '=');
        int n;
        char prop[100];
        if (!value || line[0] == '#')
            continue;
        *value++ = 0;
        value[strcspn(value, "\r\n")] = 0;
        if (!strcmp(line, "status"))
            snprintf(view.status, sizeof(view.status), "%s", value);
        else if (!strcmp(line, "detail"))
            snprintf(view.detail, sizeof(view.detail), "%s", value);
        else if (!strcmp(line, "instance.count"))
            view.instance_count = atoi(value);
        else if (!strcmp(line, "version.count"))
            view.version_count = atoi(value);
        else if (!strcmp(line, "mod.count"))
            view.mod_count = atoi(value);
        else if (!strcmp(line, "java.count"))
            view.java_count = atoi(value);
        else if (!strcmp(line, "memoryMb") || !strcmp(line, "settings.memoryMb"))
            view.memory_mb = atoi(value);
        else if (!strcmp(line, "settings.java8"))
            snprintf(view.java_path, sizeof(view.java_path), "%s", value);
        else if (!strcmp(line, "auth.userCode"))
            snprintf(view.auth_code, sizeof(view.auth_code), "%s", value);
        else if (!strcmp(line, "auth.verificationUri"))
            snprintf(view.auth_url, sizeof(view.auth_url), "%s", value);
        else if (!strcmp(line, "auth.signedIn"))
            snprintf(view.account_status, sizeof(view.account_status), "%s",
                     !strcmp(value, "true") ? "Signed in" : "Not signed in");
        else if (!strcmp(line, "auth.username"))
            snprintf(view.account_username, sizeof(view.account_username), "%s", value);
        else if (!strcmp(line, "content.kind"))
            snprintf(view.content_kind, sizeof(view.content_kind), "%s", value);
        else if (!strcmp(line, "content.instance"))
            snprintf(view.content_instance, sizeof(view.content_instance), "%s", value);
        else if (!strcmp(line, "username") || !strcmp(line, "settings.username"))
            snprintf(view.username, sizeof(view.username), "%s", value);
        else if (!strcmp(line, "settings.accountMode"))
            snprintf(view.account_mode, sizeof(view.account_mode), "%s", value);
        else if (!strcmp(line, "settings.graphics"))
            snprintf(view.graphics, sizeof(view.graphics), "%s", value);
        else if (!strcmp(line, "settings.controllerMode"))
            snprintf(view.controller_mode, sizeof(view.controller_mode), "%s", value);
        else if (!strcmp(line, "settings.themeColor"))
            snprintf(view.theme_color, sizeof(view.theme_color), "%s", value);
        else if (!strcmp(line, "settings.vrrMode"))
            snprintf(view.vrr_mode, sizeof(view.vrr_mode), "%s", value);
        else if (!strcmp(line, "auth.userCode"))
            snprintf(view.auth_code, sizeof(view.auth_code), "%s", value);
        else if (!strcmp(line, "auth.verificationUri"))
            snprintf(view.auth_url, sizeof(view.auth_url), "%s", value);
        else if (!strcmp(line, "auth.provider"))
            snprintf(view.auth_provider, sizeof(view.auth_provider), "%s", value);
        else if (!strcmp(line, "remote.pack.count"))
            view.remote_count = atoi(value);
        else if (!strcmp(line, "remote.version.count"))
            view.remote_version_count = atoi(value);
        else if (!strcmp(line, "remote.offset"))
            view.remote_offset = atoi(value);
        else if (!strcmp(line, "remote.total"))
            view.remote_total = atoi(value);
        else if (!strcmp(line, "remote.projectId"))
            snprintf(view.remote_project, sizeof(view.remote_project), "%s", value);
        else if (sscanf(line, "remote.pack.%d.%99s", &n, prop) == 2 && n >= 0 && n < 24)
        {
            PmRemotePack *p = &view.remote_packs[n];
            if (!strcmp(prop, "id"))
                snprintf(p->id, sizeof(p->id), "%s", value);
            if (!strcmp(prop, "name"))
                snprintf(p->name, sizeof(p->name), "%s", value);
            if (!strcmp(prop, "description"))
                snprintf(p->description, sizeof(p->description), "%s", value);
            if (!strcmp(prop, "icon"))
                snprintf(p->icon, sizeof(p->icon), "%s", value);
        }
        else if (sscanf(line, "remote.version.%d.%99s", &n, prop) == 2 && n >= 0 && n < 64)
        {
            PmPackRelease *p = &view.remote_versions[n];
            if (!strcmp(prop, "id"))
                snprintf(p->id, sizeof(p->id), "%s", value);
            if (!strcmp(prop, "name"))
                snprintf(p->name, sizeof(p->name), "%s", value);
            if (!strcmp(prop, "game"))
                snprintf(p->game, sizeof(p->game), "%s", value);
            if (!strcmp(prop, "loader"))
                snprintf(p->loader, sizeof(p->loader), "%s", value);
        }
        else if (sscanf(line, "instance.%d.%99s", &n, prop) == 2 && n >= 0 && n < PM_MAX_INSTANCES)
        {
            PmInstance *i = &view.instances[n];
            if (!strcmp(prop, "id"))
                snprintf(i->id, sizeof(i->id), "%s", value);
            if (!strcmp(prop, "name"))
                snprintf(i->name, sizeof(i->name), "%s", value);
            if (!strcmp(prop, "version"))
                snprintf(i->version, sizeof(i->version), "%s", value);
            if (!strcmp(prop, "loader"))
                snprintf(i->loader, sizeof(i->loader), "%s", value);
            if (!strcmp(prop, "icon"))
                snprintf(i->icon, sizeof(i->icon), "%s", value);
            if (!strcmp(prop, "installed"))
                i->installed = !strcmp(value, "true");
        }
        else if (sscanf(line, "version.%d.%99s", &n, prop) == 2 && n >= 0 && n < PM_MAX_VERSIONS)
        {
            PmVersion *v = &view.versions[n];
            if (!strcmp(prop, "id"))
                snprintf(v->id, sizeof(v->id), "%s", value);
            if (!strcmp(prop, "type"))
                snprintf(v->type, sizeof(v->type), "%s", value);
            if (!strcmp(prop, "java"))
                v->java = atoi(value);
        }
        else if (sscanf(line, "mod.%d.%99s", &n, prop) == 2 && n >= 0 && n < PM_MAX_MODS)
        {
            PmMod *m = &view.mods[n];
            if (!strcmp(prop, "name"))
                snprintf(m->name, sizeof(m->name), "%s", value);
            if (!strcmp(prop, "enabled"))
                m->enabled = !strcmp(value, "true");
        }
        else if (sscanf(line, "java.%d.%99s", &n, prop) == 2 && n >= 0 && n < PM_MAX_JAVA)
        {
            PmJavaRuntime *runtime = &view.java_runtimes[n];
            if (!strcmp(prop, "major"))
                runtime->major = atoi(value);
            if (!strcmp(prop, "valid"))
                runtime->valid = !strcmp(value, "true") || !strcmp(value, "1");
            if (!strcmp(prop, "version"))
                snprintf(runtime->version, sizeof(runtime->version), "%s", value);
            if (!strcmp(prop, "path"))
                snprintf(runtime->path, sizeof(runtime->path), "%s", value);
            if (!strcmp(prop, "detail"))
                snprintf(runtime->detail, sizeof(runtime->detail), "%s", value);
        }
    }
    fclose(fp);
}
int main(int argc, char **argv)
{
    PmFrontend f;
    PwPresentTarget t;
    FILE *fp;
    int x, y;
    if (argc < 3)
    {
        fprintf(stderr,
                "Usage: render output.ppm screen-number [launcher-view.properties|--empty]\n");
        return 2;
    }
    char cwd[450];
    if (!getcwd(cwd, sizeof(cwd)))
        return 2;
    snprintf(icon_root, sizeof(icon_root), "%s/artifacts/frontend/icons", cwd);
    pm_icons_init(icon_root);
    pm_frontend_set_icon_loader(pm_icon_pixels);
    fixture();
    if (argc > 3)
    {
        if (!strcmp(argv[3], "--empty"))
            memset(&view, 0, sizeof(view));
        else if (strncmp(argv[3], "--", 2))
            load(argv[3]);
    }
    pm_frontend_init(&f);
    f.screen = (PmScreen)atoi(argv[2]);
    if (argc > 3 && !strncmp(argv[3], "--palette=", 10))
        snprintf(view.theme_color, sizeof(view.theme_color), "%s", argv[3] + 10);
    if (argc > 3 && !strcmp(argv[3], "--rename"))
    {
        f.rename_editor = f.rename_replace = 1;
        strcpy(f.rename_text, "Fabulously Optimized 26.2");
        f.rename_key = 43;
    }
    if (argc > 3 && !strcmp(argv[3], "--versions"))
        f.add_source = 0;
    if (argc > 3 && !strcmp(argv[3], "--remote"))
    {
        f.add_source = 1;
        f.remote_browser = 1;
    }
    if (argc > 3 && !strcmp(argv[3], "--curse"))
    {
        f.add_source = 2;
        f.remote_browser = 1;
    }
    if (argc > 3 && !strcmp(argv[3], "--restored-modrinth"))
        f.add_source = 1;
    if (argc > 3 && !strcmp(argv[3], "--restored-curse"))
        f.add_source = 2;
    if (argc > 3 && (!strcmp(argv[3], "--resources") || !strcmp(argv[3], "--shaders")))
    {
        int resources = !strcmp(argv[3], "--resources");
        f.content_kind = resources ? 1 : 2;
        snprintf(view.content_kind, sizeof(view.content_kind), "%s",
                 resources ? "resourcepacks" : "shaderpacks");
        view.mod_count = 2;
        snprintf(view.mods[0].name, PM_TEXT, "%s",
                 resources ? "Vanilla Tweaks.zip" : "Complementary Reimagined.zip");
        snprintf(view.mods[1].name, PM_TEXT, "%s", resources ? "Faithful.zip" : "BSL.zip");
    }
    if (argc > 3 && !strcmp(argv[3], "--content-search"))
    {
        f.remote_browser = 1;
        const char *mods[] = {"Sodium", "FerriteCore", "Entity Culling"};
        for (int j = 0; j < 3; j++)
        {
            snprintf(view.remote_packs[j].name, PM_TEXT, "%s", mods[j]);
            snprintf(view.remote_packs[j].description, 512,
                     "A compatible mod for the selected Minecraft instance.");
        }
    }
    if (argc > 3 && !strcmp(argv[3], "--input"))
    {
        f.selector_popup = 4;
        f.selector_choice = 0;
    }
    if (argc > 3 && !strcmp(argv[3], "--theme"))
    {
        strcpy(view.theme_color,"amethyst");
        f.selector_popup=5;
        f.selector_choice=3;
    }
    if (argc > 3 && !strcmp(argv[3], "--close"))
        f.confirmation = 2;
    if (argc > 3 && !strcmp(argv[3], "--resolution"))
    {
        f.selector_popup = 2;
        f.selector_choice = 2;
    }
    if (argc > 3 && !strcmp(argv[3], "--signin"))
    {
        strcpy(view.auth_code, "ABCD-EFGH");
        strcpy(view.auth_url, "https://microsoft.com/link");
    }
    if (argc > 4 && strcmp(argv[3], "--motion"))
    {
        f.remote_browser = 1;
        f.remote_stage = !strcmp(argv[4], "--releases");
        f.search_editor = !strcmp(argv[4], "--search");
    }
    if (argc > 3 && !strcmp(argv[3], "--packs"))
    {
        f.pack_picker = 1;
        view.pack_count = 2;
        strcpy(view.packs[0].name, "My Forge 1.12.2.zip");
        strcpy(view.packs[1].name, "Forest adventures.mrpack");
    }
    for (int frame = 0; frame < 10; frame++)
        pm_frontend_tick(&f, 100);
    if (argc > 3 && !strcmp(argv[3], "--motion"))
    {
        f.transition_ms=argc > 4 ? atoi(argv[4]) : 140;
        f.transition_direction=1;
    }
    if (argc > 3 && !strcmp(argv[3], "--fo"))
        f.selected_instance=2;
    t.width = 1920;
    t.height = 1080;
    t.stride = t.width * 4;
    t.bytes = (uint64_t)t.stride * t.height;
    t.pixels = (unsigned char *)calloc(1, (size_t)t.bytes);
    if (!t.pixels)
        return 2;
    for (int frame = 0; frame < 16; frame++)
    {
        pm_frontend_render(&f, &view, &t);
        pm_icons_tick();
    }
    fp = fopen(argv[1], "wb");
    if (!fp)
    {
        perror(argv[1]);
        return 2;
    }
    fprintf(fp, "P6\n%d %d\n255\n", t.width, t.height);
    for (y = 0; y < (int)t.height; y++)
        for (x = 0; x < (int)t.width; x++)
        {
            const unsigned char *p = t.pixels + y * t.stride + x * 4;
            fputc(p[2], fp);
            fputc(p[1], fp);
            fputc(p[0], fp);
        }
    fclose(fp);
    free(t.pixels);
    return 0;
}
