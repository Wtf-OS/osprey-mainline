/* ARM32 diagnostic PID1: provide linker environment before starting mksh. */
static int call3(int number, int a, int b, int c) {
    register int r0 __asm__("r0") = a, r1 __asm__("r1") = b;
    register int r2 __asm__("r2") = c, r7 __asm__("r7") = number;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r7) : "memory", "cc");
    return r0;
}
static int mount_proc(void) {
    register int r0 __asm__("r0") = (int)"proc";
    register int r1 __asm__("r1") = (int)"/proc";
    register int r2 __asm__("r2") = (int)"proc";
    register int r3 __asm__("r3") = 0, r4 __asm__("r4") = 0;
    register int r7 __asm__("r7") = 21;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r4), "r"(r7) : "memory", "cc");
    return r0;
}
void _start(void) {
    call3(14, (int)"/dev/kmsg", 0020600, 267);
    int fd = call3(5, (int)"/dev/kmsg", 1 | 0x80000, 0); /* O_CLOEXEC: do not leak fd into Android services. */
    if (fd >= 0) {
        call3(63, fd, 1, 0);
        call3(63, fd, 2, 0);
        static const char message[] = "OSPREY PROBE: static ARM32 init entered\n";
        call3(4, fd, (int)message, sizeof(message)-1);
    }
    if (mount_proc() < 0) {
        static const char message[] = "OSPREY PROBE: mount proc failed; holding PID1\n";
        if (fd >= 0) call3(4, fd, (int)message, sizeof(message)-1);
        for (;;) call3(29, 0, 0, 0);
    }
    char *args[] = {"/sbin/sh", "/probe-init", 0};
    char *env[] = {"LD_LIBRARY_PATH=/sbin", "PATH=/sbin", "HOME=/", "TERM=linux", 0};
    call3(11, (int)args[0], (int)args, (int)env);
    static const char failed[] = "OSPREY PROBE: execve shell failed; holding PID1\n";
    if (fd >= 0) call3(4, fd, (int)failed, sizeof(failed)-1);
    for (;;) call3(29, 0, 0, 0);
}
