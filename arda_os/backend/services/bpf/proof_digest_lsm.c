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
    __uint(max_entries, 4096);
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
    __uint(max_entries, 4096);
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

SEC("lsm/bprm_check_security")
int BPF_PROG(arda_sovereign_ignition, struct linux_binprm *bprm, int ret)
{
    if (ret != 0) return ret;

    struct arda_identity key = {};
    __u32 index = 0;
    __u32 *state = bpf_map_lookup_elem(&arda_state_map, &index);
    __u32 *lockdown = bpf_map_lookup_elem(&arda_lockdown_map, &index);
    struct arda_policy_state *policy_state = bpf_map_lookup_elem(&arda_policy_state_map, &index);
    struct arda_last_deny_event deny_event = {};
    __u64 cgroup_id = 0;
    __u32 deny_reason = 0;
    __u64 policy_namespace = 0;

    if (!bprm->file) return 0;

    if (lockdown && *lockdown == ARDA_LOCKDOWN_DENY_ALL) {
        deny_reason = ARDA_DENY_REASON_LOCKDOWN;
        goto veto;
    }
    /*
     * REDLINE_PRESENT records that constitutional redline rules exist.
     * It is metadata and must coexist with strict measured execution.
     *
     * REDLINE_TRIGGERED is the fail-closed runtime emergency condition.
     * Only an explicitly triggered redline may veto execution here.
     */
    if (policy_state &&
        (policy_state->projection_flags & ARDA_POLICY_FLAG_REDLINE_TRIGGERED)) {
        deny_reason = ARDA_DENY_REASON_REDLINE;
        goto veto;
    }

    if (!state || *state == ARDA_MODE_AUDIT) {
        return 0;
    }
    key.inode = bprm->file->f_inode->i_ino;
    key.dev = bprm->file->f_inode->i_sb->s_dev;
    cgroup_id = bpf_get_current_cgroup_id();

    if (*state == ARDA_MODE_FSVERITY_STRICT || *state == ARDA_MODE_SCOPED_STRICT ||
        *state == ARDA_MODE_HOST_GLOBAL || *state == ARDA_MODE_SUBTREE_TEST) {
        policy_namespace = cgroup_id;
        if (*state == ARDA_MODE_HOST_GLOBAL) {
            // One host generation applies inside the hook to every cgroup,
            // including cgroups created after userspace prepared its policy.
            policy_namespace = 0;
        } else if (*state == ARDA_MODE_SUBTREE_TEST) {
            // Bounded disposable test: metadata identifies one ancestor only.
            // Never treat this mode as whole-host coverage.
            if (!policy_state || !(policy_state->projection_flags & 2)) {
                deny_reason = ARDA_DENY_REASON_INVALID_MODE;
                goto veto;
            }
            __u64 ancestor = bpf_get_current_ancestor_cgroup_id(policy_state->redline_rule_count);
            if (ancestor != policy_state->generation_hash_prefix) return 0;
            policy_namespace = ancestor;
        }
        __u64 *active_generation = bpf_map_lookup_elem(&arda_active_generation_map, &policy_namespace);

        // Scoped mode only enforces explicitly enrolled cgroups.
        if (*state == ARDA_MODE_SCOPED_STRICT && !active_generation)
            return 0;

        if (!active_generation) {
            deny_reason = ARDA_DENY_REASON_MISSING_ACTIVE_GENERATION;
            goto veto;
        }
        if (*active_generation == 0) {
            deny_reason = ARDA_DENY_REASON_ZERO_ACTIVE_GENERATION;
            goto veto;
        }

        struct arda_measured_exec_key measured_key = {};
        measured_key.cgroup_id = policy_namespace;
        measured_key.generation = *active_generation;
        measured_key.inode = key.inode;
        measured_key.dev = key.dev;
        __u32 *is_measured = bpf_map_lookup_elem(&arda_measured_exec_map, &measured_key);
        if (is_measured && *is_measured != 0) {
            struct arda_digest_buffer *actual = bpf_map_lookup_elem(&arda_dig_work, &index);
            if (!actual) {
                deny_reason = ARDA_DENY_REASON_VERITY_UNAVAILABLE;
                goto veto;
            }
            __builtin_memset(actual, 0, sizeof(*actual));
            struct bpf_dynptr digest_ptr;
            if (bpf_dynptr_from_mem(actual, sizeof(*actual), 0, &digest_ptr) ||
                bpf_get_fsverity_digest(bprm->file, &digest_ptr)) {
                deny_reason = ARDA_DENY_REASON_VERITY_UNAVAILABLE;
                goto veto;
            }
            if (!((actual->algorithm == 1 && actual->size == 32) ||
                  (actual->algorithm == 2 && actual->size == 64))) {
                deny_reason = ARDA_DENY_REASON_VERITY_UNAVAILABLE;
                goto veto;
            }
            struct arda_verity_identity_key digest_key = {};
            digest_key.cgroup_id = policy_namespace;
            digest_key.generation = *active_generation;
            digest_key.algorithm_id = actual->algorithm;
            digest_key.digest_size = actual->size;
            __builtin_memcpy(digest_key.digest, actual->digest, 64);
            __u32 *digest_allowed = bpf_map_lookup_elem(&arda_verity_identity_map, &digest_key);
            if (digest_allowed && *digest_allowed != 0) return 0;
            deny_reason = ARDA_DENY_REASON_VERITY_DIGEST_MISS;
            goto veto;
        }
        deny_reason = ARDA_DENY_REASON_MEASURED_EXEC_MISS;
        goto veto;
    }
    if (*state != ARDA_MODE_LEGACY_INODE) {
        deny_reason = ARDA_DENY_REASON_INVALID_MODE;
        goto veto;
    }

    __u32 *is_harmonic = bpf_map_lookup_elem(&arda_harmony_map, &key);
    if (is_harmonic && *is_harmonic != 0) {
        return 0;
    }
    deny_reason = ARDA_DENY_REASON_HARMONY_MISS;

veto:
    {
        __u64 *deny_count = bpf_map_lookup_elem(&arda_deny_count, &index);
        if (deny_count) {
            __sync_fetch_and_add(deny_count, 1);
        }
        deny_event.cgroup_id = cgroup_id;
        deny_event.active_generation = 0;
        if (state && (*state == ARDA_MODE_FSVERITY_STRICT ||
                       *state == ARDA_MODE_SCOPED_STRICT ||
                       *state == ARDA_MODE_HOST_GLOBAL || *state == ARDA_MODE_SUBTREE_TEST) && cgroup_id != 0) {
            __u64 *active_generation = bpf_map_lookup_elem(&arda_active_generation_map, &policy_namespace);
            if (active_generation) {
                deny_event.active_generation = *active_generation;
            }
        }
        deny_event.inode = key.inode;
        deny_event.dev = key.dev;
        deny_event.enforcement_mode = state ? *state : ARDA_MODE_AUDIT;
        deny_event.deny_reason = deny_reason;
        bpf_map_update_elem(&arda_last_deny_event_map, &index, &deny_event, BPF_ANY);
        return -1; // -EPERM
    }
}

char LICENSE[] SEC("license") = "GPL";
