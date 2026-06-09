#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/resource.h>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>

static int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args) {
    return vfprintf(stderr, format, args);
}

int bump_memlock_limit(void) {
    struct rlimit rlim_new = {
        .rlim_cur = RLIM_INFINITY,
        .rlim_max = RLIM_INFINITY,
    };

    if (setrlimit(RLIMIT_MEMLOCK, &rlim_new)) {
        fprintf(stderr, "Failed to increase RLIMIT_MEMLOCK limit!\n");
        return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    struct bpf_object *obj;
    struct bpf_program *prog;
    struct bpf_map *map;
    struct bpf_link *link;
    int err;

    if (argc < 2) {
        fprintf(stderr, "Usage: %s <bpf_object_file>\n", argv[0]);
        return 1;
    }

    /* Set up environment */
    if (bump_memlock_limit()) {
        return 1;
    }

    /* Enable libbpf logging to stderr */
    libbpf_set_print(libbpf_print_fn);

    /* Open BPF object */
    obj = bpf_object__open_file(argv[1], NULL);
    if (libbpf_get_error(obj)) {
        fprintf(stderr, "ERROR: opening BPF object file failed\n");
        return 1;
    }

    /* Map Reuse Strategy: Bind only mutable control maps to fixed FS paths */
    bpf_object__for_each_map(map, obj) {
        const char *name = bpf_map__name(map);
        
        // Only pin maps we actually need to interact with from userspace
        if (strcmp(name, "arda_harmony") == 0 || strcmp(name, "arda_state") == 0) {
            char pin_path[256];
            snprintf(pin_path, sizeof(pin_path), "/sys/fs/bpf/%s", name);
            bpf_map__set_pin_path(map, pin_path);
        }
    }

    /* Load and verify BPF object */
    err = bpf_object__load(obj);
    if (err) {
        fprintf(stderr, "ERROR: loading BPF object failed (err=%d)\n", err);
        return 1;
    }

    /* Find and Attach the LSM program */
    prog = bpf_object__find_program_by_name(obj, "arda_sovereign_ignition");
    if (!prog) {
        fprintf(stderr, "ERROR: finding 'arda_sovereign_ignition' failed\n");
        return 1;
    }

    link = bpf_program__attach_lsm(prog);
    if (libbpf_get_error(link)) {
        fprintf(stderr, "ERROR: attaching LSM program failed\n");
        return 1;
    }

    /* Pin the link to BPF FS */
    unlink("/sys/fs/bpf/arda_lsm_link");
    err = bpf_link__pin(link, "/sys/fs/bpf/arda_lsm_link");
    if (err) {
        fprintf(stderr, "ERROR: pinning BPF link failed\n");
        return 1;
    }

    /* Ensure maps are pinned (redundant but safe with set_pin_path) */
    err = bpf_object__pin_maps(obj, "/sys/fs/bpf");
    // We ignore 'already exists' errors from pin_maps if reuse succeeded

    printf("SUCCESS: Arda LSM Attached and Maps Linked.\n");
    return 0;
}
