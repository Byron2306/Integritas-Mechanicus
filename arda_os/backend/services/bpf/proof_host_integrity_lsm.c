/* Candidate only: no host activation until independently tested. */
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

#define ARDA_MODE_AUDIT 0
#define ARDA_MODE_LEGACY_INODE 1
#define ARDA_MODE_FSVERITY_STRICT 2
#define ARDA_MODE_SCOPED_STRICT 3
#define ARDA_MODE_HOST_GLOBAL 4
#define ARDA_MODE_SUBTREE_TEST 5
#define ARDA_LOCKDOWN_DISABLED 0
#define ARDA_LOCKDOWN_DENY_ALL 1
#define ARDA_POLICY_FLAG_REDLINE_PRESENT 1
#define ARDA_POLICY_FLAG_REDLINE_TRIGGERED 2
#define ARDA_DENY_REASON_LOCKDOWN 1
#define ARDA_DENY_REASON_REDLINE 2
#define ARDA_DENY_REASON_MISSING_ACTIVE_GENERATION 3
#define ARDA_DENY_REASON_ZERO_ACTIVE_GENERATION 4
#define ARDA_DENY_REASON_MEASURED_EXEC_MISS 5
#define ARDA_DENY_REASON_INVALID_MODE 6
#define ARDA_DENY_REASON_HARMONY_MISS 7
#define ARDA_DENY_REASON_VERITY_UNAVAILABLE 8
#define ARDA_DENY_REASON_VERITY_DIGEST_MISS 9

struct arda_digest_buffer {
    __u16 algorithm;
    __u16 size;
    __u8 digest[64];
};

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct arda_digest_buffer);
} arda_dig_work SEC(".maps");

struct arda_identity {
    unsigned long inode;
    unsigned int dev;
};

struct arda_verity_identity_key {
    __u64 cgroup_id;
    __u64 generation;
    __u16 algorithm_id;
    __u16 digest_size;
    __u8 digest[64];
};

struct arda_measured_exec_key {
    __u64 cgroup_id;
    __u64 generation;
    unsigned long inode;
    unsigned int dev;
};

struct arda_policy_state {
    __u64 generation_hash_prefix;
    __u32 redline_rule_count;
    __u32 projection_flags;
};

struct arda_last_deny_event {
    __u64 cgroup_id;
    __u64 active_generation;
    unsigned long inode;
    unsigned int dev;
    __u32 enforcement_mode;
    __u32 deny_reason;
    __u32 operation;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, struct arda_identity);
    __type(value, __u32);
} arda_harmony_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u32);
} arda_state_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} arda_deny_count SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 65536);
    __type(key, struct arda_verity_identity_key);
    __type(value, __u32);
} arda_verity_identity_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u64);
    __type(value, __u64);
} arda_active_generation_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 65536);
    __type(key, struct arda_measured_exec_key);
    __type(value, __u32);
} arda_measured_exec_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct arda_policy_state);
} arda_policy_state_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u32);
} arda_lockdown_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct arda_last_deny_event);
} arda_last_deny_event_map SEC(".maps");


#define ARDA_OP_EXEC 1
#define ARDA_OP_MMAP 2
#define ARDA_OP_MPROTECT 3
#define ARDA_OP_READ 4
#define ARDA_OP_LOAD 5
#define ARDA_DENY_ANONYMOUS 10
#define ARDA_DENY_RESTRICTED_LAUNCH 11
#define ARDA_DENY_EXEC_PERMISSION_CHANGE 12
#define ARDA_ADMIT 1
#define ARDA_RESTRICT_INTERPRETER 2
#define ARDA_RESTRICT_SCRIPT 4
#define ARDA_PROT_EXEC 4

