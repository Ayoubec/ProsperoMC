/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "pm_bridge.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* This executable sends actual frontend actions, then reads Java's real view.
 * The Python harness runs the backend between select/verify/delete stages. */
int main(int argc,char **argv)
{
    static PmView view;PmFrontend frontend;PmAction action;
    assert(argc>=4);const char *root=argv[1],*stage=argv[3];int kind=atoi(argv[2]);
    const char *kinds[]={"mods","resourcepacks","shaderpacks"};assert(kind>=0&&kind<3);
    assert(!pm_bridge_view(root,&view));assert(view.instance_count==1);
    pm_frontend_init(&frontend);frontend.screen=PM_MODS;frontend.selected_instance=0;
    if(!strcmp(stage,"select")) {
        frontend.content_kind=(kind+2)%3;frontend.focus=1;
        assert(pm_frontend_update(&frontend,&view,PM_KEY_RIGHT,&action));
        assert(!strcmp(action.command,"content-list")&&!strcmp(action.content_kind,kinds[kind]));
        assert(!strcmp(action.id,"wire-instance"));assert(!pm_bridge_request(root,&action));
    } else {
        assert(!strcmp(view.content_kind,kinds[kind]));assert(!strcmp(view.content_instance,"wire-instance"));
        assert(argc==5&&view.mod_count==1&&!strcmp(view.mods[0].name,argv[4]));
        /* Reopening and repeated view refresh retain the selected category. */
        frontend.content_kind=kind;frontend.focus=5;assert(!pm_bridge_frontend_save(root,&frontend));
        pm_frontend_init(&frontend);pm_bridge_frontend_load(root,&frontend);
        assert(frontend.content_kind==kind);assert(!pm_bridge_view(root,&view));
        assert(!strcmp(view.content_kind,kinds[kind])&&view.mod_count==1);
        if(!strcmp(stage,"delete")) {
            assert(!pm_frontend_update(&frontend,&view,PM_KEY_CONFIRM,&action));
            assert(frontend.confirmation==3);
            assert(!pm_frontend_update(&frontend,&view,PM_KEY_RIGHT,&action));
            assert(pm_frontend_update(&frontend,&view,PM_KEY_CONFIRM,&action));
            assert(!strcmp(action.command,"content-delete")&&!strcmp(action.mod,argv[4]));
            assert(!strcmp(action.content_kind,kinds[kind]));assert(!pm_bridge_request(root,&action));
        }
    }
    puts("CONTENT_WIRE_PASS");return 0;
}
