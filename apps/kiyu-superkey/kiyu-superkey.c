/*
 * kiyu-superkey — Super(Win) 키를 혼자 눌렀다 떼면 다른 키 조합(기본 Alt+F1)을 보낸다.
 * Super+E 같은 조합은 그대로 통과한다. xcape 와 같은 원리(XRecord 로 관찰, XTest 로 주입)지만
 * 배포판 패키지에 의존하지 않도록 kiyu 가 직접 관리하는 최소 구현이다.
 *
 * 사용: kiyu-superkey [-t 밀리초] [-k 키심(기본 F1)] [-m 모디파이어 키심(기본 Alt_L)]
 * 빌드: gcc -O2 -o kiyu-superkey kiyu-superkey.c -lX11 -lXtst
 * 라이선스: MIT (kiyu 프로젝트)
 */
#include <X11/Xlib.h>
#include <X11/Xproto.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
#include <X11/extensions/record.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

static Display *ctrl_dpy;
static KeyCode kc_super_l, kc_super_r, kc_mod, kc_key;
static int super_down = 0, other_pressed = 0;
static struct timeval t_down;
static long timeout_ms = 350;

static long elapsed_ms(void)
{
    struct timeval now;
    gettimeofday(&now, NULL);
    return (now.tv_sec - t_down.tv_sec) * 1000 + (now.tv_usec - t_down.tv_usec) / 1000;
}

static void send_combo(void)
{
    XTestFakeKeyEvent(ctrl_dpy, kc_mod, True, 0);
    XTestFakeKeyEvent(ctrl_dpy, kc_key, True, 0);
    XTestFakeKeyEvent(ctrl_dpy, kc_key, False, 0);
    XTestFakeKeyEvent(ctrl_dpy, kc_mod, False, 0);
    XFlush(ctrl_dpy);
}

static void callback(XPointer closure, XRecordInterceptData *d)
{
    (void)closure;
    if (d->category == XRecordFromServer && d->data) {
        const xEvent *ev = (const xEvent *)d->data;
        int type = ev->u.u.type & 0x7f;
        KeyCode kc = ev->u.u.detail;
        int is_super = (kc == kc_super_l || kc == kc_super_r);
        if (type == KeyPress) {
            if (is_super) {
                super_down = 1;
                other_pressed = 0;
                gettimeofday(&t_down, NULL);
            } else if (super_down) {
                other_pressed = 1;
            }
        } else if (type == KeyRelease) {
            if (is_super && super_down) {
                super_down = 0;
                if (!other_pressed && elapsed_ms() <= timeout_ms)
                    send_combo();
            }
        } else if (type == ButtonPress && super_down) {
            other_pressed = 1;
        }
    }
    XRecordFreeData(d);
}

int main(int argc, char **argv)
{
    KeySym key_sym = XK_F1, mod_sym = XK_Alt_L;
    int opt;
    while ((opt = getopt(argc, argv, "t:k:m:h")) != -1) {
        switch (opt) {
        case 't': timeout_ms = atol(optarg); break;
        case 'k': key_sym = XStringToKeysym(optarg); break;
        case 'm': mod_sym = XStringToKeysym(optarg); break;
        default:
            fprintf(stderr, "usage: %s [-t ms] [-k keysym] [-m modifier-keysym]\n", argv[0]);
            return opt == 'h' ? 0 : 2;
        }
    }
    if (key_sym == NoSymbol || mod_sym == NoSymbol) {
        fprintf(stderr, "kiyu-superkey: unknown keysym\n");
        return 2;
    }
    ctrl_dpy = XOpenDisplay(NULL);
    Display *data_dpy = XOpenDisplay(NULL);
    if (!ctrl_dpy || !data_dpy) {
        fprintf(stderr, "kiyu-superkey: cannot open display\n");
        return 1;
    }
    int major, minor;
    if (!XRecordQueryVersion(ctrl_dpy, &major, &minor)) {
        fprintf(stderr, "kiyu-superkey: XRecord extension not available\n");
        return 1;
    }
    XSynchronize(ctrl_dpy, True);
    kc_super_l = XKeysymToKeycode(ctrl_dpy, XK_Super_L);
    kc_super_r = XKeysymToKeycode(ctrl_dpy, XK_Super_R);
    kc_mod = XKeysymToKeycode(ctrl_dpy, mod_sym);
    kc_key = XKeysymToKeycode(ctrl_dpy, key_sym);
    if (!kc_super_l || !kc_mod || !kc_key) {
        fprintf(stderr, "kiyu-superkey: keycode lookup failed\n");
        return 1;
    }
    XRecordRange *range = XRecordAllocRange();
    if (!range) return 1;
    range->device_events.first = KeyPress;
    range->device_events.last = ButtonRelease;
    XRecordClientSpec spec = XRecordAllClients;
    XRecordContext ctx = XRecordCreateContext(ctrl_dpy, 0, &spec, 1, &range, 1);
    if (!ctx) {
        fprintf(stderr, "kiyu-superkey: cannot create record context\n");
        return 1;
    }
    XFree(range);
    if (!XRecordEnableContext(data_dpy, ctx, callback, NULL)) {
        fprintf(stderr, "kiyu-superkey: cannot enable record context\n");
        return 1;
    }
    return 0;
}
