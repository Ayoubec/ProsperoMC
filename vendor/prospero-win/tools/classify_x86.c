/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Batch adapter around the real translator for offline coverage surveys. */
#include "../src/pw_x86_block.h"
#include <stdio.h>
#include <string.h>

static int nibble(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int main(void)
{
    char line[64];
    while (fgets(line, sizeof(line), stdin)) {
        uint8_t source[15], output[8192];
        PwX86Block block;
        size_t chars = strcspn(line, "\r\n"), bytes = chars / 2;
        int status = PW_ERR_PRECONDITION;
        if (chars && !(chars & 1) && bytes <= sizeof(source)) {
            status = PW_OK;
            for (size_t i = 0; i < bytes; ++i) {
                int high = nibble(line[i * 2]), low = nibble(line[i * 2 + 1]);
                if (high < 0 || low < 0) { status = PW_ERR_PRECONDITION; break; }
                source[i] = (uint8_t)((high << 4) | low);
            }
            if (status == PW_OK) {
                status = pw_x86_translate(source, bytes, 0x10000000u,
                                          output, sizeof(output), &block);
                if (status == PW_OK && block.source_bytes != bytes)
                    status = PW_ERR_STATE;
            }
        }
        printf("%d\n", status);
    }
    return ferror(stdin) ? 1 : 0;
}
