#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef HELPER_PYTHON
#define HELPER_PYTHON "/opt/gotchi/venv/bin/python"
#endif

#ifndef HELPER_MAIL_ROOT
#define HELPER_MAIL_ROOT "/var/lib/gotchi-mail"
#endif

#ifndef HELPER_MODULE
#define HELPER_MODULE "gotchi_app.mail_helper"
#endif

int main(int argc, char **argv) {
    size_t extra = 6;
    char **new_argv = calloc((size_t)argc + extra + 1, sizeof(char *));
    if (new_argv == NULL) {
        fprintf(stderr, "gotchi-mail-bridge: calloc failed: %s\n", strerror(errno));
        return 111;
    }

    new_argv[0] = (char *)HELPER_PYTHON;
    new_argv[1] = (char *)"-s";
    new_argv[2] = (char *)"-E";
    new_argv[3] = (char *)"-m";
    new_argv[4] = (char *)HELPER_MODULE;
    new_argv[5] = (char *)"--mail-root";
    new_argv[6] = (char *)HELPER_MAIL_ROOT;

    for (int i = 1; i < argc; ++i) {
        new_argv[i + 6] = argv[i];
    }
    new_argv[argc + 6] = NULL;

    execv(HELPER_PYTHON, new_argv);
    fprintf(stderr, "gotchi-mail-bridge: exec failed: %s\n", strerror(errno));
    free(new_argv);
    return 111;
}