static __always_inline int arda_check_file(struct file *file, __u32 operation)
{
    __u32 zero = 0;
    __u32 *mode = bpf_map_lookup_elem(&arda_state_map, &zero);
    if (!mode || *mode == ARDA_MODE_AUDIT) return 0;
    __u64 cgroup = bpf_get_current_cgroup_id();
    __u64 namespace = *mode == ARDA_MODE_HOST_GLOBAL ? 0 : cgroup;
    __u64 *generation = bpf_map_lookup_elem(&arda_active_generation_map, &namespace);
    if (*mode == ARDA_MODE_SCOPED_STRICT && !generation) return 0;

    struct arda_last_deny_event event = {};
    event.cgroup_id = cgroup;
    event.enforcement_mode = *mode;
    event.operation = operation;
    if (*mode != ARDA_MODE_HOST_GLOBAL && *mode != ARDA_MODE_SCOPED_STRICT) {
        event.deny_reason = ARDA_DENY_REASON_INVALID_MODE; goto denied;
    }
    if (!generation || !*generation) {
        event.deny_reason = ARDA_DENY_REASON_MISSING_ACTIVE_GENERATION; goto denied;
    }
    event.active_generation = *generation;
    __u32 *lock = bpf_map_lookup_elem(&arda_lockdown_map, &zero);
    struct arda_policy_state *policy = bpf_map_lookup_elem(&arda_policy_state_map, &zero);
    if (lock && *lock) { event.deny_reason = ARDA_DENY_REASON_LOCKDOWN; goto denied; }
    /*
     * REDLINE_PRESENT records constitutional rule presence only.
     * Only an explicit runtime REDLINE_TRIGGERED condition may veto.
     */
    if (policy &&
        (policy->projection_flags & ARDA_POLICY_FLAG_REDLINE_TRIGGERED)) {
        event.deny_reason = ARDA_DENY_REASON_REDLINE; goto denied;
    }
    if (!file) {
        event.deny_reason = operation == ARDA_OP_MPROTECT ?
            ARDA_DENY_EXEC_PERMISSION_CHANGE : ARDA_DENY_ANONYMOUS;
        goto denied;
    }
    event.inode = file->f_inode->i_ino;
    event.dev = file->f_inode->i_sb->s_dev;
    struct arda_measured_exec_key identity = {};
    identity.cgroup_id = namespace;
    identity.generation = *generation;
    identity.inode = event.inode;
    identity.dev = event.dev;
    __u32 *admitted = bpf_map_lookup_elem(&arda_measured_exec_map, &identity);
    if (!admitted || !(*admitted & ARDA_ADMIT) ||
        (*admitted & ~(ARDA_ADMIT | ARDA_RESTRICT_INTERPRETER | ARDA_RESTRICT_SCRIPT))) {
        event.deny_reason = ARDA_DENY_REASON_MEASURED_EXEC_MISS; goto denied;
    }
    if (operation == ARDA_OP_EXEC &&
        (*admitted & (ARDA_RESTRICT_INTERPRETER | ARDA_RESTRICT_SCRIPT))) {
        event.deny_reason = ARDA_DENY_RESTRICTED_LAUNCH; goto denied;
    }
    struct arda_digest_buffer *actual = bpf_map_lookup_elem(&arda_dig_work, &zero);
    if (!actual) { event.deny_reason = ARDA_DENY_REASON_VERITY_UNAVAILABLE; goto denied; }
    __builtin_memset(actual, 0, sizeof(*actual));
    struct bpf_dynptr ptr;
    if (bpf_dynptr_from_mem(actual, sizeof(*actual), 0, &ptr) || bpf_get_fsverity_digest(file, &ptr)) {
        event.deny_reason = ARDA_DENY_REASON_VERITY_UNAVAILABLE; goto denied;
    }
    if (!((actual->algorithm == 1 && actual->size == 32) ||
          (actual->algorithm == 2 && actual->size == 64))) {
        event.deny_reason = ARDA_DENY_REASON_VERITY_UNAVAILABLE; goto denied;
    }
    struct arda_verity_identity_key digest = {};
    digest.cgroup_id = namespace;
    digest.generation = *generation;
    digest.algorithm_id = actual->algorithm;
    digest.digest_size = actual->size;
    __builtin_memcpy(digest.digest, actual->digest, 64);
    __u32 *allowed = bpf_map_lookup_elem(&arda_verity_identity_map, &digest);
    if (allowed && *allowed == ARDA_ADMIT) return 0;
    event.deny_reason = ARDA_DENY_REASON_VERITY_DIGEST_MISS;
denied:
    {
        __u64 *count = bpf_map_lookup_elem(&arda_deny_count, &zero);
        if (count) __sync_fetch_and_add(count, 1);
        bpf_map_update_elem(&arda_last_deny_event_map, &zero, &event, BPF_ANY);
        return -1;
    }
}

SEC("lsm/bprm_check_security")
int BPF_PROG(arda_host_exec, struct linux_binprm *bprm, int ret)
{
    if (ret) return ret;
    return arda_check_file(bprm->file, ARDA_OP_EXEC);
}

SEC("lsm/mmap_file")
int BPF_PROG(arda_host_mmap, struct file *file, unsigned long reqprot,
             unsigned long prot, unsigned long flags, int ret)
{
    if (ret) return ret;
    if (!(prot & ARDA_PROT_EXEC)) return 0;
    /* Private writable executable mappings permit modification of copied code. */
    return arda_check_file((prot & 2) ? NULL : file, ARDA_OP_MMAP);
}

SEC("lsm/file_mprotect")
int BPF_PROG(arda_host_mprotect, struct vm_area_struct *vma,
             unsigned long reqprot, unsigned long prot, int ret)
{
    if (ret) return ret;
    if (!(prot & ARDA_PROT_EXEC)) return 0;
    /* Valinor 6.12 does not treat a VMA-derived file as trusted for
     * bpf_get_fsverity_digest. Strict policy denies ALL executable mprotect
     * requests, including file-backed mappings and already-executable VMAs.
     * Audit and cgroups outside scoped policy still pass through unchanged.
     */
    return arda_check_file(NULL, ARDA_OP_MPROTECT);
}

SEC("lsm/kernel_read_file")
int BPF_PROG(arda_host_read, struct file *file, enum kernel_read_file_id id,
             bool contents, int ret)
{
    if (ret) return ret;
    return arda_check_file(file, ARDA_OP_READ);
}

SEC("lsm/kernel_load_data")
int BPF_PROG(arda_host_load, enum kernel_load_data_id id, bool contents, int ret)
{
    if (ret) return ret;
    return arda_check_file(NULL, ARDA_OP_LOAD);
}

char LICENSE[] SEC("license") = "GPL";
