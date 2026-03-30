#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct arda_identity {
    __u64 inode;
    __u32 dev;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, struct arda_identity);
    __type(value, __u32);
} arda_harmony_map SEC(".maps");

SEC("lsm/bprm_check_security")
int BPF_PROG(arda_sovereign_ignition, struct linux_binprm *bprm, int ret)
{
    if (ret != 0) return ret;
    if (!bprm->file) return 0;

    struct arda_identity key = {};
    key.inode = bprm->file->f_inode->i_ino;
    key.dev = bprm->file->f_inode->i_sb->s_dev;

    bpf_printk("ARDA_LSM: hook entry for inode %llu, dev %u", key.inode, key.dev);

    __u32 *is_harmonic = bpf_map_lookup_elem(&arda_harmony_map, &key);
    if (!is_harmonic || *is_harmonic == 0) {
        bpf_printk("ARDA_LSM: DENIED execution (miss) for inode %llu", key.inode);
        return -1; // -EPERM
    }

    bpf_printk("ARDA_LSM: ALLOWED execution (hit) for inode %llu", key.inode);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
