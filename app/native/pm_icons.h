/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PM_ICONS_H
#define PM_ICONS_H

#include <stdint.h>

/* Local instance/pack icons, decoded once. Render only queues a cache miss;
 * tick loads at most one icon between frames. Returned pixels are RGBA. */
void pm_icons_init(const char *data_root);
void pm_icons_tick(void);
void pm_icons_invalidate(void);
const uint8_t *pm_icon_pixels(const char *path, unsigned *width, unsigned *height);

#endif
